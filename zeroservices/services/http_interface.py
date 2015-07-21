import asyncio
import logging
import json
import binascii
import traceback

from aiohttp import web
from aiohttp import hdrs
from base64 import b64decode
from .realtime import RealtimeHandler
from ..exceptions import UnknownService


# class AuthenticationError(HTTPError):

#     def __init__(self, *args, **kwargs):
#         super(AuthenticationError, self).__init__(401, *args, **kwargs)
#         self.headers = [('WWW-Authenticate', 'Basic realm=tmr')]


# class BadRequest(HTTPError):

#     def __init__(self, *args, **kwargs):
#         super(ForbiddenError, self).__init__(400, *args, **kwargs)


# class ForbiddenError(HTTPError):

#     def __init__(self, *args, **kwargs):
#         super(ForbiddenError, self).__init__(403, *args, **kwargs)


# class MethodNotAllowed(HTTPError):

#     def __init__(self, *args, **kwargs):
#         super(MethodNotAllowed, self).__init__(405, *args, **kwargs)


class BasicAuth(object):
    """ Implements Basic AUTH logic. Should be subclassed to implement custom
    authentication checking.
    """

    def check_auth(self, username, password, resource, method):
        """ This function is called to check if a username / password
        combination is valid. Must be overridden with custom logic.

        :param username: username provided with current request.
        :param password: password provided with current request
        :param resource: resource being requested.
        :param method: HTTP method being executed (POST, GET, etc.)
        """
        raise NotImplementedError

    def authorized(self, handler, resource, method):
        """ Validates the the current request is allowed to pass through.

        :param resource: resource being requested.
        """
        auth_header = handler.request.headers.get('Authorization')
        if auth_header is None:
            raise AuthenticationError()
        if not auth_header.startswith('Basic '):
            raise AuthenticationError()

        try:
            auth_decoded = b64decode(auth_header[6:]).decode('utf-8')
            username, password = auth_decoded.split(':', 2)
        except (binascii.Error, UnicodeDecodeError, ValueError, TypeError):
            raise AuthenticationError()


        if self.check_auth(username, password, resource, method):
            return True
        else:
            raise ForbiddenError()


# Handlers
class BaseHandler(object):

    def __init__(self, service):
        self.logger = logging.getLogger('api')
        self.service = service

    def prepare(self):
        resource = self.path_kwargs.get("collection")
        self.application.auth.authorized(self, resource, self.request.method)

    def _process(self, request, collection, action, resource_id=None,
                 success_status_code=200, **kwargs):

        payload = {}

        request_body = yield from request.text()

        if request_body:
            try:
                request_body = json.loads(request_body)
                payload.update(request_body)
            except (ValueError, UnicodeDecodeError):
                self.logger.warning('Bad body: %s',
                                    request_body,
                                    exc_info=True)

        payload.update({'collection_name': collection, 'action': action})

        if resource_id:
            payload['resource_id'] = resource_id
        payload.update(kwargs)

        self.logger.info('Payload %s' % payload)

        try:
            result = yield from self.service.send(**payload)
            self.logger.info('Result is %s' % result)
        except UnknownService as e:
            self.logger.error('Payload error %s' % e)
            err_body = json.dumps({'error': str(e)}).encode('utf-8')
            raise web.HTTPNotFound(content_type="application/json",
                                   body=err_body)
        else:
            response_body = json.dumps(result).encode('utf-8')
            return web.Response(content_type="application/json",
                                body=response_body, status=success_status_code)


class MainHandler(BaseHandler):

    def main(self, request):
        response = json.dumps({'resources': self.service.known_resources}).encode('utf-8')
        return web.Response(body=response)


@asyncio.coroutine
def options(request):
    return web.Response(body=b" ")


class CollectionHandler(BaseHandler):

    def dispatch(self, request):
        return getattr(self, request.method.lower())(request)

    def get(self, request):
        return self._process(request, request.match_info['collection'], 'list')

    # def get(self, collection):
    #     args = {key: value[0] for key, value in self.request.arguments.items()}
    #     self._process(collection, 'list', where=args)

    def post(self, request):
        return self._process(request, request.match_info['collection'],
                             'create', success_status_code=201)

    def custom_action(self, request):
        return self._process(request, request.match_info['collection'],
                             request.match_info['action'])

    def options(self, request):
        return web.Response(body=b"")


class ResourceHandler(BaseHandler):

    def dispatch(self, request):
        return getattr(self, request.method.lower())(request)

    def get(self, request):
        return self._process(request, request.match_info['collection'],
                             'get', request.match_info['resource_id'])

    def delete(self, request):
        return self._process(request, request.match_info['collection'],
                             'delete', request.match_info['resource_id'],
                             success_status_code=204)

    def patch(self, request):
        return self._process(request, request.match_info['collection'],
                             'patch', request.match_info['resource_id'])

    def options(self, request):
        pass

    def custom_action(self, request):
        return self._process(request, request.match_info['collection'],
                             request.match_info['action'],
                             request.match_info['resource_id'])


@asyncio.coroutine
def cors_middleware(app, handler):
    @asyncio.coroutine
    def middleware(request):
        response = yield from handler(request)

        allowed_origins = app.allowed_origins
        if allowed_origins != "*":
            if len(allowed_origins) in [0, 1]:
                allowed_origins = allowed_origins

        response.headers['Access-Control-Allow-Origin'] = app.allowed_origins
        return response
    return middleware


@asyncio.coroutine
def get_http_interface(service, loop, port=8888, auth=None, auth_args=(),
                       auth_kwargs={}, bind=True, allowed_origins=None):
    if allowed_origins is None:
        allowed_origins = ""

    # Urls
    # sockjs_router = SockJSRouter(SockJSHandler, '/realtime')

    app = web.Application(loop=loop, middlewares=[cors_middleware])
    app.allowed_origins = allowed_origins

    # Realtime endpoint
    realtime_handler = RealtimeHandler(app, service)
    app.router.add_route('*', '/realtime', handler=realtime_handler.handler,
                         name='realtime')
    hdrs.ACCESS_CONTROL_ALLOW_ORIGIN = allowed_origins

    # URLS
    main_handler = MainHandler(service)
    app.router.add_route('*', '/', main_handler.main, name='main')

    collection_handler = CollectionHandler(service)
    app.router.add_route('*', '/{collection}', collection_handler.dispatch,
                         name='collection')
    app.router.add_route('*', '/{collection}/', collection_handler.dispatch,
                         name='collection_slash')
    app.router.add_route('POST', '/{collection}/{action}',
                         collection_handler.custom_action,
                         name='collection_custom_action')
    app.router.add_route('OPTIONS', '/{collection}/{action}',
                         options)

    resource_handler = ResourceHandler(service)
    app.router.add_route('*', '/{collection}/{resource_id}',
                         resource_handler.dispatch,
                         name='resource')
    app.router.add_route('*', '/{collection}/{resource_id}/',
                         resource_handler.dispatch,
                         name='resource_slash')
    app.router.add_route('OPTIONS', '/{collection}/{resource_id}/{action}',
                         options)
    app.router.add_route('*', '/{collection}/{resource_id}/{action}',
                         resource_handler.custom_action,
                         name='resource_custom_action')

    handler = app.make_handler()
    yield from loop.create_server(handler, '0.0.0.0', port)

    # Set application back-reference in service
    service.app = app

    return app
