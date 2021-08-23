
from envoy_client.models import DeviceCategoryType, EndDevice, EndDeviceList
import requests
from urllib.parse import urljoin
from typing import Optional
import xmltodict
import logging
logger = logging.getLogger(__name__)

from .auth import Auth

class Transport:
    """Abstract base class that represents the transport medium used to 
    communicate with the utility server.
    """
    def __init__(self, base_url: str, auth: Optional[Auth]) -> None:
        self.base_url = base_url
        self.auth = auth
        self.is_connected = False
        self.session = None

    def post(self, path: str, document: str) -> requests.Response:
        """Send a POST request to the utility server

        Args:
            path (str): resource path (excluding base URL)
            document (str): XML document to include as request body

        Returns:
            requests.Response: server response
        """
        raise NotImplementedError

    
    def get(self, path: str) -> requests.Response:
        """Send a GET request to the utility server

        Returns:
            requests.Response: server response
        """
        raise NotImplementedError

    def put(self, path: str, document: str):
        """Send a PUT request to the utility server

        Args:
            path (str): resource path (excluding base URL)
            document (str): XML document to include as request body

        Returns:
            requests.Response: server response
        """
        raise NotImplementedError

    def connect(self):
        """Initiate connection to server over the transport.
        """
        if self.is_connected:
            logging.info(f"{self.__class__} is already connected")
        

    def close(self):
        """Close connection to the server
        """
        pass

    def validate(self):
        """Validate that the transport can connect to the server
        """
        pass


class RequestsTransport(Transport):
    """`Transport` that uses the python `requests` library
    """
    def connect(self):
        if self.is_connected:
            logger.info(f"{self.__class__} is already connected")
        self.session = requests.Session()
        if self.auth:
            self.auth.update_session(self.session)
        self.session.headers["Content-Type"] = 'application/xml'
        self.is_connected = True
        
    def close(self):
        self.session.close()

    def get(self, path: str) -> requests.Response:
        response = self.session.get(urljoin(self.base_url, path))
        self._log_response(response)
        return response

    def post(self, path: str, document: str) -> requests.Response:
        response = self.session.post(urljoin(self.base_url, path), data=document)
        self._log_response(response)
        return response

    def put(self, path: str, document: str) -> requests.Response:
        response = self.session.put(urljoin(self.base_url, path), document)
        self._log_response(response)
        return response

    def _log_response(self, response) -> None:
        if response.status_code > 201:
            logger.warning(f'{response.request.method} {response.request.url} returned status {response.status_code}')
        else:
            logger.info(f'{response.request.method} {response.request.url} returned status {response.status_code}')


class MockResponse:
    """A mock response object used by the `MockTransport` to provide a response 
    from which resource locations can be extracted
    """
    def __init__(self, request, status_code=201, content='', location=None) -> None:
        self.status_code = status_code
        self.content = content
        self.request = request

        self.headers = {}
        if self.request.method in ('PUT', 'POST'):
            self.headers['location'] = location or '/mock/location/1'


class MockTransport(RequestsTransport):
    """A mock `Transport` object that prints the details of requests and returns a `MockResponse`.
    Useful for generating documentation about client-server interactions.
    """

    def generate_random_content(self, path):
        # This is required to have a functional mock_sync_devices method
        if path.startswith('/edev/'):
            # Return an `EndDevice`
            return EndDevice(lfdi='0x3497623952', device_category=DeviceCategoryType.combined_pv_and_storage)
        elif path.startswith('/edev'):
            # Return an `EndDeviceList`
            return EndDeviceList(
                end_device=[EndDevice(lfdi='0x3497623952', device_category=DeviceCategoryType.combined_pv_and_storage)]
            )
        else:
            raise ValueError(f'`MockTransport` does not support returning mock data on path {path}')
    
    def get(self, path: str) -> MockResponse:
        request = requests.Request(
            'GET', 
            urljoin(self.base_url, path),
        )
        prepared = request.prepare()
        header_str = '\n'.join(f"{k}: {v}" for k, v in request.headers.items())


        print(f"""
    {request.method} {request.url}
    {header_str}
        """)
        return MockResponse(request, 200, content=self.generate_random_content(path).to_xml(mode='show'))

    def post(self, path: str, document: str) -> MockResponse:
        request = requests.Request(
            'POST', 
            urljoin(self.base_url, path),
            headers={'Content-Type': 'application/xml'},
            data=document
        )
        prepared = request.prepare()
        header_str = '\n'.join(f"{k}: {v}" for k, v in request.headers.items())
        print(f"""
{request.method} {request.url}
{header_str}

{xmltodict.unparse(xmltodict.parse(document), pretty=True)}
        """, )
        return MockResponse(request)

    def put(self, path: str, document: str) -> MockResponse:
        request = requests.Request(
            'PUT', 
            urljoin(self.base_url, path),
            headers={'Content-Type': 'application/xml'},
            data=document
        )
        prepared = request.prepare()
        header_str = '\n'.join(f"{k}: {v}" for k, v in request.headers.items())
        print(f"""
{request.method} {request.url}
{header_str}

{xmltodict.unparse(xmltodict.parse(document), pretty=True)}
        """, )
        return MockResponse(request, 200)
