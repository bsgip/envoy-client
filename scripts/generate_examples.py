

from envoy_client.models import *
from envoy_client.client import AggregatorClient
from envoy_client.transport import DocumentationGeneratingTransport, RequestsTransport
from envoy_client.auth import LocalModeXTokenAuth

aggregator_lfdi = '0x21352135135'

client = AggregatorClient(
    # transport=DocumentationGeneratingTransport('https://server-location', auth=None),
    transport=RequestsTransport('http://localhost:8004', auth=LocalModeXTokenAuth(aggregator_lfdi)),
    lfdi=aggregator_lfdi
)

lfdi = 0x000111100001121
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

print(client.create_end_device(client.self_device))

response = client.create_end_device(end_device)
print(response.headers['location'])

edev_id = int(response.headers['location'].split('/')[-1])

response = client.create_der(end_device.der[0], edev_id=edev_id)

der_id = int(response.headers['location'].split('/')[-1])

response = (client.create_der_capability(end_device.der[0].der_capability, edev_id=edev_id, der_id=der_id))

print(response.content)
print(client.create_device_information(end_device.device_information, edev_id=edev_id))
