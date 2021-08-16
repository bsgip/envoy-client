
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
        return self.session.get(urljoin(self.base_url, path))

    def post(self, path, document):
        return self.session.post(urljoin(self.base_url, path), data=document)

    def put(self, path, document):
        return self.session.put(urljoin(self.base_url, path), document)


class DocumentationGeneratingTransport(RequestsTransport):

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
        return

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
        return
