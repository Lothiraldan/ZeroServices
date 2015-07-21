import logging

import asyncio
from zeroservices import ZeroMQMedium, BaseService
from zeroservices.discovery import UdpDiscoveryMedium


class SnifferService(BaseService):

    def __init__(self, *args, **kwargs):
        super(SnifferService, self).__init__(*args, **kwargs)
        self.logger.setLevel(logging.ERROR)
        self.medium.logger.setLevel(logging.ERROR)

    def on_event(self, message_type, *args, **kwargs):
        print("[{}] {} {}".format(message_type, args, kwargs))
        yield from asyncio.sleep(0.0000001)


def main():
    loop = asyncio.get_event_loop()
    medium = ZeroMQMedium(loop, UdpDiscoveryMedium)
    sniffer = SnifferService('sniffer', medium)
    loop.run_until_complete(sniffer.start())
    loop.run_forever()

if __name__ == '__main__':
    main()
