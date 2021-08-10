
from requests import Session

class Auth:
    def inject_headers(self, header):
        pass

    def update_session(self, session: Session) -> None:
        raise NotImplementedError

class LocalModeXTokenAuth:
    def __init__(self, lfdi: str):
        self.lfdi = lfdi

    def inject_headers(self, header):
        header["X-Token"] = self.lfdi

    def update_session(self, session: Session) -> None:
        """Update the transport layer with appropriate session headers to pass through
        on all requests

        Args:
            session (Session): Transport `Session` object
        """
        session.headers['X-Token'] = self.lfdi



