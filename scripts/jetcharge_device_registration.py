import codecs
import json
import logging
import os
from typing import List

from envoy_client.auth import ClientCertificateAuth, LocalModeXTokenAuth
from envoy_client.interface import (
    EndDeviceInterface,
    trailing_resource_id_from_response,
)
from envoy_client.models import (
    DER,
    ConnectionPoint,
    DERCapability,
    DERType,
    DeviceCategoryType,
    DeviceInformation,
    EndDevice,
    FunctionsImplementedType,
    GPSLocationType,
    ValueWithMultiplier,
)
from envoy_client.transport import RequestsTransport

logging.basicConfig(level=logging.DEBUG)

server_url = os.getenv("ENVOY_SERVER_URL")
certificate_path = os.getenv("ENVOY_CERTIFICATE_PATH")
key_path = os.getenv("ENVOY_KEY_PATH")
jetcharge_response_path = os.getenv("JETCHARGE_RESPONSE_PATH")

# This is derived from the client certificate
# and will be supplied to the aggregator/client
aggregator_lfdi = "0x21352135135"  # 2282004631861


def get_mock_end_device() -> EndDevice:
    """Creates a mock (placeholder) EndDevice.

    Returns:
      A new EndDevice object mocked with hard-coded data.
    """
    # The LFDI will normally be derived from an internal aggregator globally
    # unique identifier for each system
    # The lfdi should always be a string in hexadecimal
    # If you accidentally supply a decimal, it will get coerced to a string
    # and on the server side converted from "hex" to a decimal giving the wrong
    # value
    lfdi = "0x0001111000011F"  # 1172794507551
    return EndDevice(
        lfdi=lfdi,
        device_category=DeviceCategoryType.combined_pv_and_storage,
        device_information=DeviceInformation(
            functions_implemented=FunctionsImplementedType.der_control,
            gps_location=GPSLocationType(lat=-35.0, lon=144.0),
            lFDI=lfdi,
            mf_id=1234567,
            mf_model="Acme 2000 Pro+",
            mf_ser_num="ACME1234",
        ),
        der=[
            DER(
                der_capability=DERCapability(
                    type=DERType.combined_pv_and_storage,
                    rtg_max_w=ValueWithMultiplier(value=5000),
                    rtg_max_wh=ValueWithMultiplier(value=10000),
                )
            )
        ],
        connection_point=ConnectionPoint(meter_id="NMI123"),
    )


def register_device(client: EndDeviceInterface, end_device: EndDevice) -> bool:
    """Registers an EndDevice with a 2030.5 server.

    The full EndDevice registration is a multi-step process involving the
    creation of EndDevice, DeviceInformation, DER and DERCapability.
    If the EndDevice already exists on the server (i.e. an EndDevice with
    the same lFDI is found), the registration process does not continue and a
    value of True is returned.

    Args:
      client: A 2030.5 client interface (EndDeviceInterface)
      end_device: The EndDevice object to be registered

    Returns:
      True if the device registration was successful.
    """
    # POST EndDevice
    response = client.create_end_device(end_device)

    if response.status_code == 200:  # OK (Device already exists)
        edev_id = trailing_resource_id_from_response(response)
        logging.warning(f"Device already exists. [edev_id={edev_id}]")
        return True
    elif response.status_code != 201:  # something went wrong
        logging.warning(response)
        return False

    edev_id = trailing_resource_id_from_response(response)

    # PUT DeviceInformation
    response_di = client.create_device_information(
        end_device.device_information, edev_id=edev_id
    )
    if response_di.status_code != 200:
        logging.warning(response_di)
        return False

    # POST DER
    # Note: normally there will only be one `DER`,
    # it is possible however to have multiple
    # as demonstrated here.
    der_ids = []
    for der in end_device.der:
        response = client.create_der(der, edev_id=edev_id)
        der_id = trailing_resource_id_from_response(response)
        der_ids.append(der_id)

    # PUT DERCapability
    for (der_id, der) in zip(der_ids, end_device.der):
        response = client.create_der_capability(
            der.der_capability, edev_id=edev_id, der_id=der_id
        )

    # # Ignore since not part of the core 2030.5 server
    # # POST ConnectionPoint
    # response = client.create_connection_point(
    #     end_device.connection_point, edev_id=edev_id
    # )

    return True


def register_devices(client: EndDeviceInterface, devices: list) -> bool:
    """Registers a list of devices with a 2030.5 server

    Args:
      client: A 2030.5 client interface (EndDeviceInterface)
      devices: A list of EndDevices to register

    Returns:
      True if all devices were registered successfully.
    """
    result = True
    for device in devices:
        result = register_device(client, device)
        logging.info(f"Registered {device.lfdi}")
        if not result:
            break
    return result


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
        auth = ClientCertificateAuth((certificate_path, key_path))
    else:
        auth = LocalModeXTokenAuth(aggregator_lfdi)
    transport = RequestsTransport(server_url, auth=auth)
    return EndDeviceInterface(
        transport=transport,
        lfdi=aggregator_lfdi,
    )


def get_device_category_from_jetcharge_device_type(
    device_type: str,
) -> DeviceCategoryType:
    """Converts a JetCharge device_type to a 2030.5 DeviceCategoryType.

    Args:
      device_type: Jetcharge Device Type.

    Returns:
      The corresponding DeviceCategoryType or
      DeviceCategoryType.virtual_or_mixed_der if no suitable mapping found.
    """
    mapper = {"ChargePoint": DeviceCategoryType.electric_vehicle_supply_equipment}
    try:
        return mapper[device_type]
    except KeyError:
        return DeviceCategoryType.virtual_or_mixed_der


