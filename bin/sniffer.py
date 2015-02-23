import logging

from zeroservices import BaseService, ZeroMQMedium


class SnifferService(BaseService):

    def __init__(self, *args, **kwargs):
        super(SnifferService, self).__init__(*args, **kwargs)
        self.logger.setLevel(logging.ERROR)
        self.medium.logger.setLevel(logging.ERROR)

    def on_event(self, message_type, *args, **kwargs):
        print "[{}] {} {}".format(message_type, args, kwargs)


if __name__ == '__main__':
    sniffer = SnifferService('sniffer', ZeroMQMedium(port_random=True))
    sniffer.main()
