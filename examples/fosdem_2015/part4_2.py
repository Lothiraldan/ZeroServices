from zeroservices import ZeroMQMedium, ResourceService
from zeroservices.backend.mongodb import MongoDBCollection


class PowerCollection(MongoDBCollection):

    def __init__(self, *args, **kwargs):
        super(PowerCollection, self).__init__(*args, **kwargs)
        self.collection.ensure_index([('description', 'text')])


if __name__ == '__main__':
    todo = ResourceService('todo_mvc', ZeroMQMedium(port_random=True))
    todo.register_resource(PowerCollection("power", "fosdem_db"))
    todo.main()
