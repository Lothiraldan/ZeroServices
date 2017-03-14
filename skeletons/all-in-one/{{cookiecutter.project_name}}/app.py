from zeroservices import MemoryMedium, ResourceService, RealtimeResourceService
from zeroservices.backend.mongodb import MongoDBCollection, MongoDBResource
from zeroservices.discovery import MemoryDiscoveryMedium
from zeroservices.services import get_http_interface
import asyncio


# TODO implement your Auth logic here
class Auth(object):

    def authorized(self, handler, resource, method):
        return True


def main():
    loop = asyncio.get_event_loop()
    medium = MemoryMedium(loop, MemoryDiscoveryMedium)

    {% if cookiecutter.realtime_api %}
    service = RealtimeResourceService('{{cookiecutter.project_name}}', medium)
    {% else %}
    service = ResourceService('{{cookiecutter.project_name}}', medium)
    {% endif %}

    # Get the HTTP interface and start listening
    api = get_http_interface(service, loop, port='{{cookiecutter.api_port}}', auth=Auth(), allowed_origins="*")
    api = loop.run_until_complete(api)

    {% for resource in cookiecutter['resources (separated by comma)'].split(',') -%}
    service.register_resource(MongoDBCollection("{{resource}}", "{{cookiecutter.mongodb_database}}"))
    {% endfor %}

    # Start the service with API and resources
    loop.run_until_complete(service.start())
    loop.run_forever()


if __name__ == '__main__':
    main()
