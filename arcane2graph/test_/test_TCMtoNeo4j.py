from TCMtoNeo4j import *
from TCMtoTSM import TSM
import os
from Neo4jGraphFunctions import GraphFunctions as gf
from test_.test_db_graphs import verify_db_tsm


def validate_db_from_tcm():
    json_path = "arc_json/arc_json_tests"
    processed_json = []
    for filename in os.listdir(json_path):
        if filename.endswith(".json"):
            print(filename)
            file_path = os.path.join(json_path, filename)
            processed_json.append(TCM(file_path, 'mahyco'))

    tsm = TSM(processed_json)

    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")
    DB_NAME = AUTH[0]

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        driver.execute_query("MATCH (p)\nDETACH DELETE p") # remove current graph
        for tcm in processed_json: # build graph here
            TCMtoDB.expand_neo4j_tsm(driver, DB_NAME, tcm)
        result = driver.execute_query(gf.get_TSM_query())
        verify_db_tsm(tsm, result)
        
    print("ALL tests validated")