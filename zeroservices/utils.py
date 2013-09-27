# -*- coding: utf-8 -*-
import sys
from zmq.eventloop import ioloop, zmqstream
import zmq
import logging


def extract_links(links, link_type):
    return [link for link in links if link.startswith(link_type)]


def pop_and_replace_link(links, link_type, replace_by):
    for ind, link in enumerate(links):
        if link.startswith(link_type):
            del links[ind]
            break

    links.append(replace_by)


def maybe_asynchronous(f):
    def wrapped(*args, **kwargs):
        try:
            callback = kwargs.pop('callback')
        except KeyError:
            callback = None

        result = f(*args, **kwargs)

        if callback is not None:
            callback(result)
        else:
            return result
    return wrapped
