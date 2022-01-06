import json
import logging
import os
from typing import Any, Dict, List, Tuple

from bs4 import BeautifulSoup
from dateutil.parser import parse

from envoy_client.auth import ClientCerticateAuth, LocalModeXTokenAuth
from envoy_client.interface import (
    EndDeviceInterface,
    trailing_resource_id_from_response,
)
from envoy_client.models.base import VersionType
from envoy_client.models.constants import PhaseCode, RoleFlagsType, ServiceKind, UomType
from envoy_client.models.smart_energy import (
    DateTimeIntervalType,
    MirrorMeterReading,
    MirrorReadingSet,
    MirrorUsagePoint,
    Reading,
    ReadingType,
)
from envoy_client.transport import RequestsTransport

try:
    import zoneinfo
except ImportError:  # Python < 3.9
    from backports import zoneinfo  # noqa: F401


server_url = os.getenv("ENVOY_SERVER_URL")
certificate_path = os.getenv("ENVOY_CERTIFICATE_PATH")
key_path = os.getenv("ENVOY_KEY_PATH")

# This is a unique number for each enterprise/business/organization
# They are managed by IANA,
# https://www.iana.org/assignments/enterprise-numbers/enterprise-numbers
# TasNetworks doens't seem to have one so we will use ANUs for the time being
# ANU PEN = 28547
private_enterprise_number = 28457

# This is derived from the client certificate
# and will be supplied to the aggregator/client
aggregator_lfdi = "0x21352135135"  # 2282004631861


class MeterValueTypeDecodeError(Exception):
    pass


class MeterValueConversionError(Exception):
    pass


def get_autoincrementing_id() -> int:
    """Generates an auto-incrementing id.

    Args:
      base: see above

    Returns:
      A unique id (one larger than the previous call)
    """
    # initialize a static variable called counter
    if "counter" not in get_autoincrementing_id.__dict__:
        get_autoincrementing_id.counter = 0
    get_autoincrementing_id.counter += 1
    return int(get_autoincrementing_id.counter)


def generate_mrid(provider_id: int, pen: int) -> str:
    """Generates a globally unique master resource ID (mRID)

    mRID are 120 bits.
    +--------------------------+-------------------+
    |  provider_id (96 bits)   |  PEN (32 bits)    |
    +--------------------------+-------------------+

    When the provider_id is combined with the PEN it must form
    a globally unique identifier

    Args:
      provider_id: int
      pen: IANA Private Enterprise Number of the organisation/provider

    Returns:
      A new unique mRID as hexadecimal string
    """
    return hex((provider_id << 32) + pen)


def convert_timestamps(
    start_timestamp: str, end_timestamp: str = None
) -> DateTimeIntervalType:
    """Creates a DateTimeInterval from two timestamps.

    Args:
      start_timestamp: A Dateutil parseable timestamp string for the start of the time
        period
      end_timestamp: A Dateutil parseable timestamp string for the start of the time
        period or None.If no end_timestamp is supplied. The duration of the
        DataTimeInterval will be 0.

    Returns:
      A new DateTimeIntervalType object

    Raises:
      ParserError: If either the start_timestamp or end_timestamp cannot be parsed by
        dateutil.parser.parse
    """

    start_datetime = parse(start_timestamp)
    if end_timestamp is None:
        end_datetime = start_datetime
    else:
        end_datetime = parse(end_timestamp)

    duration = (end_datetime - start_datetime).seconds
    start = int(start_datetime.timestamp())
    return DateTimeIntervalType(duration=duration, start=start)


def parse_jetcharge_meter_value(value: str) -> int:
    try:
        return round(float(value))
    except ValueError:
        raise MeterValueConversionError


jetcharge_api_v3_meter_type_descriptions = {
    "l1VoltageV": "Phase A Voltage (V) Set",
    "l2VoltageV": "Phase B Voltage (V) Set",
    "l3VoltageV": "Phase C Voltage (V) Set",
    "l1CurrentA": "Phase A Current (A) Set",
    "l2CurrentA": "Phase B Current (A) Set",
    "l3CurrentA": "Phase C Current (A) Set",
    "totalActiveEnergyWh": "Total Active Energy (Wh) Set",
    "totalReactiveEnergyWh": "Total Reactive Energy (Wh) Set",
    "soc": "State of Charge (0-100) Set",
    "frequency": "Frequency (Hz) Set",
}


