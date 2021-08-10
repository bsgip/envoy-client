

import xmltodict

from .transport import Transport
from .auth import Auth
from .models import EndDeviceList

class AggregatorClient:
    def __init__(self, transport: Transport, auth: Auth, lfdi: int) -> None:
        self.transport = transport
        self.auth = auth
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
        end_device_list = EndDeviceList(**xmltodict.parse(response.body))
        return end_device_list

    def create_end_devices(self, end_device_list: EndDeviceList, create_der=False, abort_on_error=True) -> None:
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
        raise NotImplementedError

    def reconcile_end_devices(self, server_device_list: EndDeviceList, client_device_list: EndDeviceList) -> None:
        raise NotImplementedError

