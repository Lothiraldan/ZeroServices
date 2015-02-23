import asyncio
import aiohttp
from aiohttp import web

import sys
import json

from zeroservices import BaseService
from zeroservices import ZeroMQMedium
from zeroservices.discovery import UdpDiscoveryMedium

from jinja2 import Environment, FileSystemLoader


clients = set()


class ChatService(BaseService):

    @asyncio.coroutine
    def on_event(self, message_type, **kwargs):
        """Called when a multicast message is received
        """
        msg = {'type': message_type}
        msg.update(kwargs)
        self.send_to_all_clients(json.dumps(msg))

    @asyncio.coroutine
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
            client.send_str(msg)

loop = asyncio.get_event_loop()
medium = ZeroMQMedium(loop, UdpDiscoveryMedium, node_id=sys.argv[1])
s = ChatService(sys.argv[1], medium)

env = Environment(loader=FileSystemLoader('.'))

@asyncio.coroutine
def main_handler(request):
    template = env.get_template('chat.html')
    content = template.render(port=int(sys.argv[2]), name=sys.argv[1])
    return web.Response(text=content, content_type="text/html")


@asyncio.coroutine
def websocket_handler(request):

    ws = web.WebSocketResponse()
    ws.start(request)

    clients.add(ws)
    for node_id, node in s.directory.items():
        msg = json.dumps({'type': 'user_join',
                          'id': node_id, 'name': node['name']})
        ws.send_str(msg)

    while True:
        msg = yield from ws.receive()

        if msg.tp == aiohttp.MsgType.text:
            if msg.data == 'close':
                clients.remove(ws)
                yield from ws.close()
            else:
                message = json.loads(msg.data)

                if message['type'] == 'message':
                    msg = {'username': sys.argv[1], 'message': message['data']['message']}
                    yield from s.publish(str(message['type']), msg)
                elif message['type'] == 'direct_message':
                    msg = {'from': sys.argv[1], 'message': message['data']['message']}
                    yield from s.send(message['data']['to'], msg,
                                      message_type=str(message['type']),
                                      wait_response=False)
        elif msg.tp == aiohttp.MsgType.close:
            clients.remove(ws)
        elif msg.tp == aiohttp.MsgType.error:
            clients.remove(ws)
            print('ws connection closed with exception %s',
                  ws.exception())

    return ws

app = web.Application()
app.router.add_route('GET', '/', main_handler)
app.router.add_static('/static', '.')
app.router.add_route('*', '/websocket', websocket_handler)

if __name__ == '__main__':
    handler = app.make_handler()
    f = loop.create_server(handler, '0.0.0.0', int(sys.argv[2]))
    srv = loop.run_until_complete(f)
    loop.run_until_complete(s.start())
    print('serving on', srv.sockets[0].getsockname())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(handler.finish_connections(1.0))
        srv.close()
        s.close()
        loop.run_until_complete(srv.wait_closed())
        loop.run_until_complete(app.finish())
    loop.close()
