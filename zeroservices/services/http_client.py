import requests
import json

try:
    from urlparse import urljoin, urlsplit, urlunsplit
except ImportError:
    from urllib.parse import urljoin, urlsplit, urlunsplit


def url_path_join(*parts):
    """Normalize url parts and join them with a slash."""
    schemes, netlocs, paths, queries, fragments = zip(*(urlsplit(part) for part in parts))
    scheme = first(schemes)
    netloc = first(netlocs)
    path = '/'.join(x.strip('/') for x in paths if x) + '/'
    query = first(queries)
    fragment = first(fragments)
    return urlunsplit((scheme, netloc, path, query, fragment))

def first(sequence, default=''):
    return next((x for x in sequence if x), default)


class BaseHTTPClient(object):

    def __init__(self, base_url):
        self.base_url = base_url
        self.parts = []

    def hello_world(self):
        return MethodCaller(self, "get", False)()

    def preprocess_request(self):
        return {}

    def __getattr__(self, action):
        return MethodCaller(self, action)

    def __getitem__(self, value):
        self.parts.append(value)
        return self


class MethodCaller(object):

    method_map = {'list': 'get', 'get': 'get', 'create': 'post',
                  'delete': 'delete', 'patch': 'patch'}

    def __init__(self, client, action, decode_json=True):
        self.client = client
        self.action = action
        self.decode_json = decode_json
        self.method = self.method_map.get(action, 'get')

    def __call__(self, **kwargs):
        url = url_path_join(self.client.base_url, *self.client.parts)
        additionnal = self.client.preprocess_request()
        response = getattr(requests, self.method)(url, data=json.dumps(kwargs),
                                                  **additionnal)
        response.raise_for_status()
        self.client.parts = []
        if self.decode_json:
            return response.json()
        else:
            return response.content.decode('utf-8')


class BasicAuthHTTPClient(BaseHTTPClient):

    def __init__(self, base_url, auth_tuple):
        super(BasicAuthHTTPClient, self).__init__(base_url)
        self.auth_tuple = auth_tuple

    def preprocess_request(self):
        return {'auth': self.auth_tuple}