def create_mirror_reading_set(
    meter_reading_type: str, meter_readings: List[Dict], private_enterprise_number: int
) -> MirrorReadingSet:
    """Creates a Mirror Reading Set for a desired meter reading type.

    Args:
      meter_reading_type: The JetCharge meter reading type, for example, "l1CurrentA"
      meter_readings: List of meter readings obtained by from JetCharge API
                      transactionMeterValues Endpoint
      private_enterprise_number: IANA Private Enterprise Number

    Returns:
      A new 2030.5 Mirror Reading Set
    """

    # Create a 2030.5 reading for each (Jetcharge) meter_reading
    readings = []
    for meter_reading in meter_readings:
        readings.append(
            Reading(
                time_period=convert_timestamps(meter_reading["timestampUtc"]),
                value=parse_jetcharge_meter_value(meter_reading[meter_reading_type]),
            )
        )

    # Calculate time period of whole set of meter readings
    reading_set_start = meter_readings[0]["timestampUtc"]
    reading_set_end = meter_readings[-1]["timestampUtc"]
    time_period = convert_timestamps(
        start_timestamp=reading_set_start, end_timestamp=reading_set_end
    )

    description = jetcharge_api_v3_meter_type_descriptions[meter_reading_type]
    mrid = generate_mrid(get_autoincrementing_id(), private_enterprise_number)

    return MirrorReadingSet(
        description=description,
        mrid=mrid,
        version=VersionType(0),
        time_period=time_period,
        reading=readings,
    )


def create_all_reading_types(metering_types: List[str]) -> Dict[str, ReadingType]:
    reading_types = {}
    for metering_type in metering_types:
        try:
            reading_types[
                metering_type
            ] = create_reading_type_from_jetcharge_meter_value_type(metering_type)
        except MeterValueTypeDecodeError:
            pass
    return reading_types


def decode_phase_quantity_meter_value_type(
    meter_value_type: str,
) -> Tuple[UomType, PhaseCode]:
    """Decode JetCharge phase-quantity-style meter value types.

    Args:
      meter_value_type: A JetCharge meter_value_type in the phase-quantity form:
        "l3CurrentA" and "l1VoltageV"

    Returns:
      Tuple containing the UomType and PhaseCode for the meter_value_type

    Raises:
      MeterValueTypeDecodeError: If the UomType and PhaseCode couldn't be determined
       for the argument, meter_value_type.

    Examples:
      >>> decode_phase_quantity_meter_value_type("l1VoltageV")
      (<UomType.Voltage: 29>, <PhaseCode.Phase_A: 128>)
      >>> decode_phase_quantity_meter_value_type("l3CurrentA")
      (<UomType.Amperes: 5>, <PhaseCode.Phase_C: 32>)
    """

    # Determine the phase
    PHASE_MAPPING = {1: PhaseCode.Phase_A, 2: PhaseCode.Phase_B, 3: PhaseCode.Phase_C}
    try:
        phase_index = int(meter_value_type[1])
        phase = PHASE_MAPPING[phase_index]
    except (IndexError, ValueError):
        msg = f"Unable to decode phase of meter_value_type: {meter_value_type}"
        logging.error(msg)
        raise MeterValueTypeDecodeError(msg)

    # Determine the quantity, for example, voltage or current
    QUANTITY_MAPPING = {"VoltageV": UomType.Voltage, "CurrentA": UomType.Amperes}
    try:
        quantity_str = meter_value_type[2:]
        uom = QUANTITY_MAPPING[quantity_str]
    except (IndexError, ValueError):
        msg = f"Unable to decode quantity of meter_value_type: {meter_value_type}"
        logging.error(msg)
        raise MeterValueTypeDecodeError(msg)

    return uom, phase


