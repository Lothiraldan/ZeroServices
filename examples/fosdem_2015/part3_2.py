from zeroservices import ZeroMQMedium, ResourceService
from zeroservices.backend.mongodb import MongoDBCollection

if __name__ == '__main__':
    todo = ResourceService('todo_mvc', ZeroMQMedium(port_random=True))
    todo.register_resource(MongoDBCollection("power", "fosdem_db"))
    todo.main()
