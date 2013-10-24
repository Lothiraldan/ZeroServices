from zmq.eventloop import ioloop, zmqstream
ioloop.install()

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
        print "ON EVENT", message_type, message

    def on_new_node(self, node_info):
        msg = json.dumps({'type': 'new_user', 'id': node_info['node_id'], 'name': node_info['name']})
        self.send_to_all_clients(msg)

    def send_to_all_clients(self, msg):
        for client in clients:
            client.write_message(msg)


clients = []


class MainHandler(web.RequestHandler):
    def get(self):
        return self.render('chat.html', port=int(sys.argv[2]))


class WebSocketHandler(websocket.WebSocketHandler):

    def open(self):
        clients.append(self)
        print "OPEN"
        msg = 'Welcome %s' % sys.argv[1]
        self.write_message(json.dumps({'type': 'message', 'message': msg}))

    def on_close(self):
        clients.remove(self)


urls = [
    (r"/", MainHandler),
    (r"/websocket", WebSocketHandler)]

if __name__ == '__main__':
    import sys
    s = ChatService(sys.argv[1])
    s.medium.register()

    application = web.Application(urls)
    application.listen(int(sys.argv[2]))
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print 'Interrupted'
