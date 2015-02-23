import asyncio
from zeroservices.discovery import MemoryDiscoveryMedium

from . import _BaseDiscoveryMediumTestCase


class MemoryDiscoveryMediumTestCase(_BaseDiscoveryMediumTestCase):

    @asyncio.coroutine
    def get_medium(self, callback, loop, node_infos):
        medium = MemoryDiscoveryMedium(asyncio.coroutine(callback), loop, node_infos)
        yield from medium.start()
        return medium
