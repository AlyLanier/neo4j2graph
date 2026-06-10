from TSMtoNeo4j import sanitize
from neo4j import GraphDatabase

class GraphFunctions:

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
    def combinatorial_coverage(session, leaf_nodes_to_consider = "ALL"):
        if leaf_nodes_to_consider == "ALL": return GraphFunctions.i_want_to_fry_my_pc(session)
        
        match_on_properties = str([node['identifier'] for node in leaf_nodes_to_consider if isinstance(node, dict)])
        match_on_element_id = str([node for node in leaf_nodes_to_consider if isinstance(node, str)])
        
        additional_conditions = f" AND (vn.identifier IN {match_on_properties} OR elementId(vn) IN {match_on_element_id})"
        query = GraphFunctions.combinatorial_coverage_base_query(additional_conditions)
        
        return session.run(query)
    
    @staticmethod
    def i_want_to_fry_my_pc(session):
        query = GraphFunctions.combinatorial_coverage_base_query("")
        return session.run(query)

    @staticmethod    
    def combinatorial_coverage_base_query(additional_conditions):
        #TODO ask Dorian MATCH (vn:ValueNode) WHERE (root)-[:CONTAINS*]->(vn) AND NOT (vn)-[:CONTAINS]->()
        return f"""MATCH (root:ValueNode) WHERE NOT (root)<--()
MATCH (root)-[:CONTAINS*]->(vn:ValueNode) WHERE NOT (vn)-[:CONTAINS]->(){additional_conditions}
WITH apoc.coll.sortNodes(collect(vn), 'value') AS coverage
UNWIND apoc.coll.combinations(coverage, 2) as node_couple
WITH node_couple, count(node_couple) AS weight
CALL apoc.coll.elements(node_couple) YIELD _1n, _2n
CALL apoc.create.vRelationship(_1n, 'COMBINED', {{weight: weight}}, _2n) YIELD rel
RETURN _1n, rel, _2n, weight
ORDER BY _1n.value, _2n.value"""
    



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
            cc = GraphFunctions.combinatorial_coverage(session, nodes_to_consider)

if __name__ == '__main__':
    main()