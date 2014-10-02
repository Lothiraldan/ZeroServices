def match(query, ressource):
    """Validated a query inspired by MongoDB and TaffyDB queries languages
    """
    for query_field_name, query_field_value in query.items():
        if ressource[query_field_name] != query_field_value:
            return False

    return True
