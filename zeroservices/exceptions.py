class ServiceUnavailable(Exception):
    pass

class UnknownNode(Exception):
    pass

class UnknownService(Exception):
    pass

class ResourceException(Exception):

    def __init__(self, error_message):
        self.error_message = error_message

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "ResourceException(%s)" % self.error_message

class ResourceNotFound(Exception):
    pass
