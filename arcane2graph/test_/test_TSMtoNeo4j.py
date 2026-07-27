from TSMtoNeo4j import *
import os
from Neo4jGraphFunctions import GraphFunctions as gf
from test_.test_db_graphs import verify_db_tsm
    

def validate_db_from_TSM():
    json_path = "arc_json/arc_json_tests"
    processed_json = []
    for filename in os.listdir(json_path):
        if filename.endswith(".json") and filename != "Mahyco_test_Alyssia.json":
            print(filename)
            file_path = os.path.join(json_path, filename)
            processed_json.append(TCM(file_path, 'mahyco'))

    tsm = TSM(processed_json)
    tsm_for_neo4j = TSM_creation_query(tsm)


    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        driver.execute_query("MATCH (p)\nDETACH DELETE p") # remove current graph
        driver.execute_query(tsm_for_neo4j) # build graph here
        result = driver.execute_query(gf.get_TSM_query())
        verify_db_tsm(tsm, result) # verify if the tsm has been translated correctly into Neo4j

    print("ALL tests validated")