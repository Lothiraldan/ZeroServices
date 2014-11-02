def match(query, ressource):
    """Validated a query inspired by MongoDB and TaffyDB queries languages
    """
    for query_field_name, query_field_value in query.items():
        if ressource.get(query_field_name) != query_field_value:
            return False

    return True


def query_incoming(caller, rel, ressource_id, outgoing_ressource_type,
        *ressource_types):
    for ressource_type in ressource_types:
        query = {"_links.{}".format(rel):
                 {'$elemMatch':
                    {"target_id": (outgoing_ressource_type, ressource_id)}}}

        caller.logger.info("%s / %s", ressource_type, query)

        ressource = caller.send(collection=ressource_type, action='list',
                                where=query)

        if not len(ressource) == 1:
            caller.logger.info("Query %s", query)
            caller.logger.info("Ressources %s", ressource)
        assert len(ressource) == 1
        ressource = ressource[0]
        ressource_id = ressource['ressource_id']
        outgoing_ressource_type = ressource_type
    return ressource


def follow_links(caller, first_ressource, *rels):
    ressource = first_ressource
    for rel in rels:
        rel_links = ressource['_links']['latest'][rel]

        caller.logger.info('Rel %s, outgoing ressource %s',
            rel, rel_links)

        ressource_type, ressource_id = rel_links

        ressource = caller.send(collection=ressource_type, action='get',
            ressource_id=ressource_id)['ressource_data']
        caller.logger.info('Ressource %s', ressource)

    return ressource


