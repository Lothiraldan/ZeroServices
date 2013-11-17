from mock import Mock, create_autospec
from threading import Thread

from zeroservices.medium.zeromq import ZeroMQMedium
from zeroservices.service import BaseService

def run_poller_for(medium, timeout):
    thread = Thread(target=medium.loop, args=(timeout,))
    thread.start()

def generate_zeromq_medium(service_info, node_id=None, ioloop=None):

    service = create_autospec(BaseService, True)
    service.name = service_info['name']
    service.service_info.return_value = service_info
    service.medium = ZeroMQMedium(service, port_random=True, node_id=node_id,
                                       ioloop=ioloop)

    def stop_loop(*args, **kwargs):
        service.medium.stop()

    # Set side_effect
    service.on_registration_message.side_effect = stop_loop
    service.on_event.side_effect = stop_loop
    service.on_message.side_effect = stop_loop
    service.on_peer_join.side_effect = stop_loop
    service.on_peer_leave.side_effect = stop_loop

    return service
