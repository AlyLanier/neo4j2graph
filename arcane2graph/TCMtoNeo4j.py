from jsonToTCM import TCM
from TCMtoTSM import TSM
from TSMtoNeo4j import STARTING_CHAR, sanitize
from neo4j import GraphDatabase
import os
from functools import reduce


class TCMtoDB:
    MAX_MATCH_PER_QUERY = 15
    token_counter = 0
    final_queries = {"node_creation" : [], "node_matching" : {}, "edge_creation" : []}

    ################## Expanding db with a tcm ######################
    @staticmethod
    def expand_neo4j_tsm(driver, db, tcm):
        TCMtoDB.token_counter = 0
        TCMtoDB.final_queries = {"node_creation" : [], "node_matching" : {}, "edge_creation" : []}
        with driver.session(database = db) as session:
            TCMtoDB.process_option_value_to_neo4j(session, None, tcm.search_root(tcm.get_edges()), *tcm.get_model())
            
            TCMtoDB.process_final_queries(session)
            #session.run(final_query)
        #driver.execute_query(final_query)

    @staticmethod
    def process_option_value_to_neo4j(session, mother_specification_element, current_node, tcm_nodes, tcm_edges):
        if not TCMtoDB.is_result_empty(TCMtoDB.query_node(session, "ValueNode", {"identifier": current_node.get_identifier()})): return
        print(f"Node to add to the graph : {current_node}")
        TCMtoDB.v_node_creation_query(*current_node.get_v_node_creation_info())  
        db_msn_element, db_sn_element = None, None
        if TCMtoDB.is_possible_query(mother_specification_element):
            db_msn_element, db_sn_element = TCMtoDB.query_find_s_option(session, mother_specification_element, current_node)[0]
            #print(f"mother specification node : {db_msn_element}")
            #print(f"specification node : {db_sn_element}")
        
        if db_sn_element is not None:
            new_msn_element = db_sn_element.element_id
        else:
            #print(f"have to create s_node, is this root ? {mother_specification_element is None}")
            if mother_specification_element is None: new_msn_element = TCMtoDB.process_root(session, current_node) #node is root
            else:                                    new_msn_element = TCMtoDB.process_node(session, current_node, mother_specification_element)
        
        TCMtoDB.edge_creation_query({'identifier' : STARTING_CHAR + current_node.get_identifier()}, new_msn_element, "IS_SPECIFIED_BY")
        
        current_node_children = TCM.find_children(current_node, tcm_edges)
        for current_node_child in current_node_children:
            TCMtoDB.process_option_value_to_neo4j(session, new_msn_element, current_node_child, tcm_nodes, tcm_edges)
            TCMtoDB.edge_creation_query({'identifier': STARTING_CHAR+current_node.get_identifier()}, [current_node_child.get_identifier()], "CONTAINS")


    @staticmethod
    def process_root(session, current_node):
        new_s_node_query = TCMtoDB.query_s_root(session)
        if not TCMtoDB.is_result_empty(new_s_node_query):
            for record in new_s_node_query:
                return record[0].element_id #only 1 specification root #TODO, very annoying to get results from query
        else:
            TCMtoDB.s_node_creation_query(current_node.get_identifier(), current_node.name(), current_node.get_stype())
            return {"identifier" : current_node.get_identifier()}

    @staticmethod
    def process_node(session, current_node, mother_specification_element):
        TCMtoDB.s_node_creation_query(current_node.get_identifier(), current_node.name(), current_node.get_stype())
        TCMtoDB.edge_creation_query(mother_specification_element, {"identifier" : current_node.get_identifier()}, "CONTAINS")
        return {"identifier" : current_node.get_identifier()}


    #################### Util #######################

    @staticmethod
    def is_possible_query(db_identifier):
        return not(db_identifier is None or isinstance(db_identifier, dict))
            

    ################## Queries to find data in db ###################

    @staticmethod
    def query_s_root(session):
        query = f"MATCH (root:SpecificationNode)\nWHERE NOT EXISTS((root)<-[:CONTAINS]-())\nRETURN root"
        return session.run(query) #TODO

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
        TCMtoDB.final_queries["node_creation"].append(lambda _: (f"CREATE (:ValueNode {{value: {sanitize(value)}, identifier: '{identifier}'}})", None))
        TCMtoDB.final_queries["node_matching"][identifier] = lambda counter: f"MATCH (e{counter}:ValueNode {{identifier: '{identifier}')}}"

    @staticmethod
    def s_node_creation_query(identifier, name, stype):
        TCMtoDB.final_queries["node_creation"].append(lambda counter: (f"CREATE (e{counter}:SpecificationNode {{name: '{name}', type: '{stype}'}})", identifier))
        #TCMtoDB.final_queries["node_matching"][identifier] = lambda counter: f"MATCH (e{counter}) WHERE elementId(e{counter}) = " #will be completed on runtime

    @staticmethod
    def edge_creation_query(ms_element, cs_element, relation):
        identifiers = [None, None]
        for i, e in enumerate([ms_element, cs_element]):
            if isinstance(e, str) and not (e in TCMtoDB.final_queries["node_matching"]):
                TCMtoDB.final_queries["node_matching"][e] = lambda counter: f"MATCH (e{counter}) WHERE elementId(e{counter}) = '{e}'"
                identifiers[i] = e
            elif isinstance(e, dict) and not (e['identifier'] in TCMtoDB.final_queries["node_matching"]):
                identifiers[i] = e['identifier']
            elif isinstance(e, list) and not (e[0] in TCMtoDB.final_queries["node_matching"]):
                TCMtoDB.final_queries["node_matching"][e[0]] = lambda counter: f"MATCH (e{counter}:ValueNode {{identifier: '{e[0]}'}})"
                identifiers[i] = e[0]
            
        TCMtoDB.final_queries["edge_creation"].append((*identifiers, relation))
    
    @staticmethod
    def process_final_queries(session):
        TCMtoDB.process_node_creation_query(session)
        TCMtoDB.process_edge_creation_queries(session)
    
    @staticmethod
    def process_creation_query(session):
        element_ids_to_return = []
        query = ""
        for function in TCMtoDB.final_queries["node_creation"]:
            creation_query, identifier = function(TCMtoDB.token_counter)
            query += creation_query+'\n'
            if identifier is not None: element_ids_to_return.append((f"e{TCMtoDB.token_counter}", identifier))
            TCMtoDB.token_counter += 1
        if element_ids_to_return != []: query += "RETURN "+reduce(lambda x, y: x+', '+y, map(lambda e: e[0], element_ids_to_return)) 
        records = session.run(query)#TODO
        for record in records:
            query_results = record
            break

        for i, node_element in enumerate(query_results):
            node_identifier = element_ids_to_return[i][-1]
            match_functions = TCMtoDB.final_queries["node_matching"]
            match_functions[node_identifier] = lambda counter : f"MATCH (e{counter}) WHERE elementId(e{counter}) = '{node_element.element_id}'"
        
        TCMtoDB.token_counter = 0
    
    @staticmethod
    def process_edge_creation_queries(session):
        queries = []
        seen_identifiers = []
        edges_to_create = []
        id_counter = 0
        node_matching = TCMtoDB.final_queries["node_matching"]
        for edge in TCMtoDB.final_queries["edge_creation"]:
            edges_to_create.append(edge)
            mother_id, child_id, relation = edge
            for node_id in [mother_id, child_id]:
                if node_id not in seen_identifiers:
                    seen_identifiers.append(node_id)
                    id_counter += 1
            if id_counter >= TCMtoDB.MAX_MATCH_PER_QUERY - 1:
                queries.append(TCMtoDB.edge_creation_queries(seen_identifiers, edges_to_create))
                id_counter = 0
                seen_identifiers = []
                edges_to_create = []
            

    @staticmethod
    def edge_creation_queries()
            




def main():
    json_path = "arc_json"
    processed_json = []
    counter = 0
    for filename in os.listdir(json_path):
        if filename.endswith(".json"):
            counter += 1
            if counter < 2: continue
            file_path = os.path.join(json_path, filename)
            print(file_path)
            test = TCM(file_path)
            processed_json.append(test)
            break

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