from TSMtoNeo4j import sanitize
from neo4j import GraphDatabase

class GraphFunctions:
    @staticmethod
    def stringify_ids(list_node_ids):
        return str([node['identifier'] for node in list_node_ids if isinstance(node, dict)]), str([node for node in list_node_ids if isinstance(node, str)])


    ######### Option Coverage ##############

    @staticmethod
    def option_coverage(session, s_node_identifying_component):
        node_query = GraphFunctions.node_from_identification_query(s_node_identifying_component)
        final_query = node_query+'\n'+"""OPTIONAL MATCH (sn)-[:CONTAINS*]->(n:SpecificationNode)<-[:IS_SPECIFIED_BY]-(vn:ValueNode) 
WHERE (sn.type IN ['list', 'dict']) AND NOT (n.type IN ['list', 'dict'])
OPTIONAL MATCH (sn)<-[:IS_SPECIFIED_BY]-(v2n:ValueNode)
WHERE NOT (sn.type IN ['list', 'dict'])
return
CASE vn
    WHEN IS NULL THEN v2n
    ELSE vn
END AS result"""
        return session.run(final_query)

        
    @staticmethod
    def node_from_identification_query(s_node_identifying_component):
        match type(s_node_identifying_component).__name__:
            #'4:ff0859ac-496c-403c-b1cb-8a0bb1eafbc9:1543'
            case 'str':
                node_query = f"MATCH (sn:SpecificationNode) WHERE elementId(sn) = '{s_node_identifying_component}'"
            # {'name': 'final_time', 'type': 'float'}
            case 'dict':
                node_query = "MATCH (sn:SpecificationNode {"
                for k, v in s_node_identifying_component.items():
                    node_query += f"{k}: {sanitize(v)}, "
                node_query = node_query[:-2] + '})'
        return node_query
    

    ############# Combinatorial Coverage creation ################

    # 'ALL' | list
    @staticmethod
    def combinatorial_coverage(session, leaf_nodes_to_consider = "ALL", with_auto_reference_on_lists = False):
        if leaf_nodes_to_consider == "ALL": return GraphFunctions.i_want_to_fry_my_pc(session, with_auto_reference_on_lists)
        
        match_on_properties, match_on_element_id = GraphFunctions.stringify_ids(leaf_nodes_to_consider)
        additional_conditions = f" AND (vn.identifier IN {match_on_properties} OR elementId(vn) IN {match_on_element_id})"
        query = GraphFunctions.combinatorial_coverage_base_query(additional_conditions, with_auto_reference_on_lists)
        
        return session.run(query)
    
    @staticmethod
    def i_want_to_fry_my_pc(session, with_auto_reference_on_lists):
        query = GraphFunctions.combinatorial_coverage_base_query("", with_auto_reference_on_lists)
        return session.run(query)

    @staticmethod    
    def combinatorial_coverage_base_query(additional_conditions, with_auto_reference_on_lists):
        if with_auto_reference_on_lists: leaf_matching = "MATCH (root)-[:CONTAINS*]->(vn:ValueNode) WHERE NOT (vn)-[:CONTAINS]->()"
        else:                            leaf_matching = "MATCH (vn:ValueNode) WHERE (root)-[:CONTAINS*]->(vn) AND NOT (vn)-[:CONTAINS]->()"
        return f"""MATCH (root:ValueNode) WHERE NOT (root)<--()
{leaf_matching}{additional_conditions}
WITH apoc.coll.sortNodes(collect(vn), 'value') AS coverage
UNWIND apoc.coll.combinations(coverage, 2) as node_couple
WITH node_couple, count(node_couple) AS weight
CALL apoc.coll.elements(node_couple) YIELD _1n, _2n
CALL apoc.create.vRelationship(_1n, 'COMBINED', {{weight: weight}}, _2n) YIELD rel
RETURN _1n, rel, _2n
ORDER BY _1n.value, _2n.value"""
    

    ################ TSM Slicing ##############################
    
    @staticmethod
    def TSM_Slicing(session, nodes_to_find_on_single_root, return_all_subgraphs = False):
        return session.run(*GraphFunctions.stringify_ids(nodes_to_find_on_single_root), return_all_subgraphs)

    @staticmethod
    def TSM_Slicing_base_query(str_leaf_element_ids, str_leaf_property_ids, return_all_subgraphs):
        root_condition = "" if return_all_subgraphs else " WHERE NOT (root) <-- ()"
        return f"""WITH [{str_leaf_element_ids[1:-1]}] AS leafEID, [{str_leaf_property_ids[1:-1]}] AS leafPID
WITH leafEID, leafPID, size(leafEID) + size(leafPID) AS len

MATCH (root:ValueNode){root_condition}
MATCH (root)-[:CONTAINS*]->(leaf:ValueNode) WHERE NOT (leaf)-[:CONTAINS]->() AND (leaf.identifier IN leafPID OR elementId(leaf) IN leafEID)
WITH collect(DISTINCT leaf) AS leaves, root, len

MATCH p = (root)-[*]->(n) WHERE size(leaves) = len AND EXISTS{{ MATCH t = (root)-[*]->(m) WHERE t <> p and m = n }}
WITH p, root, nodes(p) AS Nodes, relationships(p) AS Relations

MATCH (o:ValueNode) WHERE o in Nodes
MATCH (q:SpecificationNode) WHERE q in Nodes
MATCH pr = ()-[r:CONTAINS]->() WHERE r IN Relations
MATCH ps = ()-[s:IS_SPECIFIED_BY]->() WHERE s IN Relations
WITH collect(DISTINCT o) AS Vv, collect(DISTINCT q) AS Vs, collect(DISTINCT pr) AS Ec, collect(DISTINCT ps) AS Es, root
RETURN Vv, Vs, Ec, Es"""
    



def main():
    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")
    DB_NAME = AUTH[0]

    nodes_to_consider = [{"identifier" : "5c9573292a0784c352a1c1d1cfac4242"},
                        {"identifier" : "451c9c90e9fb8dde88ebc62a989144a8"},
                        "4:ff0859ac-496c-403c-b1cb-8a0bb1eafbc9:236",
                        "4:ff0859ac-496c-403c-b1cb-8a0bb1eafbc9:276", 
                        "4:ff0859ac-496c-403c-b1cb-8a0bb1eafbc9:285", 
                        "4:ff0859ac-496c-403c-b1cb-8a0bb1eafbc9:232", 
                        "4:ff0859ac-496c-403c-b1cb-8a0bb1eafbc9:229", 
                        "4:ff0859ac-496c-403c-b1cb-8a0bb1eafbc9:270", 
                        "4:ff0859ac-496c-403c-b1cb-8a0bb1eafbc9:245"]

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()

        with driver.session(database = DB_NAME) as session:
            #oc = GraphFunctions.option_coverage(session, '4:ff0859ac-496c-403c-b1cb-8a0bb1eafbc9:1535')
            #cc = GraphFunctions.combinatorial_coverage(session, nodes_to_consider)
            #slicing = GraphFunctions.TSM_Slicing(session, nodes_to_consider)
            pass

if __name__ == '__main__':
    main()