# -*- coding: utf-8 -*-
import operator


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


def accumulate(iterable, func=operator.add):
    'Return running totals'
    # accumulate([1,2,3,4,5]) --> 1 3 6 10 15
    # accumulate([1,2,3,4,5], operator.mul) --> 1 2 6 24 120
    it = iter(iterable)
    total = next(it)
    yield total
    for element in it:
        total = func(total, element)
        yield total