def get_autoincrementing_lfdi(base: int = 0) -> str:
    """Generates an auto-incrementing lfdi.

    Generated lfdi = base + offset
    offset starts at 1 and increases by 1 after
    each call to this function.

    NOTE: Use for testing purposes only

    Args:
      base: see above

    Returns:
      A unique lfdi (one larger than the previous call)
    """
    # initialize a static variable called counter
    if "counter" not in get_autoincrementing_lfdi.__dict__:
        get_autoincrementing_lfdi.counter = 0
    get_autoincrementing_lfdi.counter += 1
    return hex(base + get_autoincrementing_lfdi.counter)


class LFDIInsufficientLengthError(Exception):
    pass


def get_local_lfdi_from_string(s: str) -> str:
    """Generates a local LFDI from an arbitrary string.

    NOTE: Use for testing purposes only (hence _local_ LFDI)

    Args:
      s: Arbitrary string of sufficient length to be converted into a local
         LFDI. In practice this means a string of at least with length >= 5
         ascii characters.

    Returns:
      A new (local) LFDI.

    Raises:
      LFDIInsufficientLengthError: when the argument s is too short to generate
      an LFDI of sufficient length.
    """
    SFDI_LENGTH_IN_BITS_WITHOUT_CHECKSUM = 36
    lfdi = s.encode("utf-8").hex()
    if int(lfdi, 16).bit_length() < SFDI_LENGTH_IN_BITS_WITHOUT_CHECKSUM:
        raise LFDIInsufficientLengthError(
            "Generated LFDI has insufficient number of bits"
            / " to generate corresponding SFDI"
        )
    return lfdi


def get_string_from_local_lfdi(local_lfdi: str) -> str:
    """Converts a local LFDI back into the string that generated it.

    See the complimentary function: get_local_lfdi_from_string(str).

    Args:
      local_lfdi: An LFDI generated with the get_local_lfdi_from_string(str)
                  function.

    Returns:
      The string that generated the local LFDI.
    """
    return codecs.decode(local_lfdi, "hex").decode("utf-8")


def get_local_lfdi_from_jetcharge_device(jetcharge_device: dict) -> str:
    """Generates a local LFDI from a jetcharge device.

    Args:
      jetcharge_device: dict containing an end device obtained from the
                        JetCharge v3 API
      Example jetcharge device,
      {
        "deviceType": "ChargePoint",
        "deviceIdentity": "CM0056",
        "status": "Available",
        "online": True,
        "childDevices": None
      }

    Returns:
      Local LFDI
    """
    full_device_identifier = (
        "JetCharge" + ":" + jetcharge_device["deviceIdentity"] + ":" + ""
    )
    return get_local_lfdi_from_string(full_device_identifier)


class InvalidJetChargeLFDIError(Exception):
    pass


def get_jetcharge_device_identity_from_lfdi(jetcharge_lfdi: str) -> str:
    """Returns the JetCharge device identity from a local LFDI.

    Args:
      jetcharge_lfdi: JetCharge LFDI generated with
                      get_local_lfdi_from_jetcharge_device(dict)

    Returns:
      Jetcharge device_identity

    Raises:
      InvalidJetChargeLFDIError: if the LFDI can't be decoded.
    """
    full_device_identifier = get_string_from_local_lfdi(jetcharge_lfdi)
    try:
        return full_device_identifier.split(":")[1]
    except IndexError:
        raise InvalidJetChargeLFDIError(
            "LFDI is malformed or not a valid JetCharge LFDI"
        )


def get_end_device_from_jetcharge_device(jetcharge_device: dict):
    """Creates a 2030.5 EndDevice from a JetCharge Device.

    Args:
      jetcharge_device: dict containing an end device obtained from the
                        JetCharge v3 API
      Example jetcharge device,
      {
        "deviceType": "ChargePoint",
        "deviceIdentity": "CM0056",
        "status": "Available",
        "online": True,
        "childDevices": None
      }

    Returns:
      The new 2030.5 EndDevice object.
    """
    lfdi = get_local_lfdi_from_jetcharge_device(jetcharge_device)
    # lfdi = get_autoincrementing_lfdi(base=314159265358979)
    return EndDevice(
        lfdi=lfdi,
        device_category=get_device_category_from_jetcharge_device_type(
            jetcharge_device["deviceType"]
        ),
        device_information=DeviceInformation(
            lFDI=lfdi,
            mf_ser_num=jetcharge_device["deviceIdentity"],
        ),
    )


def read_device_data(json_path: str) -> List[EndDevice]:
    """Converts a json file to a list of 2030.5 EndDevices

    The file must contain json response from a JetCharge v3 API call
    to https://jetcharge-illuminate.azure-api.net/chargeData/v3/deviceList

    Args:
      json_path: Path to .json file containing deviceList response from
                 JetCharge v3 API.

    Returns:
      A list of 2030.5 EndDevices
    """
    with open(json_path, mode="r") as file:
        try:
            jetcharge_response = json.load(file)
        except json.JSONDecodeError:
            logging.error("Unable to decode JetCharge DeviceList response")

    devices = []
    if jetcharge_response:
        for device in jetcharge_response["devices"]:
            end_device = get_end_device_from_jetcharge_device(device)
            devices.append(end_device)
    return devices


def main():
    devices = read_device_data(jetcharge_response_path)
    client = create_aggregator_client(
        server_url, certificate_path, key_path, aggregator_lfdi, use_ssl_auth=False
    )
    register_devices(client, devices)


if __name__ == "__main__":
    main()
