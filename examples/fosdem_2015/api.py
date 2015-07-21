import asyncio

from zeroservices import ZeroMQMedium, ResourceService
from zeroservices.services import get_http_interface

from zeroservices.discovery import UdpDiscoveryMedium


# Http utils

class Auth(object):

    def authorized(self, handler, resource, method):
        return True


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    medium = ZeroMQMedium(loop, UdpDiscoveryMedium)
    service = ResourceService('todo_mvc', medium)
    application = get_http_interface(service, loop, port=5001, allowed_origins="*")
    application = loop.run_until_complete(application)
    loop.run_until_complete(service.start())
    loop.run_forever()
