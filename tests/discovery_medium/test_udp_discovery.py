import asyncio
from zeroservices.discovery import UdpDiscoveryMedium

from . import _BaseDiscoveryMediumTestCase


class UdpDiscoveryMediumTestCase(_BaseDiscoveryMediumTestCase):

    @asyncio.coroutine
    def get_medium(self, callback, loop, node_infos):
        medium = UdpDiscoveryMedium(callback, loop, node_infos)
        yield from medium.start()
        return medium
