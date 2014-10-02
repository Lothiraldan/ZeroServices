import six

from voluptuous import Schema, MultipleInvalid, Required, Any


def _str(value):
    if not isinstance(value, six.string_types):
        raise ValueError("{} is not a string".format(value))


REGISTRATION_SCHEMA = Schema({Required('node_type'): _str,
                              Required('node_id'): _str,
                              Required('name'): _str}, extra=True)

