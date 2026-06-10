import os
import re
from neo4j import GraphDatabase
from TCMtoTSM import TSM
from jsonToTCM import TCM

STARTING_CHAR = "a"

def sanitize(obj):
    if obj is None: return "null"
    if isinstance(obj, str): return f"\'{obj}\'"
    return obj

def v_node_creation_query(node):
    return f"CREATE ({STARTING_CHAR}{node.get_identifier()}:ValueNode {{value: {sanitize(node.val())}, identifier: {sanitize(node.get_identifier())}}})"
    #                 ^^^^^^^^^^^^^ -- to make it so the identifier does not start with a number, neo4j does not like it

def s_node_creation_query(node):
    return f"CREATE ({STARTING_CHAR}{node.get_identifier()}:SpecificationNode {{name: {sanitize(node.name())}, type: {sanitize(node.stype_name())}}})"

def edge_creation_query(edge, relation):
    return f"CREATE ({STARTING_CHAR}{edge.source().get_identifier()})-[{relation}]->({STARTING_CHAR}{edge.target().get_identifier()})"

def TSM_creation_query(tsm):
    query = ""

    for node in tsm.get_value_nodes():
        query += v_node_creation_query(node) + "\n"
    
    for node in tsm.get_specification_nodes():
        query += s_node_creation_query(node) + "\n"
    
    for edge in tsm.get_containment_edges():
        query += edge_creation_query(edge, ":CONTAINS") + "\n"
    
    for edge in tsm.get_specification_edges():
        query += edge_creation_query(edge, ":IS_SPECIFIED_BY") + "\n"
    
    print(query)
    return query[:-1]


def build_tsm(files):
    max_process = 2
    json_path = "arc_json"
    processed_json = []
    for filename in files:
        file_path = os.path.join(json_path, filename)
        print(file_path)
        test = TCM(file_path)
        processed_json.append(test)
    
    return TSM(processed_json)

def main():
    
    test_tsm = build_tsm(['Mahyco_0x5b67d7517e00.json', 'Mahyco_0x5be0ee5cb7b0.json'])
    string_for_neo4j = TSM_creation_query(test_tsm)
    

    # URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        # remove current graph
        driver.execute_query("MATCH (p)\nDETACH DELETE p")
        print("deleted previous db")

        # build graph here
        driver.execute_query(string_for_neo4j)

        

if __name__ == '__main__':
    main()