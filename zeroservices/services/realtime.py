import asyncio
import aiohttp

try:
    import json
except ImportError:
    import simplejson as json

from collections import defaultdict, namedtuple
from itertools import accumulate
import logging
import datetime

Parser = None

# Limit import
__all__ = ["Parser"]

class DefaultJsonParser(json.JSONEncoder):
    """ Create a basic JSON parser instance """
    def default(self, obj):
        """ Output data """
        # Printer for datetime object
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()

        # Switch to default handler
        return json.JSONEncoder.default(self, obj)

# Setting parser to default one
Parser = DefaultJsonParser


# class DefaultSockJSHandler(SockJSConnection):
#     """ Default handler """
#     _parser = Parser()

#     def check_origin(self, origin):
#         return origin in self.session.handler.application.allowed_origins

#     def __init__(self, session):
#         super(DefaultSockJSHandler, self).__init__(session)
#         self.rooms = []

#     def on_open(self, info):
#         self.app = self.session.handler.application
#         self.app.clients.append(self)
#         self.send({'data': 'Connected'})

#     def on_message(self, data):
#         """ Parsing data, and try to call responding message """
#         # Trying to parse response
#         data = json.loads(data)
#         if data["name"] is not None:
#             logging.debug("%s: receiving message %s" % (data["name"], data["data"]))
#             fct = getattr(self, "on_" + data["name"])
#             res = fct(data["data"])
#             if res is not None:
#                 self.write_message(res)
#         else:
#             logging.error("SockJSDefaultHandler: data.name was null")


#     ###
#     # Utils
#     ###

#     def publish(self, name, data, userList):
#         """ Publish data """
#         # Publish data to all room users
#         self.broadcast(userList, {
#             "name": name,
#             "data": self._parser.encode(data)
#         })

#     def _get_room(self, topic):
#         return self.app.rooms.setdefault(topic, set())

#     def join(self, topic):
#         """ Join a room """
#         self._get_room(topic).add(self)

#     def leave(self, _id):
#         """ Leave a room """
#         for topic in self.rooms:
#             self._get_room(topic).delete(self)

#     def publishToRoom(self, topic, name, data, userList=None):
#         """ Publish to given room data submitted """
#         if userList is None:
#             userList = self._get_room(topic)

#         # Publish data to all room users
#         # print("DefaultSockJSHandler: broadcasting (name: %s, data: %s, number of users: %s)" % (name, data, len(userList)))
#         self.broadcast(userList, {
#             "name": name,
#             "data": data
#         })

#     def publishToOther(self, topic, name, data):
#         """ Publish to only other people than myself """
#         tmpList = self._get_room(topic)
#         # Select everybody except me
#         userList = (x for x in tmpList if x is not self)
#         self.publishToRoom(topic, name, data, userList)

#     def publishToMyself(self, topic, name, data):
#         """ Publish to only myself """
#         self.publishToRoom(topic, name, data, [self])


# class SockJSHandler(DefaultSockJSHandler):

#     def on_join(self, data):
#         topic = data['topic']
#         self.rooms.append(topic)
#         self.join(topic)


class Session(object):

    __slots__ = ['ws', 'topics']

    def __init__(self, ws, topics=None):
        self.ws = ws
        self.topics = topics or set()


class RealtimeHandler(object):

    rooms = defaultdict(set)
    sessions = set()

    def __init__(self, app, service):
        self.app = app
        self.service = service
        self.service.medium.add_event_listener(self.publish)
        self.session = None

    @asyncio.coroutine
    def publish(self, event_type, event_message):
        self.broadcast('*', 'event', event_message)

        topics = accumulate(event_type.split('.'), lambda x, y: '.'.join((x, y)))

        for topic in topics:
            # self.logger.info('Publish %s to %s topic', event_message, topic)
            self.broadcast(topic, 'event', event_message)

    def broadcast(self, topic, msg_type, msg):
        if topic == '*':
            sessions = self.__class__.sessions
        else:
            sessions = self.__class__.rooms[topic]

        message = json.dumps({'type': msg_type, 'data': msg})

        for session in sessions:
            try:
                session.ws.send_str(message)
            except RuntimeError as e:
                pass

    @asyncio.coroutine
    def handler(self, request):
        ws = aiohttp.web.WebSocketResponse()
        ws.start(request)

        while True:
            msg = yield from ws.receive()

            session = Session(ws, None)
            self.sessions.add(session)

            self.process(session, msg.tp, msg)

            print("Status", self.__class__.sessions, self.__class__.rooms)

        return ws

    def process(self, session, msg_type, msg):
        if msg_type == aiohttp.MsgType.text:
            parsed_msg = json.loads(msg.data)

            if parsed_msg['type'] == 'join':
                topics = parsed_msg.get('topics', set())

                for topic in topics:
                    session.topics.add(topic)
                    self.__class__.rooms[topic].add(session)

            if parsed_msg['type'] == 'subscribe':
                for topic in parsed_msg.get('topics', set()):
                    if not topic in self.session.topics:
                        session.topics.add(topic)
                        self.__class__.rooms[topic].add(session)
        elif msg_type == aiohttp.MsgType.close:
            pass
        elif msg_type == aiohttp.MsgType.error:
            pass