def create_reading_type_from_jetcharge_meter_value_type(
    meter_value_type: str,
) -> ReadingType:
    """Convert a JetCharge meter_value_type into a 2030.5 ReadingType.

    The following meter_value_types are supported:
    1. Values with Phases
      - "lnVoltageV", where n=1,2, or 3 e.g. "l1VoltageV"
      - "lnCurrentA", where n=1,2, or 3 e.g. "l3CurrentA"
    2. Values with Phases
      - "totalActiveEnergyWh"
      - "totalReactiveEnergyWh"
      - "frequency"
      - "soc"

    Args:
      meter_value_type: A JetCharge meter_value_type

    Returns:
      A new ReadingType (2030.5) matching the meter_value_type (JetCharge)

    Raises:
      MeterValueTypeDecodeError: If the UomType and PhaseCode couldn't be determined
       for the argument, meter_value_type.
    """
    if meter_value_type == "totalActiveEnergyWh":
        uom = UomType.Wh
        phase = PhaseCode.Not_applicable
    elif meter_value_type == "totalReactiveEnergyWh":
        uom = UomType.VArh
        phase = PhaseCode.Not_applicable
    elif meter_value_type == "frequency":
        uom = UomType.Hz
        phase = PhaseCode.Not_applicable
    elif meter_value_type == "soc":
        # State of charge, 0-100. Currently only available for DC chargers
        # TODO Can we handle these kinds of values?
        uom = UomType.Not_applicable
        phase = PhaseCode.Not_applicable
    else:
        # Decode "l3CurrentA" and "l1VoltageV" style meter value types.
        uom, phase = decode_phase_quantity_meter_value_type(meter_value_type)

    return ReadingType(
        interval_length=0,
        power_of_ten_multiplier=0,
        uom=uom,
        phase=phase,
    )


def create_mirror_meter_reading() -> MirrorMeterReading:
    return MirrorMeterReading()


def create_mup(device_lfdi: str) -> MirrorUsagePoint:
    # "@xmlns": "urn:ieee:std:2030.5:ns"
    mrid = generate_mrid(
        provider_id=get_autoincrementing_id(), pen=private_enterprise_number
    )
    return MirrorUsagePoint(
        mrid=mrid,
        description="JetCharge Chargers",
        role_flags=RoleFlagsType.IsMirror,
        service_category_kind=ServiceKind.Electricity,
        status="1",
        device_lfdi=device_lfdi,
    )


def create_aggregator_client(
    server_url: str,
    certificate_path: str,
    key_path: str,
    aggregator_lfdi: str,
    use_ssl_auth: bool = True,
) -> EndDeviceInterface:
    """Creates a 2030.5 aggregator client with the requested authentication.

    The client is used by aggregators to interface to a 2030.5 server. SSL
    encryption is the default. Disabling SSL encryption (use_ssl_auth=False)
    will only work with a locally deployed servers that have been configured to
    accept unencrypted connections. In this a certificate_path and key_path is
    not required.

    Args:
      server_url: The URL of the 2030.5 server.
      certificate_path: A path to the certificate used for SSL encryption.
      key_path: A path to the key used for SSL encryption.
      aggregator_lfdi: The lFDI of the aggregator as a hex string e.g.
                       "0x1234567890"
      use_ssl_auth: If True uses the certificate given by certificate path to
                    provide SSL encrypted communications to the server.
                    If False no SSL encryption is used.

    Returns:
      The new EndDeviceInterface.
    """
    auth = None
    if use_ssl_auth:
        auth = ClientCerticateAuth((certificate_path, key_path))
    else:
        auth = LocalModeXTokenAuth(aggregator_lfdi)
    transport = RequestsTransport(server_url, auth=auth)
    return EndDeviceInterface(
        transport=transport,
        lfdi=aggregator_lfdi,
    )


def get_jetcharge_metering_types_for_non_none_values(meter_value: Dict) -> List[str]:
    all_types = get_jetcharge_metering_types(meter_value)
    non_none_types = []
    for type in all_types:
        if meter_value[type] != "None":
            non_none_types.append(type)
    return non_none_types


def get_jetcharge_metering_types(meter_value: Dict) -> List[str]:
    """Determine the metering types available."""

    keys_to_exclude = ["id", "timestampUtc"]
    for key_to_exclude in keys_to_exclude:
        meter_value.pop(key_to_exclude, None)
    return list(meter_value.keys())


def process_meter_values_from_file(
    json_filepath: str, mup_id: int, client: EndDeviceInterface
):
    with open(json_filepath, "r") as fh:
        meter_values_response = json.load(fh)
    meter_values = meter_values_response["meterValues"]

    metering_types = get_jetcharge_metering_types_for_non_none_values(
        meter_values[0].copy()
    )
    reading_types = create_all_reading_types(metering_types)

    for meter_type, reading_type in reading_types.items():
        mrid = generate_mrid(
            provider_id=get_autoincrementing_id(), pen=private_enterprise_number
        )
        mmr = MirrorMeterReading(
            mrid=mrid,
            reading_type=reading_type,
            mirror_reading_set=create_mirror_reading_set(meter_type, meter_values),
        )

        # print(json.dumps(mmr.dict(exclude_unset=True), indent=4))
        bs = BeautifulSoup(mmr.to_xml(mode="create"), "xml")
        print(bs.prettify())
        response = client.create_mirror_meter_reading(
            mup_id=mup_id, mirror_meter_reading=mmr
        )
        print(response.content)


