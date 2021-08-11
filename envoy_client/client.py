from typing import List

import xmltodict

from .transport import Transport
from .auth import Auth
from .models import END_DEVICE_CREATE_TEMPLATE_KWARGS, EndDevice, EndDeviceList

import logging
logger = logging.getLogger(__name__)

class AggregatorClient:
    def __init__(self, transport: Transport, lfdi: str) -> None:
        self.transport = transport
        self.lfdi = lfdi

    def get_end_devices(self, include_self=False) -> EndDeviceList:
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
        print(response.content)
        print(xmltodict.parse(response.content)['EndDeviceList'])
        end_device_list = EndDeviceList(**xmltodict.parse(response.content)['EndDeviceList'])
        if not include_self and end_device_list.end_device:
            if end_device_list.end_device[0].lfdi == self.lfdi:
                end_device_list.end_device = end_device_list.end_device[1:]
            else:
                logger.warning('First EndDevice does not match client LFDI')
        return end_device_list

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
            self.transport.post('/edev', xmltodict.unparse(end_device.dict(**END_DEVICE_CREATE_TEMPLATE_KWARGS), full_document=False))
        return

    def reconcile_end_devices(self, server_device_list: EndDeviceList, client_device_list: EndDeviceList) -> None:
        raise NotImplementedError

