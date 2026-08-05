from arcane2graph.Neo4jGraphFunctions import GraphFunctions
from neo4j import GraphDatabase
import os
import unittest

class TestDB(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.URI = "bolt://localhost:7687"
        cls.AUTH = (os.getenv("NEO4J_USER_TESTS"), os.getenv("NEO4J_PASSWORD_TESTS"))
        if not all(cls.AUTH): cls.AUTH = ("neo4j", "password")
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        del cls.URI, cls.AUTH
        return super().tearDownClass()

    def test_validate_db(self):
       
        with GraphDatabase.driver(self.URI, auth=self.AUTH) as driver:
            driver.verify_connectivity()

            with driver.session(database = self.AUTH[0]) as session:
                db_validity = session.run(GraphFunctions.Db_Validity_query()).single()
        
        self.assertTrue(db_validity[0], "The database TSM does not complete the tests, there is a problem in it")
