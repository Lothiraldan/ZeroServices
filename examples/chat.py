from zeroservices import BaseService
from zeroservices import ZeroMQMedium

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
        print "A NEW CHALLENGER !", node_info

    def coucou(self):
        self.medium.publish('Hello', {'message': 'World'})

    def main(self):
        self.medium.ioloop.add_timeout(time() + 2, self.coucou)
        super(ChatService, self).main()

if __name__ == '__main__':
    import sys
    s = ChatService(sys.argv[1])
    s.main()
