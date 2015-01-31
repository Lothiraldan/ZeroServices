from zeroservices import ResourceWorker, ZeroMQMedium


class BuildWorker(ResourceWorker):

    def __init__(self, *args, **kwargs):
        super(BuildWorker, self).__init__(*args, **kwargs)
        # Process each resource in status building
        self.register(self.do_build, 'power', status='pending')

    def do_build(self, resource_name, resource_data, resource_id, action):
        power = resource_data['value'] * resource_data['value']
        self.send(collection='power',
                  resource_id=resource_id,
                  action='patch', patch={"$set": {'result': power,
                                                  'status': 'done'}})

if __name__ == '__main__':
    worker = BuildWorker('PowerWorker', ZeroMQMedium(port_random=True))
    worker.main()
