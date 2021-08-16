

from envoy_client.models import *
from envoy_client.client import AggregatorClient
from envoy_client.transport import DocumentationGeneratingTransport

aggregator_lfdi = '0x21352135135'

client = AggregatorClient(
    transport=DocumentationGeneratingTransport('https://server-location', auth=None),
    lfdi=aggregator_lfdi
)

lfdi = 0x000111100001111
end_device = EndDevice(
    lfdi=lfdi, 
    device_category=DeviceCategoryType.combined_pv_and_storage,
    device_information=DeviceInformation(
        functions_implemented=FunctionsImplementedType.der_control,
        gps_location=GPSLocationType(lat=-35.0, lon=144.0),
        lFDI=lfdi,
    ),
    der=[DER(der_capability=DERCapability(
        type=DERType.combined_pv_storage,
        rtg_max_w=ValueWithMultiplier(value=5000)
    ))]
)

client.create_end_device(end_device)
client.create_der(end_device.der[0], edev_id=3)
client.create_der_capability(end_device.der[0].der_capability, edev_id=3, der_id=5)
client.create_device_information(end_device.device_information, 3)
