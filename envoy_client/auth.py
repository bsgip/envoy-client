
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
        # Convert to integer as this is what is checked against
        session.headers['X-Token'] = str(int(self.lfdi, 16))
        session.headers['X-Forwarded-Client-Cert'] = ""  # Required for local auth


class ClientCerticateAuth(Auth):
    def __init__(self, cert: str) -> None:
        """Authorisation based on the supplied path to a client-side certificate.
        This certificate is normally issued by the relevant Certificate Authority 
        that the utility server is using. For testing purposes, this may be a self-signed
        certificate.

        Args:
            cert (str): Path to the client certificate
        """
        super().__init__()
        self.cert = cert

    def update_session(self, session: Session) -> None:
        """Update transport session with relevant authorisation information

        Args:
            session (Session): Transport `Session` object
        """
        session.cert = self.cert
