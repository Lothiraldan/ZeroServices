ZeroServices
============

Network services made easy and Micro-Services architectures made fucking
easy.

-  Free software: MIT license
-  Documentation: https://zeroservices.readthedocs.org.

QuickStart
----------

Let’s imagine you want an API exposing two resources Foo and Bar.

First some imports:

::

    from zeroservices import ZeroMQMedium, ResourceService, RealtimeResourceService
    from zeroservices.backend.mongodb import MongoDBCollection, MongoDBResource
    from zeroservices.services import get_http_interface

Now we declare a Service, it’s one node in the cluster:

::

    service = RealtimeResourceService('test', ZeroMQMedium(port_random=True))

We give it a name ``test`` and tell it to use ZeroMQ for communication.

Now let’s register our resources.

::

    service.register_resource(MongoDBCollection("foo", database_name="test"))
    service.register_resource(MongoDBCollection("bar", database_name="test"))

We declare two resources, ``foo`` and ``bar``, both using the ``test``
MongoDB database.

Last but not the least, we still need our API but before we need to
declare how users will be authenticated, let’s allow all users right
now:

::

    class Auth(object):

        def authorized(self, handler, resource, method):
            return True

And now let’s add an API using this Auth logic:

::

    api = get_http_interface(service, port='5001', auth=Auth(), allowed_origins="*")

We use the get\_http\_interface, pass the service and our custom Auth
object. We tell the API to listen on 5001 port and allow all origins
(for CORS requests).

And now let’s start the whole service:

::

    service.main()

The whole example file will look like:

::

    from zeroservices import ZeroMQMedium, ResourceService, RealtimeResourceService
    from zeroservices.backend.mongodb import MongoDBCollection, MongoDBResource
    from zeroservices.services import get_http_interface


    class Auth(object):

        def authorized(self, handler, resource, method):
            return True


    if __name__ == '__main__':
        service = RealtimeResourceService('test', ZeroMQMedium(port_random=True))
        api = get_http_interface(service, port='5001', auth=Auth(), allowed_origins="*")
        service.register_resource(MongoDBCollection("foo", "test"))
        service.register_resource(MongoDBCollection("bar", "test"))

        service.main()

Let’s play with our API now (I use the awesome httpie project for
examples):

::

    $> http localhost:5001
    HTTP/1.1 200 OK
    Access-Control-Allow-Headers: X-CUSTOM-ACTION
    Access-Control-Allow-Origin: *
    Content-Length: 20
    Content-Type: text/html; charset=UTF-8
    Date: Mon, 23 Feb 2015 22:43:19 GMT
    Etag: "af6572026125710f90d41f0ffe6e63e6f4089ece"
    Server: TornadoServer/4.0.2

    Hello world from api

Nothing fancy here, let’s try to play with our foo resource (I will drop
some useless headers for readibility):

::

    $> http localhost:5001/foo/
    HTTP/1.1 200 OK
    Content-Type: application/json

    []

Let’s try to add a new foo resource:

::

    $> http POST localhost:5001/foo/ resource_id=#1 resource_data:='{"hello": "world"}'

Skeleton generator
------------------

You will find in skeletons directory some cookiecutter templates that
you can use to quickstart a new project or play quickly with
ZeroServices.

Install cookiecutter (https://github.com/audreyr/cookiecutter), go into
one subdirectory and type:

::

    cookiecutter .

Answer all questions and then you will have a directory with your brand
new project.

Event sniffer
-------------

You’ll find a event sniffer in bin directory, it will output all events
in the network, here is an example:

::

    $> python sniffer.py
    INFO:sniffer.medium:Set service sniffer, node_info: {'pub_port': 55655, 'node_type': 'node', 'node_id': 'f1be938ad5fb4c70920815b67cdd52e4', 'name': 'sniffer', 'server_port': 62103}

    [power.create.power_1] ({u'action': u'create', u'resource_name': u'power', u'resource_data': {u'status': u'pending', u'description': u'My first autosum resource', u'value': 42}, u'resource_id': u'power_1'},) {}
    [power.patch.power_1] ({u'action': u'patch', u'patch': {u'$set': {u'status': u'done', u'result': 1764}}, u'resource_name': u'power', u'resource_id': u'power_1'},) {}
    [power.create.power_3] ({u'action': u'create', u'resource_name': u'power', u'resource_data': {u'status': u'pending', u'description': u'Another one', u'value': 3}, u'resource_id': u'power_3'},) {}
    [power.patch.power_3] ({u'action': u'patch', u'patch': {u'$set': {u'status': u'done', u'result': 9}}, u'resource_name': u'power', u'resource_id': u'power_3'},) {}
    [power.create.power_5] ({u'action': u'create', u'resource_name': u'power', u'resource_data': {u'status': u'pending', u'description': u'Another one which should be process immediately', u'value': 24}, u'resource_id': u'power_5'},) {}
    [power.patch.power_5] ({u'action': u'patch', u'patch': {u'$set': {u'status': u'done', u'result': 576}}, u'resource_name': u'power', u'resource_id': u'power_5'},) {}

Features
--------

-  TODO
