from zmq.eventloop import ioloop, zmqstream
ioloop.install()

import sys
import json

from zeroservices import BaseService
from zeroservices import ZeroMQMedium

from tornado import gen
from tornado import web
from tornado import websocket

from time import time


class ChatService(BaseService):

    def __init__(self, username):
        self.username = username
        super(ChatService, self).__init__(ZeroMQMedium(self, port_random=True))

    def service_info(self):
        return {'name': self.username}

    def on_event(self, message_type, message):
        """Called when a multicast message is received
        """
        msg = {'type': message_type}
        msg.update(message)
        self.send_to_all_clients(json.dumps(msg))

    def on_message(self, message_type, **kwargs):
        """Called when an unicast message is received
        """
        msg = {'type': message_type}
        msg.update(kwargs)
        self.send_to_all_clients(json.dumps(msg))

    def on_peer_join(self, node_info):
        """Called when a new peer joins
        """
        msg = json.dumps({'type': 'user_join', 'id': node_info['node_id'], 'name': node_info['name']})
        self.send_to_all_clients(msg)

    def on_peer_leave(self, node_info):
        """Called when a peer leaves
        """
        msg = json.dumps({'type': 'user_leave', 'id': node_info['node_id'], 'name': node_info['name']})
        self.send_to_all_clients(msg)

    def send_to_all_clients(self, msg):
        for client in clients:
            client.write_message(msg)


s = ChatService(sys.argv[1])
clients = []

class MainHandler(web.RequestHandler):
    def get(self):
        return self.render('chat.html', port=int(sys.argv[2]), name=sys.argv[1])


class WebSocketHandler(websocket.WebSocketHandler):

    def open(self):
        """Called on new websocket connection
        """
        clients.append(self)
        for node_id, node in s.nodes_directory.items():
            msg = json.dumps({'type': 'user_join',
                              'id': node_id, 'name': node['name']})
            self.write_message(msg)

    def on_close(self):
        """Called on websocket connection close
        """
        clients.remove(self)

    def on_message(self, message):
        """Called on websocket message
        """
        message = json.loads(message)
        if message['type'] == 'message':
            msg = {'username': sys.argv[1], 'message': message['data']['message']}
            s.publish(str(message['type']), msg)
        elif message['type'] == 'direct_message':
            msg = {'from': sys.argv[1], 'message': message['data']['message']}
            s.send(message['data']['to'], msg, msg_type=str(message['type']))

urls = [
    (r"/", MainHandler),
    (r"/websocket", WebSocketHandler),
    (r"/static/(.*)", web.StaticFileHandler, {"path": "."})]

if __name__ == '__main__':
    application = web.Application(urls, debug=True)
    application.listen(int(sys.argv[2]))
    try:
        ioloop.IOLoop.instance().add_timeout(time() + 1, s.medium.register)
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        s.close()
        for client in clients:
            client.close()
