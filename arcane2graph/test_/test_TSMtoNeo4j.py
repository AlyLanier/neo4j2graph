from TSMtoNeo4j import *
import os

json_path = "arc_json/arc_json_tests"
processed_json = []
for filename in os.listdir(json_path):
    if filename.endswith(".json"):
        print(filename)
        file_path = os.path.join(json_path, filename)
        processed_json.append(TCM(file_path, 'mahyco'))

tsm = TSM(processed_json)
string_for_neo4j = TSM_creation_query(tsm)


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
print("ALL tests validated")