def match(query, resource):
    """Validated a query inspired by MongoDB and TaffyDB queries languages
    """
    for query_field_name, query_field_value in query.items():
        if resource.get(query_field_name) != query_field_value:
            return False

    return True


def query_incoming(caller, rel, resource_id, outgoing_resource_type,
        *resource_types):
    for resource_type in resource_types:
        query = {"_links.{}".format(rel):
                 {'$elemMatch':
                    {"target_id": (outgoing_resource_type, resource_id)}}}

        caller.logger.info("%s / %s", resource_type, query)

        resource = yield from caller.send(collection=resource_type,
                                          action='list',
                                          where=query)

        if not len(resource) == 1:
            caller.logger.info("Query %s", query)
            caller.logger.info("Resources %s", resource)
        assert len(resource) == 1
        resource = resource[0]
        resource_id = resource['resource_id']
        outgoing_resource_type = resource_type
    return resource


def follow_links(caller, first_resource, *rels):
    resource = first_resource
    for rel in rels:
        rel_links = resource['_links']['latest'][rel]

        caller.logger.info('Rel %s, outgoing resource %s',
            rel, rel_links)

        resource_type, resource_id = rel_links

        resource = caller.send(collection=resource_type, action='get',
            resource_id=resource_id)['resource_data']
        caller.logger.info('Resource %s', resource)

    return resource


