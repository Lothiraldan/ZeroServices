from zeroservices import ZeroMQMedium, ResourceService, RealtimeResourceService
from zeroservices.backend.mongodb import MongoDBCollection, MongoDBResource
from zeroservices.services import get_http_interface


# TODO implement your Auth logic here
class Auth(object):

    def authorized(self, handler, resource, method):
        return True


if __name__ == '__main__':
    {% if cookiecutter.realtime_api %}
    service = RealtimeResourceService('{{cookiecutter.project_name}}', ZeroMQMedium(port_random=True))
    {% else %}
    service = ResourceService('{{cookiecutter.project_name}}', ZeroMQMedium(port_random=True))
    {% endif %}
    api = get_http_interface(service, port='{{cookiecutter.api_port}}', auth=Auth(), allowed_origins="*")

    {% for resource in cookiecutter['resources (separated by comma)'].split(',') -%}
    service.register_resource(MongoDBCollection("{{resource}}", "{{cookiecutter.mongodb_database}}"))
    {% endfor %}

    # Start the service with API and resources
    service.main()
