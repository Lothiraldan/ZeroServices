import json
import unittest
import responses
from mock import sentinel

from zeroservices.services import HTTPClient
from zeroservices.services import get_http_interface, BasicAuth

class HttpClientTestCase(unittest.TestCase):

    def setUp(self):
        self.base_url = "http://localhost"
        self.collection_name = "collection"
        self.ressource_id = "1"
        self.ressource_body = {'_id': self.ressource_id, 'key': 'value'}
        self.client = HTTPClient(self.base_url)
        self.app = get_http_interface(sentinel.SERVICE, bind=False)

        # URLS
        self.collection_url = self.base_url + \
            self.app.reverse_url("collection", self.collection_name)
        self.ressource_url = self.base_url + \
            self.app.reverse_url("ressource", self.collection_name,
                self.ressource_id)

    @responses.activate
    def test_main(self):
        expected_body = "Hello world from api"
        responses.add(
            responses.GET, self.base_url + self.app.reverse_url("main"),
            body=expected_body, status=200)

        response = self.client.hello_world()

        self.assertEquals(response, expected_body)

    @responses.activate
    def test_list_on_collection(self):
        expected_body = [self.ressource_body]

        responses.add(
            responses.GET, self.collection_url,
            body=json.dumps(expected_body), status=200)

        response = self.client[self.collection_name].list()

        self.assertEquals(response, expected_body)

    @responses.activate
    def test_get_on_ressource(self):
        expected_body = self.ressource_body

        responses.add(
            responses.GET, self.ressource_url,
            body=json.dumps(expected_body), status=200)

        response = self.client[self.collection_name][self.ressource_id].get()

        self.assertEquals(response, expected_body)

    @responses.activate
    def test_post_on_ressource(self):
        expected_body = {'_id': self.ressource_id}

        responses.add(
            responses.POST, self.ressource_url,
            body=json.dumps(expected_body), status=200)

        response = self.client[self.collection_name][self.ressource_id].create(**self.ressource_body)

        self.assertEquals(response, expected_body)

        self.assertEquals(len(responses.calls), 1)
        request_body = responses.calls[0].request.body
        self.assertEquals(request_body, json.dumps(self.ressource_body))
