"""Ontology definitions frozen with the graph that was built from them."""


def entity_metadata(ontology, sensitive_columns=()):
    sensitive = set(sensitive_columns)
    hidden = {
        attribute.name for cls in ontology.classes for attribute in cls.attributes
        if attribute.pii or (cls.mapping and f"{cls.mapping.source_table}.{attribute.source_column}" in sensitive)
    }
    for relationship in ontology.relationships:
        mapping = relationship.mapping
        hidden.update(attribute.name for attribute in relationship.properties
                      if attribute.pii or (mapping and f"{mapping.table}.{attribute.source_column}" in sensitive))
        if mapping:
            hidden.update(column for column in mapping.property_columns if f"{mapping.table}.{column}" in sensitive)
    return {
        "name": ontology.name,
        "version": ontology.version,
        "hidden_properties": sorted(hidden),
        "classes": [cls.model_dump(mode="json", include={"name", "description", "mapping", "attributes"})
                    for cls in ontology.classes],
        "relationships": [rel.model_dump(mode="json", exclude={"origin"}) for rel in ontology.relationships],
    }
