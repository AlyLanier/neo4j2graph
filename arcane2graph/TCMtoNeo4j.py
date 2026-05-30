from jsonToTCM import TCM
from TCMtoTSM import TSM
from TSMtoNeo4j import STARTING_CHAR, sanitize
from neo4j import GraphDatabase
import os
from functools import reduce


class TCMtoDB:
    creation_match_counter = 0

    ################## Expanding db with a tcm ######################
    @staticmethod
    def expand_neo4j_tsm(driver, db, tcm):
        queries = [[], []]
        with driver.session(database = db) as session:
            TCMtoDB.process_option_value_to_neo4j(session, None, tcm.search_root(tcm.get_edges()), *tcm.get_model(), queries)
            final_query = ""
            for query in queries:
                final_query += reduce(lambda x, y: x + "\n" + y, query)+'\n'
            #print(final_query)
            #session.run(final_query)
        creation_match_counter = 0

    @staticmethod
    def process_option_value_to_neo4j(session, mother_specification_element, current_node, tcm_nodes, tcm_edges, creation_queries):
        if not TCMtoDB.is_result_empty(TCMtoDB.query_node(session, "ValueNode", {"identifier": current_node.get_identifier()})): return
        print(current_node)
        TCMtoDB.queries_append(creation_queries, TCMtoDB.v_node_creation_query(*current_node.get_v_node_creation_info()))    
        db_msn_element, db_sn_element = None, None
        tcm_mother_node = TCM.find_node_from_edge(tcm_edges, current_node, from_source = False)
        if TCMtoDB.is_possible_query(mother_specification_element):
            db_msn_element, db_sn_element = TCMtoDB.query_find_s_option(session, mother_specification_element, current_node)[0]
            print(db_msn_element)
            print(db_sn_element)
        
        if db_sn_element is not None:
            new_msn_element = db_sn_element.element_id
        else:
            print(mother_specification_element is None)
            if mother_specification_element is None: new_msn_element = TCMtoDB.process_root(session, current_node, creation_queries) #node is root
            else:                                    new_msn_element = TCMtoDB.process_node(session, current_node, mother_specification_element, creation_queries)
        
        TCMtoDB.queries_append(creation_queries, TCMtoDB.edge_creation_query({'identifier' : STARTING_CHAR + current_node.get_identifier()}, new_msn_element, "IS_SPECIFIED_BY"))           
        
        current_node_children = TCM.find_children(current_node, tcm_edges)
        print(current_node_children)
        for current_node_child in current_node_children:
            TCMtoDB.process_option_value_to_neo4j(session, new_msn_element, current_node_child, tcm_nodes, tcm_edges, creation_queries)
            TCMtoDB.queries_append(creation_queries, f"CREATE ({STARTING_CHAR}{current_node.get_identifier()})-[:CONTAINS]->(:ValueNode {{identifier: '{current_node_child.get_identifier()}'}})")

    @staticmethod
    def process_root(session, current_node, queries):
        new_s_node_query = TCMtoDB.query_s_root(session)
        if not TCMtoDB.is_result_empty(new_s_node_query):
            for record in new_s_node_query:
                return record[0].element_id #only 1 specification root #TODO, very annoying to get results from query
        else:
            TCMtoDB.queries_append(queries, TCMtoDB.s_node_creation_query(current_node.get_identifier(), *current_node.get_s_node_creation_info()))
            return {"identifier" : STARTING_CHAR + current_node.get_identifier()}

    @staticmethod
    def process_node(session, current_node, mother_specification_element, queries):
        print("yow")
        TCMtoDB.queries_append(queries, TCMtoDB.s_node_creation_query(current_node.get_identifier(), *current_node.get_s_node_creation_info()))
        TCMtoDB.queries_append(queries, TCMtoDB.edge_creation_query(mother_specification_element, new_msn_element, "CONTAINS"))
        return {"identifier" : STARTING_CHAR + current_node.get_identifier()}


    #################### Util #######################

    @staticmethod
    def is_possible_query(db_identifier):
        return not(db_identifier is None or isinstance(db_identifier, dict))
    
    @staticmethod
    def queries_append(queries, obj):
        if isinstance(obj, str): queries[1].append(obj)
        else:
            queries[1].append(obj[0])
            if obj[1]: queries[0].append(obj[1])
            


    ################## Queries to find data in db ###################

    @staticmethod
    def query_s_root(session):
        query = f"MATCH (root:SpecificationNode)\nWHERE NOT EXISTS((root)<-[:CONTAINS]-())\nRETURN root"
        return session.run(query)

    @staticmethod
    def query_node(session, node_type, properties):
        query = f"MATCH (NT:{node_type}"
        if properties:
            query += " {"
            for k, v in properties.items():
                query += f"{k}: '{v}',"
            query = query[:-1]+"}"
        query += ")\nRETURN NT"
        return session.run(query)

    @staticmethod
    def query_find_s_option(session, mother_specification_element, current_node):
        query = f"""MATCH (SNM:SpecificationNode)
                    WHERE elementId(SNM) = '{mother_specification_element}'
                    OPTIONAL MATCH (SN:SpecificationNode {{name: '{current_node.name()}'}})<-[:CONTAINS]-(SNM)
                    RETURN SNM, SN
                    """
        return TCMtoDB.get_elements_query(session.run(query))

    @staticmethod
    def is_result_empty(query_result):
        return query_result.peek() is None

    @staticmethod
    def get_elements_query(result_query):
        return [e for e in result_query]


    ############### queries to create objects in db ################

    @staticmethod
    def v_node_creation_query(identifier, value):
        return f"CREATE ({STARTING_CHAR}{identifier}:ValueNode {{value: {sanitize(value)}, identifier: '{identifier}'}})"

    @staticmethod
    def s_node_creation_query(identifier, name, stype):
        return f"CREATE ({STARTING_CHAR}{identifier}:SpecificationNode {{name: '{name}', type: '{stype}'}})"

    @staticmethod
    def edge_creation_query(ms_element, cs_element, relation):
        setup = ""
        token = [None, None]
        for i, e in enumerate([ms_element, cs_element]):
            if not isinstance(e, dict):
                setup += f"MATCH (e{TCMtoDB.creation_match_counter}) WHERE elementId(e{TCMtoDB.creation_match_counter}) = '{e}'"
                token[i] = f"e{TCMtoDB.creation_match_counter}"
                TCMtoDB.creation_match_counter += 1
            else: token[i] = e['identifier']
        
        return f"CREATE ({token[0]})-[:{relation}]->({token[1]})", setup


def main():
    json_path = "arc_json"
    processed_json = []
    counter = 0
    for filename in os.listdir(json_path):
        if filename.endswith(".json"):
            counter += 1
            if counter < 3: continue
            file_path = os.path.join(json_path, filename)
            print(file_path)
            test = TCM(file_path)
            processed_json.append(test)
            break

    # URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")
    DB_NAME = AUTH[0]

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()

        for tcm in processed_json:
            TCMtoDB.expand_neo4j_tsm(driver, DB_NAME, tcm)
        
    return


    query = f"""MATCH (SNM:SpecificationNode)<-[:IS_SPECIFIED_BY]-(:ValueNode {{identifier: "a1566f82ecbad4341fdb52a472e4c5b1"}})
            OPTIONAL MATCH (SN:SpecificationNode {{name: "nme"}})<-[:CONTAINS]-(SNM)
            RETURN SNM, SN
            """
    test = driver.execute_query(query)
    print(test[0]) #records
    print(test[0][0]) # first of records if multiple possibilities
    print(test[0][0][0]) # first return value of query
    print(test[0][0][0].element_id)
    print(test[0][0][1])

        

if __name__ == '__main__':
    main()