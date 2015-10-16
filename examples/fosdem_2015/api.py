import asyncio

from zeroservices import ZeroMQMedium, ResourceService
from zeroservices.services import get_http_interface

from zeroservices.discovery import UdpDiscoveryMedium


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    medium = ZeroMQMedium(loop, UdpDiscoveryMedium)
    service = ResourceService('api_interface', medium)
    application = get_http_interface(service, loop, port=5001, allowed_origins="*")
    application = loop.run_until_complete(application)
    loop.run_until_complete(service.start())
    loop.run_forever()
