from zeroservices import ZeroMQMedium, RealtimeResourceService
from zeroservices.services import get_http_interface


# Http utils

class Auth(object):

    def authorized(self, handler, resource, method):
        return True


if __name__ == '__main__':
    app = RealtimeResourceService('power_fosdem', ZeroMQMedium(port_random=True))
    application = get_http_interface(app, port=5001, auth=Auth(), allowed_origins="*")
    app.main()
