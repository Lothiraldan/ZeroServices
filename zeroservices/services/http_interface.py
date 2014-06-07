import logging
import json
import tornado
import logging

from functools import wraps
from base64 import decodestring
from tornado import gen
from tornado.web import URLSpec, RequestHandler, Application
from tornado import websocket


# Tornado handlers
def basic_auth(auth):

    def decore(f):

        def _request_auth(handler):
            handler.set_header('WWW-Authenticate', 'Basic realm=tmr')
            handler.set_status(401)
            handler.finish()
            return False

        @wraps(f)
        def new_f(*args, **kwargs):
            handler = args[0]

            auth_header = handler.request.headers.get('Authorization')
            if auth_header is None:
                return _request_auth(handler)
            if not auth_header.startswith('Basic '):
                return _request_auth(handler)

            auth_decoded = decodestring(auth_header[6:])
            username, password = auth_decoded.split(':', 2)

            if (auth(username, password)):
                f(*args, **kwargs)
            else:
                return _request_auth(handler)

        return new_f
    return decore



def get_http_interface(service, port=8888, auth_decorator=None, auth_args=(), auth_kwargs={}):

    # Default auth decorator
    if auth_decorator is None:
        auth_decorator = basic_auth

    logger = logging.getLogger('api')

    # Handlers
    class MainHandler(RequestHandler):
        def get(self):
            self.write("Hello world from api")


    class CollectionHandler(RequestHandler):

        @auth_decorator(*auth_args, **auth_kwargs)
        def get(self, collection):
            self.write(self.request.body)
            self.finish()
            args = json.loads(self.request.body)

            payload = {'collection': collection, 'action': action,
                'args': args}
            logger.info('Payload %s' % payload)

            result = interface.call(**payload)
            logger.info('Result is %s' % result)

            self.write(result)
            self.finish()

        @auth_decorator(*auth_args, **auth_kwargs)
        def post(self, collection):
            args = json.loads(self.request.body.decode('utf-8'))

            payload = {'collection': collection, 'action': 'create',
                'args': args}
            logger.info('Payload %s' % payload)

            result = service.send(**payload)
            logger.info('Result is %s' % result)

            self.write(result)
            self.finish()


    class RessourceHandler(RequestHandler):

        @auth_decorator(*auth_args, **auth_kwargs)
        def post(self, collection, ressource_id, action):
            args = json.loads(self.request.body)

            payload = {'collection': collection, 'action': action,
                'args': args, 'ressource_id': ressource_id}
            logger.info('Payload %s' % payload)

            result = interface.call(**payload)
            logger.info('Result is %s' % result)

            self.write(result[0])
            self.finish()


    class WebSocketHandler(websocket.WebSocketHandler):

        def open(self):
            clients.append(self)
            self.write_message('Test')

        def on_close(self):
            clients.remove(self)


    # Urls
    urls = [
        URLSpec(r"/", MainHandler, name="main"),
        URLSpec(r"/(?P<collection>[^\/]+)/$",
                CollectionHandler, name="collection"),
        URLSpec(r"/(?P<collection>[^\/]+)/(?P<ressource_id>[^\/]+)/(?P<action>[^\/]+)$",
                RessourceHandler, name="ressource"),
        URLSpec(r"/websocket", WebSocketHandler, name="websocket")]

    # Application
    application = Application(urls)
    application.listen(port)
    application.clients = []

    return application
