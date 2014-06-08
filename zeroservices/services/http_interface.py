import logging
import json
import tornado
import logging

from functools import wraps
from base64 import decodestring
from tornado import gen
from tornado.web import URLSpec, RequestHandler, Application, HTTPError
from tornado import websocket


class AuthenticationError(HTTPError):

    def __init__(self, *args, **kwargs):
        super(AuthenticationError, self).__init__(*args, **kwargs)
        self.status_code = 401
        self.headers = [('WWW-Authenticate', 'Basic realm=tmr')]


class ForbiddenError(HTTPError):
    def __init__(self, *args, **kwargs):
        super(ForbiddenError, self).__init__(*args, **kwargs)
        self.status_code = 403


class BasicAuth(object):
    """ Implements Basic AUTH logic. Should be subclassed to implement custom
    authentication checking.

    """

    def __init__(self, handler):
        self.handler = handler

    def check_auth(self, username, password, resource, method):
        """ This function is called to check if a username / password
        combination is valid. Must be overridden with custom logic.

        :param username: username provided with current request.
        :param password: password provided with current request
        :param resource: resource being requested.
        :param method: HTTP method being executed (POST, GET, etc.)
        """
        raise NotImplementedError

    def authorized(self, resource, method):
        """ Validates the the current request is allowed to pass through.

        :param resource: resource being requested.
        """
        handler = self.handler

        auth_header = handler.request.headers.get('Authorization')
        if auth_header is None:
            raise AuthenticationError()
        if not auth_header.startswith('Basic '):
            raise AuthenticationError()

        auth_decoded = decodestring(auth_header[6:])
        username, password = auth_decoded.split(':', 2)

        if self.check_auth(username, password, ressource, method):
            return True
        else:
            raise ForbiddenError()


def get_http_interface(service, port=8888, auth=None, auth_args=(), auth_kwargs={}):

    logger = logging.getLogger('api')

    # Handlers


    class BaseHandler(RequestHandler):

        def prepare(self):
            auth = self.application.auth(self)

            ressource = self.path_kwargs.get("collection")
            auth.authorized(ressource, self.request.method)

        def write_error(self, status_code, **kwargs):
            if self.settings.get("serve_traceback") and "exc_info" in kwargs:
                # in debug mode, try to send a traceback
                self.set_header('Content-Type', 'text/plain')
                for line in traceback.format_exception(*kwargs["exc_info"]):
                    self.write(line)
                self.finish()
            else:
                if exc_info in kwargs:
                    for header in getattr(kwargs['exc_info'][1], 'headers', []):
                        self.set_header(*header)

                self.finish("<html><title>%(code)d: %(message)s</title>"
                            "<body>%(code)d: %(message)s</body></html>" % {
                                "code": status_code,
                                "message": self._reason,
                            })



    class MainHandler(RequestHandler):
        def get(self):
            self.write("Hello world from api")


    class BaseHandler(RequestHandler):

        def _process(self, collection, action, ressource_id=None,
                     read_body=True):

            payload = {'collection': collection, 'action': action}

            if ressource_id:
                payload['ressource_id'] = ressource_id

            if read_body:
                payload['args'] = json.loads(self.request.body.decode('utf-8'))
            else:
                payload['args'] = {}

            logger.info('Payload %s' % payload)

            result = service.send(**payload)
            logger.info('Result is %s' % result)

            return result


    class CollectionHandler(BaseHandler):

        def get(self, collection):
            self.write(self._process(collection, 'list', read_body=False))
            self.finish()


    class RessourceHandler(BaseHandler):

        def get(self, collection, ressource_id):
            self.write(self._process(collection, 'get', ressource_id,
                                     read_body=False))
            self.finish()

        def post(self, collection, ressource_id):
            self.write(self._process(collection, 'create', ressource_id))
            self.finish()

        def delete(self, collection, ressource_id):
            self.write(self._process(collection, 'delete', ressource_id,
                                     read_body=False))
            self.finish()

        def patch(self, collection, ressource_id):
            self.write(self._process(collection, 'patch', ressource_id))
            self.finish()


    class WebSocketHandler(websocket.WebSocketHandler):

        def open(self):
            self.application.clients.append(self)
            self.write_message('Test')

        def on_close(self):
            self.application.clients.remove(self)


    # Urls
    urls = [
        URLSpec(r"/", MainHandler, name="main"),
        URLSpec(r"/(?P<collection>[^\/]+)/$",
                CollectionHandler, name="collection"),
        URLSpec(r"/(?P<collection>[^\/]+)/(?P<ressource_id>[^\/]+)/$",
                RessourceHandler, name="ressource"),
        URLSpec(r"/websocket", WebSocketHandler, name="websocket")]

    # Application
    application = Application(urls)
    application.listen(port)
    application.auth = auth
    application.clients = []

    return application
