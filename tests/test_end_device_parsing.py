
import xmltodict

from envoy_client.models import EndDevice, EndDeviceList, DeviceCategoryType

import random

def random_lfdi():
    return hex(random.randint(10e12, 10e13))

def test_end_device_creation():
    end_device = EndDevice()


def test_end_device_serialisation_deserialisation():
    end_device = EndDevice(
        lfdi=random_lfdi(),
        device_category=DeviceCategoryType.electric_vehicle
    )

    xml = xmltodict.unparse(end_device.xml_dict(by_alias=True), full_document=False)
    rehydrated_end_device = EndDevice(**xmltodict.parse(xml)['EndDevice'])

    print(rehydrated_end_device)