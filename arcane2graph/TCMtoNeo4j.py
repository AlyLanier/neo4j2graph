from jsonToTCM import TCM
from TCMtoTSM import TSM
from TSMtoNeo4j import STARTING_CHAR, sanitize
from neo4j import GraphDatabase

def v_node_creation_query_with_cast(identifier, value):
    return f"CREATE ({STARTING_CHAR}{identifier}:ValueNode {{value: {sanitize(TSM.value_cast(value))}, identifier: {sanitize(identifier)}}})"

def expand_neo4j_tsm(driver, tcm):
    tcm_root = tcm.search_root()
    process_option_value_to_neo4j(driver, tcm_root, *tcm.get_model())

def process_option_value_to_neo4j(driver, current_node, tcm_nodes, tcm_edges):
    if exists_node(lambda x : query_node(*x), driver, "ValueNode", {"identifier": current_node.get_identifier()}): return

    new_v_node_query = v_node_creation_query_with_cast(current_node.get_identifier(), current_node.val())
    tcm_mother_node = TSM.find_node_from_edge(tcm_edges, current_node, from_source = False)
    
    tsm_s_node_element, tsm_mother_s_node_element = None, None
    query_result = query_child_specification_option(driver, tcm_mother_node)[0]
    if query_result != []: tsm_s_node_element, tsm_mother_s_node_element = query_result[0]
    if tsm_s_node_element is not None:
        new_s_edge_query = f"""MATCH"""

    
        
    

    return

def exists_node(query_method, *args):
    return query_method(args) != []

def query_node(driver, node_type, properties):
    query = f"MATCH (NT:{node_type}"
    if properties:
        query += " {"
        for k, v in properties.items():
            query += f"{k}: '{v}',"
        query = query[:-1]+"}"
    query += ")\nRETURN NT"
    #print(query)
    return driver.execute_query(query)[0]

def query_child_specification_option(driver, mother_node):
    query = f"""MATCH (SNM:SpecificationNode)<-[:IS_SPECIFIED_BY]-(:ValueNode {{identifier: '{mother_node.get_identifier()}'}})
                OPTIONAL MATCH (SN:SpecificationNode {{name: '{mother_node.name()}'}})<-[:CONTAINS]-(SNM)
                RETURN SNM, SN
                """
    return driver.execute_query(query)[0]

def process_option_value():
    v_nodes = self.get_value_nodes()
    for v_node in v_nodes:
        if v_node.get_identifier() == current_node.get_identifier(): return

    new_v_node = TSM.create_v_node(current_node.get_identifier(), TSM.value_cast(current_node.val()))
    self.add_value_node(new_v_node)

    tsm_mother_v_node, tsm_mother_s_node, tsm_s_node = None, None, None
    tcm_mother_node = TSM.find_node_from_edge(tcm_edges, current_node, from_source = False)
    if tcm_mother_node   is not None: tsm_mother_v_node = TSM.find_node_from_hash(v_nodes, tcm_mother_node)
    if tsm_mother_v_node is not None: tsm_mother_s_node = self.spec(tsm_mother_v_node)
    if tsm_mother_s_node is not None: tsm_s_node = TSM.find_node_from_edge(self.get_containment_edges(), tsm_mother_s_node, from_source = True)

        
    if tsm_s_node is not None and tsm_s_node.name() == current_node.name():
        TSM.process_type(current_node, tsm_s_node)
        self.add_specification_edge(new_v_node, tsm_s_node)
    else:
        new_s_node = TSM.create_s_node(current_node.name(), type(TSM.value_cast(current_node.val())), current_node.get_path())
        self.add_specification_edge(new_v_node, new_s_node)
        self.add_specification_node(new_s_node)
        if tsm_mother_s_node is not None: self.add_containment_edge(tsm_mother_s_node, new_s_node)
    
    current_node_children = TSM.find_children(current_node, tcm_edges)
    for current_node_child in current_node_children:
        self.process_option_value(current_node_child, tcm_nodes, tcm_edges)
        tsm_v_node_child = TSM.find_node_from_hash(v_nodes, current_node_child)
        self.add_containment_edge(new_v_node, tsm_v_node_child)




def main():

    # URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()

        # build graph here
        query = f"""MATCH (SNM:SpecificationNode)<-[:IS_SPECIFIED_BY]-(:ValueNode {{identifier: "a1566f82ecbad4341fdb52a472e4c5b1"}})
                OPTIONAL MATCH (SN:SpecificationNode {{name: "nme"}})<-[:CONTAINS]-(SNM)
                RETURN SNM, SN
                """
        test = driver.execute_query(query)
        print(test[0])
        print(test[0][0])
        print(test[0][0][0])
        print(test[0][0][0].element_id)
        print(test[0][0][1])

        

if __name__ == '__main__':
    main()