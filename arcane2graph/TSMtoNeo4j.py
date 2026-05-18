from TCMtoTSM import TSM, VNode, SNode, Edge

def node_creation_query(node):
    return f"CREATE ({node.get_identifier()}:ValueNode {{name: {TSM.spec(node).name()}, value: {node.val()}}})"

def edge_creation_query(edge):
    return f"({edge.source().get_identifier()})-[]->({edge.target().get_identifier()})"

def TSM_creation_query(TSM):
    query = ""
    for node in TSM.get_value_nodes():
        query += node_creation_query(node) + "\n"
    
    for edge in TSM.get_containment_value_edges():
        query += edge_creation_query(edge) + "\n"
    
    return query



if __name__ == '__main__':
    from neo4j import GraphDatabase

    # URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
    URI = "<database-uri>"
    AUTH = ("<username>", "<password>")

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()

        # build graph here