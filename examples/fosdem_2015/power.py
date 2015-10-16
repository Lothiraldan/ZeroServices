import asyncio
from zeroservices import ZeroMQMedium, ResourceService
from zeroservices.discovery import UdpDiscoveryMedium
from zeroservices.backend.mongodb import MongoDBCollection


class PowerCollection(MongoDBCollection):

    def __init__(self, *args, **kwargs):
        super(PowerCollection, self).__init__(*args, **kwargs)
        self.collection.ensure_index([('description', 'text')])


def main():
    loop = asyncio.get_event_loop()
    medium = ZeroMQMedium(loop, UdpDiscoveryMedium)
    service = ResourceService('fosdem_2015_power', medium)
    service.register_resource(PowerCollection("power", "fosdem_db"))
    loop.run_until_complete(service.start())
    loop.run_forever()

if __name__ == '__main__':
    main()
