from typing import List, Optional

import xmltodict

from .transport import Transport
from .auth import Auth
from .models import DER, DeviceCategoryType, DeviceInformation, EndDevice, EndDeviceList, \
    DERCapability, ConnectionPoint

import logging
logger = logging.getLogger(__name__)

class AggregatorClient:
    def __init__(self, transport: Transport, lfdi: str) -> None:
        self.transport = transport
        self.lfdi = lfdi
        self.transport.connect()

    def get_end_devices(self, include_self=False) -> Optional[EndDeviceList]:
        """Retrieve all associated `EndDevice`s.

        # TODO This currently retrieves all devices in one query. At scale, this should
        be paginated

        Args:
            include_self (bool, optional): Whether to include or ignore the first device, which
                will represent the aggregator. Defaults to False.
        
        Returns:
            List of `EndDevice`s (as an `EndDeviceList`)
        """
        response = self.transport.get('/edev')
        if response:
            response_dct = xmltodict.parse(response.content)['EndDeviceList']
            if 'EndDevice' not in response_dct:
                logger.warning('No EndDevices returned in response')
                return None
            end_device_list = EndDeviceList(**response_dct)
            return end_device_list

    def create_end_device(self, end_device: EndDevice):
        return self.transport.post('/edev', end_device.to_xml(mode='create'))

    def create_device_information(self, device_information: DeviceInformation, edev_id: int):
        return self.transport.post(f'/edev/{edev_id}/di', device_information.to_xml(mode='create'))

    def create_der(self, der: DER, edev_id: int):
        return self.transport.post(f'/edev/{edev_id}/der', der.to_xml(mode='create'))

    def create_der_capability(self, der_capability: DERCapability, edev_id: int, der_id: int):
        return self.transport.post(f'/edev/{edev_id}/der/{der_id}/derc', der_capability.to_xml(mode='create'))

    def create_connection_point(self, connection_point: ConnectionPoint, edev_id: int):
        return self.transport.post(f'/edev/{edev_id}/cp', connection_point.to_xml(mode='create'))
    
    @property
    def self_device(self):
        return EndDevice(lfdi=self.lfdi, device_category=DeviceCategoryType.virtual_or_mixed_der)

    def create_self_device(self):
        return self.create_end_device(self.self_device)

    def get_end_device(self, resource_location):
        return EndDevice.from_xml(self.transport.get(resource_location).content)

    def create_end_devices(self, end_devices: List[EndDevice], create_der=False, abort_on_error=True) -> None:
        """Create the complete `EndDeviceList` on the server. This assumes all
        devices are to be created and will (optionally) create all DER linked to these
        devices.

        This function adds each `EndDevice` in an individual call.

        Args:
            end_device_list (EndDeviceList): `EndDeviceList` to add.
            create_der (bool): Optionally create linked `DER` assets in addition to the 
                `EndDevice`
            abort_on_error (bool): Abort creation of devices after first error
        """
        errors = []
        for end_device in end_devices: 
            self.create_end_device(end_device)
        return

    def reconcile_end_devices(self, server_device_list: EndDeviceList, client_device_list: EndDeviceList) -> None:
        raise NotImplementedError

