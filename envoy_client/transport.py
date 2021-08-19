
from envoy_client.models import DeviceCategoryType, EndDevice
import requests
from urllib.parse import urljoin
from typing import Optional
import xmltodict
import logging
logger = logging.getLogger(__name__)

from .auth import Auth

class Transport:
    def __init__(self, base_url: str, auth: Optional[Auth]) -> None:
        self.base_url = base_url
        self.auth = auth
        self.is_connected = False
        self.session = None

    def post(self, path: str, document: str):
        raise NotImplementedError

    
    def get(self, path: str):
        raise NotImplementedError

    def put(self, document, path):
        raise NotImplementedError

    def connect(self):
        if self.is_connected:
            logging.info(f"{self.__class__} is already connected")
        

    def close(self):
        pass

    def validate(self):
        pass


class RequestsTransport(Transport):
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

    def get(self, path):
        response = self.session.get(urljoin(self.base_url, path))
        self._log_response(response)
        return response

    def post(self, path, document):
        response = self.session.post(urljoin(self.base_url, path), data=document)
        self._log_response(response)
        return response

    def put(self, path, document):
        response = self.session.put(urljoin(self.base_url, path), document)
        self._log_response(response)
        return response

    def _log_response(self, response):
        if response.status_code > 201:
            logger.warning(f'{response.request.method} {response.request.url} returned status {response.status_code}')
        else:
            logger.info(f'{response.request.method} {response.request.url} returned status {response.status_code}')


class MockResponse:
    def __init__(self, request, status_code=201, content='', location=None) -> None:
        self.status_code = status_code
        self.content = content
        self.request = request

        self.headers = {}
        if self.request.method in ('PUT', 'POST'):
            self.headers['location'] = location or '/mock/location/1'


class DocumentationGeneratingTransport(RequestsTransport):

    def generate_random_content(self, path):
        # This is required to have a functional mock_sync_devices method
        if path.startswith('/edev/'):
            return EndDevice(lfdi='0x3497623952', device_category=DeviceCategoryType.combined_pv_and_storage)
    
    def get(self, path):
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

    def post(self, path, document):
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

    def put(self, path, document):
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
