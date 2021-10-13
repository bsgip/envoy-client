import codecs
import json
import logging
import os
from typing import List

from envoy_client.auth import ClientCerticateAuth, LocalModeXTokenAuth
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
    aggregator_lfdi: str,
    use_ssl_auth: bool = True,
) -> EndDeviceInterface:
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


def get_device_category_from_jetcharge_device_type(
    device_type: str,
) -> DeviceCategoryType:
    mapper = {
        "ChargePoint": DeviceCategoryType.electric_vehicle_supply_equipment
    }
    try:
        return mapper[device_type]
    except KeyError:
        return DeviceCategoryType.virtual_or_mixed_der


def get_autoincrementing_lfdi(base: int = 0) -> str:
    # initialize a static variable called counter
    if "counter" not in get_autoincrementing_lfdi.__dict__:
        get_autoincrementing_lfdi.counter = 0
    get_autoincrementing_lfdi.counter += 1
    return hex(base + get_autoincrementing_lfdi.counter)


class LFDIInsufficientLengthError(Exception):
    pass


def get_local_lfdi_from_string(s: str) -> str:
    SFDI_LENGTH_IN_BITS_WITHOUT_CHECKSUM = 36
    lfdi = s.encode("utf-8").hex()
    if int(lfdi, 16).bit_length() < SFDI_LENGTH_IN_BITS_WITHOUT_CHECKSUM:
        raise LFDIInsufficientLengthError(
            "Generated LFDI has insufficient number of bits"
            / " to generate corresponding SFDI"
        )
    return lfdi


def get_string_from_local_lfdi(local_lfdi: str) -> str:
    return codecs.decode(local_lfdi, "hex").decode("utf-8")


def get_local_lfdi_from_jetcharge_device(jetcharge_device: dict) -> str:
    full_device_identifier = (
        "JetCharge" + ":" + jetcharge_device["deviceIdentity"] + ":" + ""
    )
    return get_local_lfdi_from_string(full_device_identifier)


class InvalidJetChargeLFDIError(Exception):
    pass


def get_jetcharge_device_identity_from_lfdi(jetcharge_lfdi: str) -> str:
    full_device_identifier = get_string_from_local_lfdi(jetcharge_lfdi)
    try:
        return full_device_identifier.split(":")[1]
    except IndexError:
        raise InvalidJetChargeLFDIError(
            "LFDI is malformed or not a valid JetCharge LFDI"
        )


def get_end_device_from_jetcharge_device(jetcharge_device: dict):
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


def read_device_data(mock=False) -> List[EndDevice]:
    if mock:
        return [get_mock_end_device()]

    with open(jetcharge_response_path, mode="r") as file:
        try:
            jetcharge_response = json.load(file)
        except json.JSONDecodeError:
            logging.error("Unable to decode jetcharge response")

    devices = []
    if jetcharge_response:
        for device in jetcharge_response["devices"]:
            end_device = get_end_device_from_jetcharge_device(device)
            devices.append(end_device)
    return devices


def main(dry_run=True):
    devices = read_device_data()
    client = create_aggregator_client(
        server_url, certificate_path, aggregator_lfdi, use_ssl_auth=False
    )
    if not dry_run:
        register_devices(client, devices)


if __name__ == "__main__":
    main(dry_run=False)
