from jsonToTCM import TCM, Node, TYPES
from TSMtoNeo4j import sanitize
from neo4j import GraphDatabase
import os
from functools import reduce
from itertools import compress
from pydoc import locate

class TCMtoDB:
    MAX_MATCH_PER_QUERY = 15
    final_queries = {"node_creation" : [], "node_matching" : {}, "edge_creation" : []}
    path_of_s_nodes_to_create = []
    db_existing_nodes = []

    ################## Expanding db with a tcm ######################
    @staticmethod
    def expand_neo4j_tsm(driver, db, tcm):
        unified_tcm = tcm.unify_types() # needed for type consistency
        TCMtoDB.final_queries = {"node_creation" : [], "node_matching" : {}, "edge_creation" : []}
        TCMtoDB.path_of_s_nodes_to_create = []
        TCMtoDB.db_existing_nodes = []
        with driver.session(database = db) as session:
            TCMtoDB.db_existing_nodes = TCMtoDB.already_existing_nodes(session, unified_tcm)
            TCMtoDB.process_option_value_to_neo4j(session, None, unified_tcm.search_root(unified_tcm.get_edges()), *unified_tcm.get_model())
            TCMtoDB.process_final_queries(session)

    @staticmethod
    def process_option_value_to_neo4j(session, mother_specification_element, current_node, tcm_nodes, tcm_edges):
        if not (isinstance(mother_specification_element, dict) or (current_node.get_identifier() not in TCMtoDB.db_existing_nodes)): return
        if current_node.get_identifier() in TCMtoDB.final_queries["node_matching"]: return
        print(f"Node to add to the graph : {current_node}") 

        db_sn_element = None
        if TCMtoDB.is_possible_query(mother_specification_element):
            db_sn_element = TCMtoDB.query_find_s_option(session, mother_specification_element, current_node)
        
        if db_sn_element is not None:#TODO process type here
            new_msn_element = db_sn_element.element_id
        else: # no need to process type here because the TCM has been unified in the init so each equivalent tcm node has the same type
            if mother_specification_element is None: new_msn_element = TCMtoDB.process_root(session, current_node) #node is root
            else:                                    new_msn_element = TCMtoDB.process_node(session, current_node, mother_specification_element)
        
        TCMtoDB.v_node_creation_query(*current_node.get_v_node_creation_info())
        TCMtoDB.edge_creation_query({'identifier' : current_node.get_identifier()}, new_msn_element, "IS_SPECIFIED_BY")
        
        current_node_children = TCM.find_children(current_node, tcm_edges)
        for current_node_child in current_node_children:
            TCMtoDB.process_option_value_to_neo4j(session, new_msn_element, current_node_child, tcm_nodes, tcm_edges)
            TCMtoDB.edge_creation_query({'identifier': current_node.get_identifier()}, [current_node_child.get_identifier()], "CONTAINS")


    @staticmethod
    def process_root(session, current_node):
        new_s_node_query = TCMtoDB.query_s_root(session)
        if not TCMtoDB.is_result_empty(new_s_node_query):
            return new_s_node_query.single()[0].element_id
        else:
            TCMtoDB.path_of_s_nodes_to_create.append((current_node.get_path(), current_node.get_identifier()))
            TCMtoDB.s_node_creation_query("s"+current_node.get_identifier(), current_node.name(), current_node.get_stype())
            return {"identifier" : "s"+current_node.get_identifier()}

    @staticmethod
    def process_node(session, current_node, mother_specification_element):
        mother_info = TCM.find_node(TCMtoDB.path_of_s_nodes_to_create, lambda n : n[0] == current_node.get_path(), lambda n : n[1])
        if mother_info is not None: identifier = mother_info
        else:
            identifier = "s" + current_node.get_identifier()
            TCMtoDB.path_of_s_nodes_to_create.append((current_node.get_path(), identifier))
            TCMtoDB.s_node_creation_query(identifier, current_node.name(), current_node.get_stype())
            TCMtoDB.edge_creation_query(mother_specification_element, {"identifier" : identifier}, "CONTAINS")

        return {"identifier" : identifier}
    

    ################### Exists node in db ? ######################

    @staticmethod
    def already_existing_nodes(session, tcm):
        query = "RETURN "
        identifiers = set(map(lambda x: x.get_identifier(), tcm.get_nodes()))
        for ident in identifiers:
            query += f"EXISTS{{(:ValueNode {{identifier: '{ident}'}})}}, "
        query = query[:-2]

        query_results = list(session.run(query).single())
        if all(query_results):
            raise Exception("TCM already is in db")
        return list(compress(identifiers, query_results))

    @staticmethod
    def is_result_empty(query_result):
        return query_result.peek() is None

    @staticmethod
    def is_possible_query(db_identifier):
        return not(db_identifier is None or isinstance(db_identifier, dict))
    

    ################## Processing node type ###########################
    #TODO not put into main function, must be tested TODO no more leaf node with null value
    @staticmethod
    def process_type_db(current_node, db_sn_element):
        current_node_valtype = locate(current_node.get_stype())
        db_sn_type = locate(db_sn_element.properties.type)
        if db_sn_element.element_id in TCMtoDB.final_queries["type_change"] and TYPES[TCMtoDB.final_queries["type_change"][db_sn_element.element_id]] > TYPES[db_sn_type]:
            db_sn_type = TCMtoDB.final_queries["type_change"][db_sn_element.element_id]
        if db_sn_type == current_node_valtype: return

        if TYPES[db_sn_type] < TYPES[current_node_valtype]:
            TCMtoDB.final_queries["type_change"][db_sn_element.element_id] = TCMtoDB.update_tsm_types(db_sn_element, current_node, db_sn_type, current_node_valtype)
        else:
            current_node.cast(db_sn_type)
        
    
    @staticmethod
    def update_tsm_types(db_sn_element, current_node, db_sn_type, current_node_valtype):
        update_sn_query = f"""MATCH (sn:SpecificationNode) WHERE elementId(sn) = '{db_sn_element.element_id}'
SET sn.type = '{current_node.get_stype()}'"""
        cast_method = "n.value"
        if db_sn_type == bool:
            cast_method = TCMtoDB.Neo4j_type_cast(cast_method, int)
        if current_node_valtype == float:
            cast_method = TCMtoDB.Neo4j_type_cast(cast_method, float)
        elif current_node_valtype == str:
            cast_method = TCMtoDB.Neo4j_type_cast(cast_method, str)

        update_vn_query = f"""MATCH (vn:ValueNode) WHERE (sn)<-[:IS_SPECIFIED_BY]-(vn)
FOREACH(n IN collect(vn) | SET n.value = {cast_method})"""
        return update_sn_query + update_vn_query
        
    @staticmethod
    def Neo4j_type_cast(obj, cast_into):
        if cast_into == int:
            return f"toInteger({obj})"
        elif cast_into == float:
            return f"toFloat({obj})"
        elif cast_into == str:
            return f"'{obj}'"
    
            

    ################## Queries to find data in db ###################

    @staticmethod
    def query_s_root(session):
        query = f"MATCH (root:SpecificationNode)\nWHERE NOT EXISTS((root)<-[:CONTAINS]-())\nRETURN root"
        return session.run(query)

    @staticmethod
    def query_find_s_option(session, mother_specification_element, current_node):
        query = f"""MATCH (SNM:SpecificationNode)
                    WHERE elementId(SNM) = '{mother_specification_element}'
                    OPTIONAL MATCH (SN:SpecificationNode {{name: '{current_node.name()}'}})<-[:CONTAINS]-(SNM)
                    RETURN SN
                    """
        return session.run(query).single()[0]


    ############### queries to create objects in db ################

    @staticmethod
    def v_node_creation_query(identifier, value):
        TCMtoDB.final_queries["node_creation"].append(lambda _: (f"CREATE (:ValueNode {{value: {sanitize(value)}, identifier: '{identifier}'}})", None))
        TCMtoDB.final_queries["node_matching"][identifier] = (lambda counter: f"MATCH (e{counter}:ValueNode {{identifier: '{identifier}'}})"), ""

    @staticmethod
    def s_node_creation_query(identifier, name, stype):
        TCMtoDB.final_queries["node_creation"].append(lambda counter: (f"CREATE (e{counter}:SpecificationNode {{name: '{name}', type: '{stype}'}})", identifier))

    @staticmethod
    def edge_creation_query(ms_element, cs_element, relation):
        identifiers = [None, None]
        for i, e in enumerate([ms_element, cs_element]):
            if isinstance(e, str):
                if not (e in TCMtoDB.final_queries["node_matching"]):
                    TCMtoDB.final_queries["node_matching"][e] = (lambda counter: f"MATCH (e{counter}) WHERE elementId(e{counter}) = "), f"'{e}'"
                identifiers[i] = e
            elif isinstance(e, dict):
                identifiers[i] = e['identifier']
            elif isinstance(e, list):
                if not (e[0] in TCMtoDB.final_queries["node_matching"]):
                    TCMtoDB.final_queries["node_matching"][e[0]] = (lambda counter: f"MATCH (e{counter}:ValueNode {{identifier: "), f"'{e[0]}'}})"
                identifiers[i] = e[0]
            
        TCMtoDB.final_queries["edge_creation"].append((*identifiers, relation))
    
    @staticmethod
    def process_final_queries(session):
        TCMtoDB.process_node_creation_query(session)
        TCMtoDB.process_edge_creation_queries(session)
    
    @staticmethod
    def process_node_creation_query(session):
        element_ids_to_return = []
        query = ""

        for i, function in enumerate(TCMtoDB.final_queries["node_creation"]):
            creation_query, identifier = function(i)
            query += creation_query+'\n'
            if identifier is not None: element_ids_to_return.append((f"e{i}", identifier))
        if element_ids_to_return != []: 
            query += "RETURN "+reduce(lambda x, y: x+', '+y, map(lambda e: e[0], element_ids_to_return))
        else:
            print(query)
            session.run(query)
            return
        
        print(query)
        #return
        query_results = session.run(query).single()

        for i, node_element in enumerate(query_results):
            node_identifier = element_ids_to_return[i][1]
            TCMtoDB.final_queries["node_matching"][node_identifier] = (lambda counter : f"MATCH (e{counter}) WHERE elementId(e{counter}) = "), f"'{node_element.element_id}'"

    
    @staticmethod
    def process_edge_creation_queries(session):
        queries = []
        seen_identifiers = []
        edges_to_create = []
        id_counter = 0
        for edge in TCMtoDB.final_queries["edge_creation"]:
            edges_to_create.append(edge)
            mother_id, child_id, relation = edge
            for node_id in [mother_id, child_id]:
                if node_id not in seen_identifiers:
                    seen_identifiers.append(node_id)
                    id_counter += 1
            if id_counter >= TCMtoDB.MAX_MATCH_PER_QUERY - 1:
                queries.append(TCMtoDB.final_edge_creation_queries(seen_identifiers, edges_to_create))
                id_counter = 0
                seen_identifiers = []
                edges_to_create = []
        if edges_to_create != []:
            queries.append(TCMtoDB.final_edge_creation_queries(seen_identifiers, edges_to_create))
        
        queries = f"CALL apoc.cypher.runMany(\n  \"{reduce(lambda x, y: x + ';\n  '+y, queries)}\"\n,{{}});"
        print(queries)
        #return

        session.run(queries)
        

    @staticmethod
    def final_edge_creation_queries(seen_identifiers, edges_to_create):
        node_matching = TCMtoDB.final_queries["node_matching"]
        query = ""
        id_token = dict(zip(seen_identifiers, [f"{i}" for i in range(len(seen_identifiers))]))
        for k, v in id_token.items():
            query += node_matching[k][0](v) + node_matching[k][1] +'\n  '
        
        for (mother_id, child_id, relation) in edges_to_create:
            query += f"CREATE (e{id_token[mother_id]})-[:{relation}]->(e{id_token[child_id]})\n  "
        return query[:-3]



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
            test = TCM(file_path, 'mahyco')
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
            OPTIONAL MATCH (SN:SpecificationNode {{name: "name"}})<-[:CONTAINS]-(SNM)
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