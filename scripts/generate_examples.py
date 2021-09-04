import uuid

from envoy_client.models import *
from envoy_client.interface import EndDeviceInterface, trailing_resource_id_from_response
from envoy_client.transport import MockTransport, RequestsTransport
from envoy_client.auth import LocalModeXTokenAuth

# This is derived from the client certificate and will be supplied to the aggregator/client
aggregator_lfdi = '0x21352135135'  


client = EndDeviceInterface(
    transport=MockTransport('https://server-location', auth=None),
    lfdi=aggregator_lfdi
)

mmr = MirrorMeterReading(
    mrid=int(str(uuid.uuid4()).replace('-', ''), 16),
    description="Random meter reading",
    reading_type=ReadingType(
        kind=KindType.Power,
        power_of_ten_multiplier=0,
        uom=UomType.W,
        phase=PhaseCode.Phase_A
    ),
    reading=Reading(
        time_period=DateTimeIntervalType(duration=300, start=0),
        value=4000
    )
)

mmr.to_xml()

# The LFDI will normally be derived from an internal aggregator globally unique identifier
# for each system
lfdi = 0x0001111000011f
end_device = EndDevice(
    lfdi=lfdi, 
    device_category=DeviceCategoryType.combined_pv_and_storage,
    device_information=DeviceInformation(
        functions_implemented=FunctionsImplementedType.der_control,
        gps_location=GPSLocationType(lat=-35.0, lon=144.0),
        lFDI=lfdi,
        mf_id=1234567,
        mf_info='Acme Corp',
        mf_model='Acme 2000 Pro+',
        mf_ser_num='ACME1234'
    ),
    der=[DER(der_capability=DERCapability(
        type=DERType.combined_pv_storage,
        rtg_max_w=ValueWithMultiplier(value=5000),
        rtg_max_wh=ValueWithMultiplier(value=10000)
    ))],
    connection_point=ConnectionPoint(
        meter_id='NMI123'
    )
)


# POST EndDevice
response = client.create_end_device(end_device)
edev_id = trailing_resource_id_from_response(response)

# PUT DeviceInformation
client.create_device_information(end_device.device_information, edev_id=edev_id)

# POST DER
# Note: normally there will only be one `DER`, it is possible however to have multiple
# as demonstrated here.
der_ids = []
for der in end_device.der:
    response = client.create_der(der, edev_id=edev_id)
    der_id = trailing_resource_id_from_response(response)
    der_ids.append(der_id)

# PUT DERCapability
for (der_id, der) in zip(der_ids, end_device.der):
    client.create_der_capability(der.der_capability, edev_id=edev_id, der_id=der_id)

# POST ConnectionPoint
client.create_connection_point(end_device.connection_point, edev_id=edev_id)


mup = MirrorUsagePoint(
    mrid=str(uuid.uuid4()),
    description="Random mirror usage point",
    role_flags=RoleFlagsType.IsDER | RoleFlagsType.IsMirror,
    service_category_kind=ServiceKind.Electricity,
    status=1,
    device_lfdi=end_device.lfdi
)

response = client.create_mup(mup)
mup_id = trailing_resource_id_from_response(response)

mmr = MirrorMeterReading(
    mrid=int(str(uuid.uuid4()).replace('-', ''), 16),
    description="Random meter reading",
    reading_type=ReadingType(
        kind=KindType.Power,
        power_of_ten_multiplier=0,
        uom=UomType.W,
        phase=PhaseCode.Phase_A
    ),
    reading=Reading(
        time_period=DateTimeIntervalType(duration=300, start=0),
        value=4000
    )
)


client.create_mirror_meter_reading(mup_id=mup_id, mirror_meter_reading=mmr)