from Neo4jGraphFunctions import GraphFunctions
from neo4j import GraphDatabase
from test_.test_TCMtoTSM import test_tsm

def validate_db(by_query = True):
    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")
    DB_NAME = AUTH[0]

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()

        with driver.session(database = DB_NAME) as session:
            if by_query:    db_validity = session.run(GraphFunctions.Db_Validity_query()).single()
            else:           tsm = GraphFunctions.TSM_from_db(session)
    
    if by_query:    assert db_validity[0] == True
    else:           test_tsm(tsm)
    print('ALL tests validated')
