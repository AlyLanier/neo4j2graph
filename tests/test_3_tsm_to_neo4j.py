from src.panoramix.tsm_to_neo4j import *
from src.panoramix.neo4j_graph_functions import GraphFunctions as gf
from tests.test_db_graphs import verify_db_tsm

import os
import unittest

class TestTSMtoNeo4J(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.URI = "bolt://localhost:7687"
        cls.AUTH = (os.getenv("NEO4J_USER_TESTS"), os.getenv("NEO4J_PASSWORD_TESTS"))
        if not all(cls.AUTH): cls.AUTH = ("neo4j", "password")
        cls.TSM = TSM([TCM(os.path.join("arc_json/arc_json_tests", filename), 'mahyco') for filename in os.listdir("arc_json/arc_json_tests") if filename.endswith(".json")])
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        del cls.TSM, cls.URI, cls.AUTH
        return super().tearDownClass()

    def test_validate_db_from_TSM(self):
        tsm_for_neo4j = TSM_creation_query(self.TSM)

        with GraphDatabase.driver(self.URI, auth=self.AUTH) as driver:
            driver.verify_connectivity()
            print(driver.execute_query("SHOW PROCEDURES yield name RETURN name ORDER BY name DESC"))
            print(driver.execute_query("WITH TSM_Statistics.mean([7, -1, 18], '-inf') as testminf RETURN testminf, testminf = -1"))
            driver.execute_query("MATCH (p)\nDETACH DELETE p") # remove current graph
            driver.execute_query(tsm_for_neo4j) # build graph here
            result = driver.execute_query(gf.get_TSM_query())
            self.assertTrue(verify_db_tsm(self.TSM, result), "TSM has not been correctly translated to neo4j, blame the coder please") # verify if the tsm has been translated correctly into Neo4j
