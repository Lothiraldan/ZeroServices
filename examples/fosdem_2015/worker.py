import asyncio

from zeroservices import ResourceWorker, ZeroMQMedium
from zeroservices.discovery import UdpDiscoveryMedium


class PowerWorker(ResourceWorker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Process each resource in status building
        self.register(self.do_build, 'power', status='pending')

    def do_build(self, resource_name, resource_data, resource_id, action):
        power = resource_data['value'] * resource_data['value']
        yield from self.send(collection_name='power',
                             resource_id=resource_id,
                             action='patch', patch={"$set": {'result': power,
                                                    'status': 'done'}})

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    medium = ZeroMQMedium(loop, UdpDiscoveryMedium)
    worker = PowerWorker('PowerWorker', medium)
    loop.run_until_complete(worker.start())
    loop.run_forever()
