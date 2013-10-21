from mock import Mock
from threading import Thread

from zeroservices.medium.zeromq import ZeroMQMedium

def run_poller_for(medium, timeout):
    thread = Thread(target=medium.loop, args=(timeout,))
    thread.start()

def generate_zeromq_medium(service_info, node_id=None):

    class TestService(object):

        def __init__(self):
            self.service_info = Mock()
            self.service_info.return_value = service_info
            self.medium = ZeroMQMedium(self, port_random=True, node_id=node_id)
            self.on_registration_message = Mock()
            self.on_registration_message.side_effect = self.stop_loop

            self.on_event = Mock()
            self.on_event.side_effect = self.stop_loop

            self.on_message = Mock()
            self.on_message.side_effect = self.stop_loop

        def stop_loop(self, *args, **kwargs):
            self.medium.stop()

    return TestService()
