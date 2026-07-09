from jsonToTCM import TCM, TYPES, Node, Edge
from TSMtoNeo4j import sanitize, TSM_creation_query, STARTING_CHAR
from TCMtoTSM import TSM
from neo4j import GraphDatabase
import os, sys
from functools import reduce
from pydoc import locate

class TCMtoDB:
    @staticmethod
    def setup_variables(tcm):
        tcm.unify_types() # needed for type consistency
        TCMtoDB.final_queries = {"node_matching" : {}, "node_creation" : [], "edge_creation" : [], "type_change" : {}, "annotations": tcm.get_annotations()}
        TCMtoDB.nodes_created = []
        TCMtoDB.db_specification_nodes = {}
        TCMtoDB.path_of_s_nodes_to_create = []
        TCMtoDB.db_value_nodes = {}
        TCMtoDB.db_optional_node = None
        print(tcm.get_annotations())


    ################## Expanding db with a tcm ######################
    @staticmethod
    def expand_neo4j_tsm(driver, db: str, tcm: TCM)->None:
        TCMtoDB.setup_variables(tcm)
        with driver.session(database = db) as session:
            TCMtoDB.get_db_nodes_start(session, tcm)
            root = tcm.search_root(tcm.get_edges())
            if root.get_identifier() in TCMtoDB.db_value_nodes:
                session.run(TCMtoDB.annotation_tcm_in_db_query(root.get_identifier()))
                return

            TCMtoDB.process_option_value_to_neo4j(session, None, root, *tcm.get_model())
            TCMtoDB.process_final_queries(session)

    @staticmethod
    def process_option_value_to_neo4j(session, mother_specification_element: str|list|None, current_node: Node, tcm_nodes: list[Node], tcm_edges: list[Edge])->None:
        if current_node.get_identifier() in TCMtoDB.db_value_nodes: return
        if current_node.get_identifier() in TCMtoDB.nodes_created: return
        print(f"Node to add to the graph : {current_node}")

        db_sn_element = None
        if TCMtoDB.is_possible_query(mother_specification_element):
            db_sn_element = TCMtoDB.find_s_option(mother_specification_element, current_node)

        
        if db_sn_element is not None:
            new_msn_element = db_sn_element.element_id
            TCMtoDB.process_type_db(current_node, db_sn_element)
        else: # no need to process type here because the TCM has been unified in the init so each equivalent tcm node has the same type
            if mother_specification_element is None: new_msn_element = TCMtoDB.process_root(current_node) #node is root
            else:                                    new_msn_element = TCMtoDB.process_node(current_node, mother_specification_element)
        
        TCMtoDB.node_creation(*current_node.get_v_node_creation_info())
        TCMtoDB.edge_creation([STARTING_CHAR+current_node.get_identifier()], new_msn_element, "IS_SPECIFIED_BY")
        
        edges_from_current_node = TCM.find_edges(tcm_edges, from_node=current_node)
        for edge_to_child in edges_from_current_node:
            child_id = edge_to_child.target().get_identifier()
            if child_id in TCMtoDB.db_value_nodes: child_ref_id = TCMtoDB.db_value_nodes[child_id]
            else:
                TCMtoDB.process_option_value_to_neo4j(session, new_msn_element, edge_to_child.target(), tcm_nodes, tcm_edges)
                child_ref_id = [STARTING_CHAR+child_id]
            TCMtoDB.edge_creation([STARTING_CHAR+current_node.get_identifier()], child_ref_id, "CONTAINS", edge_to_child.get_index())


    @staticmethod
    def process_root(current_node: Node)->list[str]:
        if TCMtoDB.db_specification_nodes != {}:
            return TCMtoDB.get_db_s_root().element_id
        else:
            identifier = "s" + current_node.get_identifier()
            TCMtoDB.path_of_s_nodes_to_create.append((current_node.get_path(), identifier))
            TCMtoDB.node_creation(identifier, current_node.name(), current_node.get_stype())
            return [identifier]

    @staticmethod
    def process_node(current_node: Node, mother_specification_element: str|list)->list[str]:
        mother_info = TCM.find_node(TCMtoDB.path_of_s_nodes_to_create, lambda n : n[0] == current_node.get_path(), lambda n : n[1])
        if mother_info is not None: identifier = mother_info
        else:
            identifier = "s" + current_node.get_identifier()
            TCMtoDB.path_of_s_nodes_to_create.append((current_node.get_path(), identifier))
            TCMtoDB.node_creation(identifier, current_node.name(), current_node.get_stype())
            TCMtoDB.edge_creation(mother_specification_element, [identifier], "CONTAINS")

        return [identifier]
    

    ################### Exists node in db ? ######################
    @staticmethod
    def get_db_nodes_start(session, tcm:TCM)->None:
        TCMtoDB.db_specification_nodes = TCMtoDB.get_db_specification_nodes(session)
        TCMtoDB.db_value_nodes = TCMtoDB.already_existing_value_nodes(session, tcm)
        TCMtoDB.db_optional_node = TCMtoDB.get_db_optional_annotation_node(session)

    @staticmethod
    def already_existing_value_nodes(session, tcm:TCM)-> dict[str, str]:
        res = {}
        identifiers = list(set(map(lambda x: x.get_identifier(), tcm.get_nodes())))
        query = f"""WITH [{str(identifiers)[1:-1]}] AS identifiers UNWIND identifiers AS ident
OPTIONAL MATCH (v:ValueNode {{identifier: ident}})
RETURN ident, elementId(v) AS e_id"""
        query_results = session.run(query)
        for result in query_results:
            ident, element_id = result['ident'], result['e_id']
            if element_id is not None:
                res[ident] = element_id

        return res

    @staticmethod
    def get_db_specification_nodes(session)->dict:
        query = """MATCH (s:SpecificationNode)
OPTIONAL MATCH (s)-[:CONTAINS]->(a)
RETURN s, collect(elementId(a))"""
        res = {}
        results = session.run(query)
        for node, child_list in results:
            if child_list != []:
                res[node] = list(map(lambda s: s[39:], child_list))
            else:
                res[node] = []
        return res

    @staticmethod
    def get_db_optional_annotation_node(session):
        query = "MATCH (a:AnnotationNode {annotation: 'This value is optional'})-[:ANNOTATES]->(s) RETURN a, collect(s)"
        return session.run(query).single()

    @staticmethod
    def is_result_empty(query_result)->bool:
        return query_result.peek() is None

    @staticmethod
    def is_possible_query(db_identifier: str|list|None)->bool:
        return db_identifier is not None and not isinstance(db_identifier, list)
    
    @staticmethod
    def get_db_s_root():
        for node in TCMtoDB.db_specification_nodes.keys():
            if node["name"] == "root":
                return node
        raise Exception("[CRITICAL ERROR] no root node found in the db")
    

    ################## Processing node type ###########################

    @staticmethod
    def process_type_db(current_node: Node, db_sn_element)->None:
        current_node_valtype = locate(current_node.get_stype())
        db_sn_type = locate(db_sn_element['type'])
        if db_sn_element.element_id in TCMtoDB.final_queries["type_change"] and TYPES[TCMtoDB.final_queries["type_change"][db_sn_element.element_id]] > TYPES[db_sn_type]:
            db_sn_type = TCMtoDB.final_queries["type_change"][db_sn_element.element_id]
        if db_sn_type == current_node_valtype: return
        if TYPES[db_sn_type] < TYPES[current_node_valtype]:
            TCMtoDB.final_queries["type_change"][db_sn_element.element_id] = TCMtoDB.update_tsm_types_query(db_sn_element, current_node, db_sn_type, current_node_valtype)
        else:
            current_node.cast(db_sn_type)
        
    @staticmethod
    def update_tsm_types_query(db_sn_element, current_node: Node, db_sn_type, current_node_valtype: type)->str:
        update_sn_query = f"""MATCH (sn:SpecificationNode) WHERE elementId(sn) = '{db_sn_element.element_id}'
SET sn.type = '{current_node.get_stype()}' WITH sn\n"""
        cast_method = "n.value"
        if db_sn_type == bool:
            cast_method = TCMtoDB.Neo4j_type_cast(cast_method, int)
        if current_node_valtype == float:
            cast_method = TCMtoDB.Neo4j_type_cast(cast_method, float)
        elif current_node_valtype == str:
            cast_method = TCMtoDB.Neo4j_type_cast(cast_method, str)

        update_vn_query = f"""MATCH (vn:ValueNode) WHERE (sn)<-[:IS_SPECIFIED_BY]-(vn) WITH collect(vn) as value_nodes
FOREACH(n IN value_nodes | SET n.value = {cast_method})"""
        return update_sn_query + update_vn_query
        
    @staticmethod
    def Neo4j_type_cast(obj: str, cast_into: type)->str:
        if cast_into == int:
            return f"toInteger({obj})"
        elif cast_into == float:
            return f"toFloat({obj})"
        elif cast_into == str:
            return f"toString({obj})"
    
    @staticmethod
    def find_s_option(mother_specification_element: str, current_node: Node):
        for k, v in TCMtoDB.db_specification_nodes.items():
            if k.element_id == mother_specification_element:
                for child_k in TCMtoDB.db_specification_nodes.keys():
                    if child_k["name"] == current_node.name() and child_k.element_id[39:] in v:
                        return child_k
        return None
        
        
    ############### queries to create objects in db ################

    @staticmethod
    def node_creation(*args)->None:
        TCMtoDB.final_queries["node_creation"].append(tuple(args))
        TCMtoDB.nodes_created.append(args[0])

    @staticmethod
    def edge_creation(ms_element: str|list|dict, cs_element: str|list, relation: str, relation_index: list[int] = None)->None:
        identifiers = [None, None]
        for i, e in enumerate([ms_element, cs_element]):
            if isinstance(e, str): #db node
                if e in TCMtoDB.final_queries["node_matching"]:
                    identifiers[i] = TCMtoDB.final_queries["node_matching"][e]
                else:
                    identifiers[i] = TCMtoDB.final_queries["node_matching"][e] = f"e{len(TCMtoDB.final_queries["node_matching"])}"
            elif isinstance(e, list): #new node
                identifiers[i] = e[0]
            
        TCMtoDB.final_queries["edge_creation"].append((*identifiers, relation, relation_index))
    
    
    ################ processing queries ############################
    
    @staticmethod
    def process_final_queries(session)->None:
        query = ""
        if TCMtoDB.final_queries["node_matching"] != {}:    query += TCMtoDB.node_matching_query()+"\n"
        if TCMtoDB.final_queries["node_creation"] != []:    query += TCMtoDB.node_creation_query()+"\n"
        if TCMtoDB.final_queries["type_change"] != {}:      query += TCMtoDB.type_change_query()+"\n"
        if TCMtoDB.final_queries["edge_creation"] != []:    query += TCMtoDB.edge_creation_query()+"\n"
        query += TCMtoDB.annotation_query()
        print(query)
        session.run(query)
    
    @staticmethod
    def node_matching_query()->str:
        queries = []
        for db_node_eid, ref_id in TCMtoDB.final_queries["node_matching"].items():
            queries.append(f"MATCH ({ref_id}) WHERE elementId({ref_id}) = '{db_node_eid}'")
        
        return reduce(lambda x, y: x+"\n"+y, queries)

    @staticmethod
    def node_creation_query()->str:
        queries = []
        for n_tuple in TCMtoDB.final_queries["node_creation"]:
            match len(n_tuple):
                case 2:
                    identifier, value = n_tuple
                    queries.append(f"CREATE ({STARTING_CHAR}{identifier}:ValueNode {{identifier: '{identifier}', value: {sanitize(value)}}})")
                case 3:
                    identifier, name, stype = n_tuple
                    queries.append(f"CREATE ({identifier}:SpecificationNode {{name: '{name}', type: '{stype}'}})")
                case _:
                    raise Exception("parameters for node creation not valid")

        return reduce(lambda x, y: x+"\n"+y, queries)

    @staticmethod
    def type_change_query()->str:
        return reduce(lambda x, y: x +"\n"+y, TCMtoDB.final_queries["type_change"].values())
    
    @staticmethod
    def edge_creation_query()->str:
        queries = []
        for edge in TCMtoDB.final_queries["edge_creation"]:
            mother_id, child_id, relation, relation_index = edge
            index_str = f" {{index: {relation_index}}}" if relation_index is not None else "" 
            queries.append(f"CREATE ({mother_id})-[:{relation}{index_str}]->({child_id})")
        
        return reduce(lambda x, y: x+"\n"+y, queries)
        
    @staticmethod
    def annotation_query():
        query = ""
        for key, annotation in TCMtoDB.final_queries["annotations"].items():
            match key:
                case "filenames":
                    root_id, filename_list = list(annotation.items())[0]
                    query += f"CREATE (:FileNode:AnnotationNode {{filenames: {filename_list}}})-[:ANNOTATES]->({STARTING_CHAR}{root_id}) \n"
                case "optional_nodes":
                    for spec_node_id, _ in annotation.items():
                        query += optional_node_annotation_creation_query(spec_node_id) + "\n"
                case "nonexistent_nodes":
                    for parent_id, name in annotation.items():
                        for option_name in name:
                            query += nonexistant_node_creation_query(parent_id, option_name) + '\n'
    
    @staticmethod
    def annotation_tcm_in_db_query(root_identifier):
        file_name = TCMtoDB.final_queries["annotations"]["filenames"][root_identifier][0]
        return f"""MATCH (f:FileNode) WHERE (f)-[:ANNOTATES]->(:ValueNode {{identifier: '{root_identifier}'}})
SET f.filenames = f.filenames + '{file_name}'"""



def main():

    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")
    DB_NAME = AUTH[0]
    json_path = "arc_json"

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        with driver.session(database=DB_NAME) as session:
            print(TCMtoDB.get_db_optional_annotation_node(session))
    return

    
    files_to_consider = ['Mahyco_0x5b67d7517e00.json', 'Mahyco_0x5aa3a2f6d0f0.json', 'Mahyco_0x5be0ee5cb7b0.json']
    processed_json = []
    for filename in files_to_consider:
        file_path = os.path.join(json_path, filename)
        print(file_path)
        processed_json.append(TCM(file_path, 'mahyco'))
    tsm = TSM(processed_json[:-1])
    tsm_str = TSM_creation_query(tsm)
    

    

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        driver.execute_query("MATCH (p)\nDETACH DELETE p")# remove current graph
        driver.execute_query(tsm_str)# build graph here

        TCMtoDB.expand_neo4j_tsm(driver, DB_NAME, processed_json[-1])
        
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

        

if __name__ == "__main__":
    args = sys.argv
    if len(args) == 1: main()
    elif args[1] == 'test':
        import test_.test_TCMtoNeo4j as test
        test.validate_db_from_tcm()