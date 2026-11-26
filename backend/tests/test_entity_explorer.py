import networkx as nx

from backend.app.services import entity_explorer as entities


def test_composite_identity_and_neighborhood_preserve_scope_and_direction():
    graph = nx.MultiDiGraph()
    for label, identity in [("Supplier", "007|EU"), ("Warehouse", "007|EU"),
                            ("Shipment", "009"), ("Order", "010"), ("Supplier", "isolated")]:
        graph.add_node(f"{label}:{identity}", label=label, source_key=identity)
    root = "Supplier:007|EU"
    graph.add_edge("Warehouse:007|EU", root, key="STORES", type="STORES", capacity=12)
    graph.add_edge(root, "Shipment:009", key="SENDS", type="SENDS")
    graph.add_edge("Shipment:009", "Order:010", key="FULFILLS", type="FULFILLS")
    graph.add_edge("Order:010", "Supplier:isolated", key="USES", type="USES")
    graph.add_node("Warehouse:alone", label="Warehouse", source_key="alone")

    def search(term, label="", prefix=False):
        return entities.local_search(graph, dict, term, label, prefix, {})["matches"]

    assert {item["label"] for item in search("007|EU")} == {"Supplier", "Warehouse"}
    assert [item["id"] for item in search("007|EU", "Supplier")] == [root]
    assert search("7|EU") == search("007|eu") == []
    assert len(search("007|", prefix=True)) == 2

    def view(node, hops):
        return entities.neighborhood(
            entities.local_node(graph, dict, node), hops,
            lambda batch, expanded, limit: entities.local_edges(graph, dict, batch, expanded, limit), {},
            node_count=len(graph), edge_count=graph.number_of_edges())

    one, two, three = [view(root, depth) for depth in (1, 2, 3)]
    assert [len(item["graph"]["nodes"]) for item in (one, two, three)] == [3, 4, 5]
    assert (one["root"]["incoming"], one["root"]["outgoing"]) == (1, 1)
    assert {"source": "Warehouse:007|EU", "target": root, "key": "STORES",
            "properties": {"type": "STORES", "capacity": 12}} in one["graph"]["edges"]
    assert not one["graph"]["truncated"]
    assert view("Warehouse:alone", 3)["graph"]["edges"] == []


def test_high_degree_expansion_is_bounded_and_explicitly_truncated():
    graph = nx.MultiDiGraph()
    graph.add_node("root", label="Root")
    for i in range(600):
        graph.add_edge("root", f"leaf:{i}", key="CONNECTS", type="CONNECTS")
    view = entities.neighborhood(
        entities.local_node(graph, dict, "root"), 3,
        lambda batch, expanded, limit: entities.local_edges(graph, dict, batch, expanded, limit),
        {}, node_count=len(graph), edge_count=graph.number_of_edges())
    assert view["root"]["outgoing"] == 600
    assert view["graph"]["truncated"]
    assert len(view["graph"]["nodes"]) == entities.NODE_LIMIT
    assert len(view["graph"]["edges"]) <= entities.EDGE_LIMIT
