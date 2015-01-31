from zeroservices import ZeroMQMedium, RealtimeResourceService
from zeroservices.services import get_http_interface


# Http utils

class Auth(object):

    def authorized(self, handler, resource, method):
        return True


if __name__ == '__main__':
    todo = RealtimeResourceService('todo_mvc', ZeroMQMedium(port_random=True))
    application = get_http_interface(todo, port=5001, auth=Auth(), allowed_origins="*")
    todo.main()
