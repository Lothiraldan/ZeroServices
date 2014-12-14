import pymongo

from zeroservices import RessourceService, ZeroMQMedium
from zeroservices.backend.mongodb import MongoDBCollection, MongoDBRessource
from zeroservices.memory import MemoryCollection, MemoryCollection
from zeroservices.ressources import is_callable

import sys
from zmq.eventloop import ioloop, zmqstream
ioloop.install()
import logging
import json
import tornado

from functools import wraps
from base64 import decodestring
from tornado import gen
from tornado import web
from tornado import websocket

from zeroservices import RessourceService, ZeroMQMedium
from zeroservices.services import get_http_interface, BasicAuth

from zeroservices.utils import accumulate


# Http utils

class Auth(object):

    def authorized(self, handler, resource, method):
        return True


# APP
class TODOService(RessourceService):

    def on_event(self, message_type, data):
        self.logger.info("On event %s", locals())
        application.clients[0].publishToRoom('*', 'event', data)

        topics = accumulate(message_type.split('.'), lambda x, y: '.'.join((x, y)))

        for topic in topics:
            application.clients[0].publishToRoom(topic, 'event', data)


if __name__ == '__main__':
    todo = TODOService('todo_mvc', ZeroMQMedium(port_random=True))
    application = get_http_interface(todo, port=5001, auth=Auth(), allowed_origins="*")
    todo.register_ressource(MongoDBCollection("todo_list"))
    todo.register_ressource(MongoDBCollection("todo_item"))
    todo.main()