jetcharge_api_v3_metering_types = [
    "l1VoltageV",
    "l2VoltageV",
    "l3VoltageV",
    "l1CurrentA",
    "l2CurrentA",
    "l3CurrentA",
    "totalActiveEnergyWh",
    "totalReactiveEnergyWh",
    "soc",
    "frequency",
]


def get_available_meter_types(meter_value: Dict[str, Any]) -> List[str]:
    """List of available JetCharge meter reading types

    The possible meter reading types are determined from meter_value argument.
    The meter types have values such as "l1VoltageV" and "totalActiveEnergyWh".
    "Available" meter types have an assigned values (their value is not "None").

    Args:
      meter_value:
      Example meter_value:
      {
        "id":1400682,
        "timestampUtc":"2021-09-22T21:27:51Z",
        "l1VoltageV":238.03,
        "l2VoltageV":"None",
        ...
      }

    Returns:
      A list of meter readings types
    """
    meter_types = []
    for jetcharge_api_v3_meter_type in jetcharge_api_v3_metering_types:
        if jetcharge_api_v3_meter_type in meter_value:
            if meter_value[jetcharge_api_v3_meter_type] != "None":
                meter_types.append(jetcharge_api_v3_meter_type)
    return meter_types


def generate_mirror_meter_readings(meter_values: List[Dict[str, Any]]) -> List:
    """Convert JetCharge meter readings to 2030.5 Mirror Meter Readings

    Args:
      meter_values: List of JetCharge meter readings obtained from a request to
                    the JetCharge API endpoint, transactionMeterValues
      Example meter_values:
      [
        {
          "id":1400682,
          "timestampUtc":"2021-09-22T21:27:51Z",
          "l1VoltageV":238.03,
          "l2VoltageV":"None",
          ...
        },
        ...
      ]

    Yields:
        A new MirrorMeterReading for each meter reading that has assigned values.
        (Unassigned readings have the value "None" and are ignored)
    """
    if not meter_values:
        return  # End the generator because there are no meter_values

    for meter_type in get_available_meter_types(meter_values[0]):
        reading_type = create_reading_type_from_jetcharge_meter_value_type(meter_type)
        mrid = generate_mrid(
            provider_id=get_autoincrementing_id(), pen=private_enterprise_number
        )
        yield MirrorMeterReading(
            mrid=mrid,
            reading_type=reading_type,
            mirror_reading_set=create_mirror_reading_set(meter_type, meter_values),
        )


def process_meter_values_from_file_with_generator(
    json_filepath: str, mup_id: int, client: EndDeviceInterface
):
    # Read the meter values in from file
    with open(json_filepath, "r") as fh:
        meter_values_response = json.load(fh)
    meter_values = meter_values_response["meterValues"]

    for mirror_meter_reading in generate_mirror_meter_readings(meter_values):
        # print(json.dumps(mirror_meter_reading.dict(exclude_unset=True), indent=4))
        bs = BeautifulSoup(mirror_meter_reading.to_xml(mode="create"), "xml")
        print(bs.prettify())
        response = client.create_mirror_meter_reading(
            mup_id=mup_id, mirror_meter_reading=mirror_meter_reading
        )
        print(response)


def main():

    client = create_aggregator_client(
        server_url, certificate_path, key_path, aggregator_lfdi, use_ssl_auth=False
    )

    for i in client.get_paged_mups():
        print(i)
        print("-------------------------------------")
    return

    device_lfdi = "0x4a65744368617267653a434d303035363a"
    mup = create_mup(device_lfdi)
    response = client.create_mup(mup)
    mup_id = trailing_resource_id_from_response(response)

    jetcharge_meter_values_file = "scripts/jetcharge_meter_values.json"

    # process_meter_values_from_file(jetcharge_meter_values_file, mup_id, client)
    process_meter_values_from_file_with_generator(
        jetcharge_meter_values_file, mup_id, client
    )


if __name__ == "__main__":
    main()
