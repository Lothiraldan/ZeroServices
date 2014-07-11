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


class HTTPClient(object):

    def __init__(self, base_url):
        self.base_url = base_url
        self.parts = []

    def hello_world(self):
        response = requests.get(self.base_url)
        return response.content.decode('utf-8')

    def __getattr__(self, action):
        return MethodCaller(self, action)

    def __getitem__(self, value):
        self.parts.append(value)
        return self


class MethodCaller(object):

    method_map = {'list': 'get', 'get': 'get', 'create': 'post'}

    def __init__(self, client, action):
        self.client = client
        self.action = action
        self.method = self.method_map.get(action)

    def __call__(self, **kwargs):
        url = url_path_join(self.client.base_url, *self.client.parts)
        response = getattr(requests, self.method)(url, data=json.dumps(kwargs))
        self.client.parts = []
        return response.json()
