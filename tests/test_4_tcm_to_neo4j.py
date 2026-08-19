from panoramix.tcm_to_neo4j import *
from panoramix.tcm_to_tsm import TSM
from panoramix.neo4j_graph_functions import GraphFunctions as gf

from tests.test_db_graphs import verify_db_tsm

import os
import unittest

class TestTCMtoNeo4j(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.URI = "bolt://localhost:7687"
        cls.AUTH = (os.getenv("NEO4J_USER_TESTS"), os.getenv("NEO4J_PASSWORD_TESTS"))
        if not all(cls.AUTH): cls.AUTH = ("neo4j", "password")
        cls.TCMS = [TCM(os.path.join("arc_json/arc_json_tests", filename), 'mahyco') for filename in os.listdir("arc_json/arc_json_tests") if filename.endswith(".json")]
        cls.TSM = TSM(cls.TCMS)
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        del cls.TSM, cls.URI, cls.AUTH
        return super().tearDownClass()

    def test_validate_db_from_tcm(self):

        with GraphDatabase.driver(self.URI, auth=self.AUTH) as driver:
            driver.verify_connectivity()
            driver.execute_query("MATCH (p)\nDETACH DELETE p") # remove current graph
            for tcm in self.TCMS: # build graph here
                TCMtoDB.expand_neo4j_tsm(driver, self.AUTH[0], tcm)
            result = driver.execute_query(gf.get_TSM_query())
            self.assertTrue(verify_db_tsm(self.TSM, result), "TCMs have not been correctly translated to neo4j, blame the coder please") # verify if the tcms have been translated correctly into Neo4j
            
