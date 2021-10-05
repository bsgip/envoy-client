import logging
import os

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

# This is derived from the client certificate
# and will be supplied to the aggregator/client
aggregator_lfdi = "0x21352135135"  # 2282004631861


def get_mock_end_device() -> EndDevice:
    # The LFDI will normally be derived from an internal aggregator globally
    # unique identifier for each system
    # The lfdi should always be a string in hexadecimal
    # If you supply a decimal, it will get coerced to a string and on
    # the server side converted from "hex" to a decimal giving the wrong
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


def register_device(client: EndDeviceInterface, end_device: EndDevice):
    # POST EndDevice
    response = client.create_end_device(end_device)
    if response.status_code != 201:
        logging.warning(response.content)
        return
    edev_id = trailing_resource_id_from_response(response)

    # PUT DeviceInformation
    response_di = client.create_device_information(
        end_device.device_information, edev_id=edev_id
    )
    if response_di.status_code != 200:
        logging.warning(response_di.content)
        return

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


def register_devices(client: EndDeviceInterface, devices: list) -> bool:
    result = True
    for device in devices:
        result = register_device(client, device)
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


def read_device_data() -> list:
    return [get_mock_end_device()]


def main():
    devices = read_device_data()
    client = create_aggregator_client(
        server_url, certificate_path, aggregator_lfdi, use_ssl_auth=False
    )
    register_devices(client, devices)


if __name__ == "__main__":
    main()
