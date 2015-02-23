import zmq
import json
import time
import socket
import asyncio

from datetime import timedelta
from time import sleep, time

try:
    from unittest.mock import Mock, call
except ImportError:
    from mock import Mock, call

from zeroservices.medium.memory import MemoryMedium
from zeroservices.discovery import MemoryDiscoveryMedium
from .utils import generate_zeromq_medium
from ..utils import TestCase, _async_test, TestService

from . import _BaseMediumTestCase


class MemoryMediumTestCase(_BaseMediumTestCase):

    @asyncio.coroutine
    def get_medium(self, loop):
        medium = MemoryMedium(loop=loop, discovery_class=MemoryDiscoveryMedium)
        medium.set_service(TestService('test_service', medium))
        yield from medium.start()
        return medium

    def tearDown(self):
        super(MemoryMediumTestCase, self).tearDown()
        MemoryMedium.reset()

    @_async_test
    def test_periodic_call(self):
        periodic_called = Mock()

        @asyncio.coroutine
        def mock_wrapper():
            return periodic_called()

        self.medium_1.periodic_call(mock_wrapper, 0.1)

        yield from self.medium_1.call_callbacks()

        self.assertEqual(periodic_called.call_count, 1)


if __name__ == '__main__':
    unittest.main()
