from typing import List, Optional

import xmltodict
import requests

from .transport import Transport
from .auth import Auth
from .models import DER, DeviceCategoryType, DeviceInformation, EndDevice, EndDeviceList, \
    DERCapability, ConnectionPoint

import logging
logger = logging.getLogger(__name__)


def trailing_resource_id_from_response(response: requests.Response) -> int:
    """Extract the resource ID from the response. Assumes that a `location` header is
    included in the response, indicating the location of the resource, and that the
    ID is the last part of the location path

    Args:
        response (requests.Response): response containing location header

    Raises:
        ValueError: location header not present in response

    Returns:
        int: resource ID
    """
    if hasattr(response, 'headers'):
        if 'location' in response.headers:
            return int(response.headers['location'].split('/')[-1])
    raise ValueError('Response object has no location resource.')

class AggregatorClient:
    """A 2030.5 aggregator client that functions according to the Common Smart Inverter Profile.

    Used to act on behalf of non-2030.5 devices (aggregator-mediated)
    """
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

    def create_end_device(self, end_device: EndDevice) -> requests.Response:
        """Register a 2030.5 `EndDevice` on the server
        """
        return self.transport.post('/edev', end_device.to_xml(mode='create'))

    def update_end_device(self, end_device: EndDevice, edev_id: int) -> requests.Response:
        """Update an EndDevice"""
        # TODO Untested
        return self.transport.put(f'/edev/{edev_id}', end_device.to_xml('create'))

    def create_device_information(self, device_information: DeviceInformation, edev_id: int):
        """Create or update an `EndDevice` `DeviceInformation` object
        """
        return self.transport.put(f'/edev/{edev_id}/di', device_information.to_xml(mode='create'))

    def create_der(self, der: DER, edev_id: int) -> requests.Response:
        """Create a new `DER` container associated with `EndDevice` with ID `edev_id`
        """
        return self.transport.post(f'/edev/{edev_id}/der', der.to_xml(mode='create'))

    def create_der_capability(self, der_capability: DERCapability, edev_id: int, der_id: int) -> requests.Response:
        """Create or update a `DER` `DERCapability` object associated with `DER` with ID `der_id`
        and `EndDevice` with ID `edev_id`
        """
        return self.transport.put(f'/edev/{edev_id}/der/{der_id}/dercap', der_capability.to_xml(mode='create'))

    def create_connection_point(self, connection_point: ConnectionPoint, edev_id: int) -> requests.Response:
        """Create a `ConnectionPoint` object on the server associated with `EndDevice` with
        ID `edev_id`. Note: this is an extension to the 2030.5 spec.
        """
        return self.transport.put(f'/edev/{edev_id}/cp', connection_point.to_xml(mode='create'))
    
    @property
    def self_device(self):
        """The `EndDevice` associated with the AggregatorClient.
        """
        return EndDevice(lfdi=self.lfdi, device_category=DeviceCategoryType.virtual_or_mixed_der)

    def create_self_device(self) -> requests.Response:
        """Create an `EndDevice` corresponding to the `SelfDevice` of the AggregatorClient
        """
        return self.create_end_device(self.self_device)

    def get_end_device(self, edev_id: int) -> Optional[EndDevice]:
        """Retrieve an `EndDevice` object from the server with ID `edev_id`"""
        response = self.transport.get(f'/edev/{edev_id}')
        if response.status_code == 200:
            return EndDevice.from_xml(response.content)
        logger.warning(f'No EndDevice found with edevID {edev_id}')
        return None

    def sync_end_device(self, end_device: EndDevice, edev_id: Optional[int]=None, create_nested: bool=False):
        """Check if an `EndDevice` is already registered on the server. If not, create 
        the `EndDevice` and (optionally) all nested objects.

        Args:
            end_device (EndDevice): `EndDevice` to create
            edev_id (int, optional): Resource ID of `EndDevice` if it already exists. 
            If `None`, creates a new `EndDevice`. Defaults to None.
            create_nested (bool, optional): Create nested objects (e.g. `DER`, `DeviceInformation`). Defaults to False.

        Raises:
            ValueError: Raised when request to create `EndDevice` fails.
        """
        if edev_id is None:
            logger.info('No edevID supplied. Attempting to create EndDevice')
            response = self.create_end_device(end_device)
            if response.status_code == 201:
                edev_id = trailing_resource_id_from_response(response)
            else:
                raise ValueError(f'Attempt to create EndDevice returned {response.status_code}: {response.content}')
        
        server_end_device = self.get_end_device(edev_id)

        if create_nested:
            self.create_device_information(end_device.device_information, edev_id=edev_id)

            for der in end_device.der:
                response = self.create_der(der, edev_id=edev_id)
                if response.status_code > 201:
                    logger.warning(f'DER could not be created for EndDevice {edev_id}')
                der_id = trailing_resource_id_from_response(response)
                if der.der_capability:
                    response = self.create_der_capability(der.der_capability, edev_id, der_id)

            if end_device.connection_point:
                self.create_connection_point(end_device.connection_point, edev_id)

        

    
    def sync_end_devices(self, end_devices: List[EndDevice], create_der=False, abort_on_error=True) -> None:
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
