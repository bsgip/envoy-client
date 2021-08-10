
import requests
import logging
logger = logging.getLogger(__name__)

from .auth import Auth

class Transport:
    def __init__(self, auth: Auth) -> None:
        self.auth = auth
        self.is_connected = False
        self.session = None

    def post(self, document, path):
        raise NotImplementedError

    
    def get(self, path):
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
        self.auth.update_session(self.session)
        self.is_connected = True
        
    def close(self):
        self.session.close()

