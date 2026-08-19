from panoramix.tcm_to_tsm import TSM, VNode, SNode, Edge
from panoramix.json_to_tcm import *
from pydoc import locate
from panoramix.tsm_to_neo4j import sanitize
from neo4j import GraphDatabase
from panoramix.mean_functions import *

class GraphFunctions:

    @staticmethod
    def stringify_ids(list_node_ids):
        return str([node['identifier'] for node in list_node_ids if isinstance(node, dict)]), str([node for node in list_node_ids if isinstance(node, str)])


    ########## Get TSM from DB ################

    @staticmethod
    def get_TSM_query():
        return """MATCH (o:ValueNode) WITH collect(o) AS vn
MATCH (q:SpecificationNode) WHERE (q)<-[:IS_SPECIFIED_BY]-() WITH vn, collect(q) AS sn
MATCH pr = ()-[:CONTAINS]->(end) WHERE end:ValueNode OR (end)<-[:IS_SPECIFIED_BY]-() WITH vn, sn, collect(reduce(output = [], n IN nodes(pr) | output + n)) AS ce
MATCH ps = ()-[:IS_SPECIFIED_BY]->() WITH vn, sn, ce, collect(reduce(output = [], n IN nodes(ps) | output + n)) as se
RETURN vn, sn, ce, se
"""


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
        return f"""MATCH (root:ValueNode) WHERE NOT (root)<-[:CONTAINS]-()
{leaf_matching}{additional_conditions}
WITH collect(vn) AS coverage, root AS _
UNWIND apoc.coll.combinations(coverage, 2) as node_couple
WITH node_couple, count(node_couple) AS weight
CALL apoc.coll.elements(node_couple) YIELD _1n, _2n
CALL apoc.create.vRelationship(_1n, 'COMBINED', {{weight: weight}}, _2n) YIELD rel
RETURN _1n, rel, _2n"""
    
    @staticmethod
    def combinatorial_coverage_from_slicing_query(additional_conditions, with_auto_reference_on_lists):
        if with_auto_reference_on_lists: leaf_matching = "MATCH (root)-[:CONTAINS*]->(vn:ValueNode) WHERE NOT (vn)-[:CONTAINS]->()"
        else:                            leaf_matching = "MATCH (vn:ValueNode) WHERE (root)-[:CONTAINS*]->(vn) AND NOT (vn)-[:CONTAINS]->()"
        return f"""{leaf_matching}{additional_conditions}
WITH collect(vn) AS coverage, root AS _
UNWIND apoc.coll.combinations(coverage, 2) as node_couple
WITH node_couple, count(node_couple) AS weight
CALL apoc.coll.elements(node_couple) YIELD _1n, _2n
CALL apoc.create.vRelationship(_1n, 'COMBINED', {{weight: weight}}, _2n) YIELD rel
RETURN _1n, rel, _2n"""

    

    ################ TSM Slicing ##############################
    
    @staticmethod
    def TSM_Slicing(session, nodes_to_find_on_single_root, return_all_subgraphs = False):
        return session.run(*GraphFunctions.stringify_ids(nodes_to_find_on_single_root), return_all_subgraphs)

    @staticmethod
    def TSM_Slicing_base_query(str_leaf_element_ids, str_leaf_property_ids, return_all_subgraphs):
        root_condition = "" if return_all_subgraphs else " WHERE NOT (root) <-[:CONTAINS]- ()"
        return f"""WITH [{str_leaf_element_ids[1:-1]}] AS leafEID, [{str_leaf_property_ids[1:-1]}] AS leafPID
WITH leafEID, leafPID, size(leafEID) + size(leafPID) AS len

MATCH (root:ValueNode){root_condition}
MATCH (root)-[:CONTAINS*]->(leaf:ValueNode) WHERE NOT (leaf)-[:CONTAINS]->() AND (leaf.identifier IN leafPID OR elementId(leaf) IN leafEID)
WITH size(collect(DISTINCT leaf)) AS sizes, root, len

MATCH p = (root)-[*]->(n) WHERE sizes = len AND (EXISTS{{ MATCH t = (root)-[*]->(n) WHERE t <> p }})
WITH p, root, nodes(p) AS Nodes, relationships(p) AS Relations

MATCH (o:ValueNode) WHERE o in Nodes
MATCH (q:SpecificationNode) WHERE q in Nodes
MATCH pr = ()-[r:CONTAINS]->() WHERE r IN Relations
MATCH ps = ()-[s:IS_SPECIFIED_BY]->() WHERE s IN Relations
WITH collect(DISTINCT o) AS Vv, collect(DISTINCT q) AS Vs, collect(DISTINCT pr) AS Ec, collect(DISTINCT ps) AS Es, root
RETURN Vv, Vs, Ec, Es"""
    
    @staticmethod
    def TSM_Slicing_for_cc_query(str_leaf_element_ids, str_leaf_property_ids, return_all_subgraphs):
        root_condition = "" if return_all_subgraphs else " WHERE NOT (root) <-[:CONTAINS]- ()"
        return f"""WITH [{str_leaf_element_ids[1:-1]}] AS leafEID, [{str_leaf_property_ids[1:-1]}] AS leafPID
WITH leafEID, leafPID, size(leafEID) + size(leafPID) AS len

MATCH (root:ValueNode){root_condition}
MATCH (root)-[:CONTAINS*]->(leaf:ValueNode) WHERE NOT (leaf)-[:CONTAINS]->() AND (leaf.identifier IN leafPID OR elementId(leaf) IN leafEID)
WITH size(collect(DISTINCT leaf)) AS sizes, root, len

MATCH p = (root)-[*]->(n) WHERE sizes = len AND (EXISTS{{ MATCH t = (root)-[*]->(n) WHERE t <> p }})
WITH root"""
    

    ################ Slicing --> Combinatorial Coverage ###########

    @staticmethod
    def TSM_Slicing_and_Combinatorial_Coverage(session, nodes_on_slice, nodes_for_combinatorial_coverage, return_all_subgraphs = False, with_self_reference = False):
        match_on_properties, match_on_element_id = GraphFunctions.stringify_ids(nodes_for_combinatorial_coverage)
        if nodes_for_combinatorial_coverage == "ALL": additional_conditions = ""
        else:                                         additional_conditions = f" AND (vn.identifier IN {match_on_properties} OR elementId(vn) IN {match_on_element_id})"
        
        
        Slicing_part = *GraphFunctions.stringify_ids(nodes_on_slice), return_all_subgraphs
        CC_part = additional_conditions, with_self_reference
        query = GraphFunctions.TSM_Slicing_for_cc_query(*Slicing_part) + '\n' + GraphFunctions.combinatorial_coverage_from_slicing_query(*CC_part)
        return session.run(query)
        
    
    ################## Node prevalence update ##############

    # User-Defined functions to create in java, it will be able to be called directly in Neo4j; must add .jar file in plugins of Neo4j instance 
    # https://github.com/neo4j-examples/neo4j-procedure-template/
    # https://neo4j.com/docs/java-reference/4.3/extending-neo4j/procedures/
    # https://neo4j.com/docs/java-reference/4.3/extending-neo4j/customized-code/
    # TODO done, need to put the project as a module
    # TODO maybe optimize query by processing by depth
    # TODO do we really need ordered occurrences ?

    @staticmethod
    def set_prevalence(session):
        session.run(GraphFunctions.set_occurrences_query())
        session.run(GraphFunctions.set_leaves_prevalence_query())
        session.run(GraphFunctions.set_nonleaves_prevalence_query())

    @staticmethod
    def set_occurrences_query():
        return """MATCH (nonexistent:SpecificationNode) WHERE NOT (nonexistent)<-[:IS_SPECIFIED_BY]-(:ValueNode) SET nonexistent.occurrence = 0
MATCH (sroot:SpecificationNode) WHERE NOT (sroot)<-[:CONTAINS]-()
MATCH (v:ValueNode)-[:IS_SPECIFIED_BY]->(sroot) SET v.occurrence = 1 WITH collect(v) AS vn, sroot
SET sroot.occurrence = size(vn) WITH sroot
CALL(sroot){
  MATCH (v:ValueNode)-[:IS_SPECIFIED_BY]->(s:SpecificationNode) WITH collect(v) AS vn, s
  MATCH p = (sroot)-[:CONTAINS*]->(s) WITH vn, s, length(p) AS depth
  RETURN vn, s, depth ORDER BY depth
}
WITH vn, s
CALL(vn, s){
  MATCH (s)<-[:CONTAINS]-(mother_spec:SpecificationNode)
  CALL(*){
    OPTIONAL MATCH (mother_spec)<-[:ANNOTATES]-(a:AnnotationNode {annotation: 'This value is optional'})
    CALL(mother_spec, a){
      WHEN a IS :: NULL
      THEN RETURN mother_spec.occurrence as occ
      ELSE{
        MATCH (mother_spec)<-[:IS_SPECIFIED_BY]-(mother_value:ValueNode)
        RETURN reduce(occu = 0, m in collect(mother_value)| occu + m.occurrence) as occ
      }
    }
    SET s.occurrence = occ 
  }
  WITH vn, mother_spec
  CALL(mother_spec){
    OPTIONAL MATCH (mother_spec)<-[:IS_SPECIFIED_BY]-(:ValueNode)-[r:CONTAINS]->(:ValueNode) WITH collect(r.listIndex) as edges_index
    CALL(edges_index){
      WHEN edges_index = []
      THEN RETURN -1 AS edge_max
      ELSE {
        UNWIND edges_index AS edge_index
        UNWIND edge_index as index
        RETURN max(index) AS edge_max
      }
    }
    RETURN edge_max
  }
  WITH vn, edge_max
  UNWIND vn as vnode
  CALL(vnode, edge_max){
    WHEN edge_max = -1
    THEN {
      MATCH (mother:ValueNode)-[:CONTAINS]->(vnode)
      WITH reduce(occu = 0, m in collect(mother)| occu + m.occurrence) as mothers_occ, vnode
      SET vnode.occurrence = mothers_occ
    }
    ELSE{
      WITH vnode
      MATCH (mother:ValueNode)-[r:CONTAINS]->(vnode) WITH r.listIndex AS indexe, vnode, collect(mother) as mother
      WITH indexe, vnode, reduce(occ = 0, m in mother|occ + m.occurrence) as occurrence_on_1_edge_index
      let occ1edgeindex_positionned = [i in range(0, edge_max)|occurrence_on_1_edge_index*toInteger(i in indexe)]
      with vnode, collect(occ1edgeindex_positionned) as all_occ_on_edges
      SET vnode.occurrence_ordered = [i in range(0, edge_max)|reduce(acc = 0, j in range(0, size(all_occ_on_edges)-1)|acc + all_occ_on_edges[j][i])]
      SET vnode.occurrence = reduce(acc = 0, m in vnode.occurrence_ordered|acc+m)
    }
  }
}
"""

    @staticmethod
    def set_leaves_prevalence_query():
        return """match (vn:ValueNode)-[:IS_SPECIFIED_BY]->(sn:SpecificationNode)
SET vn.prevalence = toFloat(vn.occurrence)/sn.occurrence
CALL(vn, sn){
  WHEN NOT vn.occurrence_ordered IS ::NULL
  THEN SET vn.prevalence_ordered = [i in range(0, size(vn.occurrence_ordered)-1)|toFloat(vn.occurrence_ordered[i])/sn.occurrence]
}"""

    @staticmethod
    def set_nonleaves_prevalence_query():
        return """match (mvn:ValueNode) WHERE (mvn)-[:CONTAINS]->()
match (vleaf:ValueNode) WHERE (mvn)-[:CONTAINS*]->(vleaf) AND NOT (vleaf)-[:CONTAINS]->() WITH mvn, collect(vleaf.prevalence) as leaves_prevalence
SET mvn.prevalence = TSM_Statistics(leaves_preavalence, -1)"""



    ################## create TSM from DB ######################

    @staticmethod
    def TSM_from_db(session):
        db_vn, db_sn, db_ce, db_se = session.run(GraphFunctions.get_TSM_query()).single()
        vn = [VNode(node_element['identifier'], node_element['value']) for node_element in db_vn]
        sn = [(SNode(node_element['name'], locate(node_element['type'])), node_element.element_id) for node_element in db_sn]
        finding_method_vn = lambda node_element : TCM.find_node(vn, lambda node: node.get_identifier() == node_element['identifier'])
        finding_method_sn = lambda node_element : TCM.find_node(sn, lambda node: node[1] == node_element.element_id)[0]

        ce = []
        for edge in db_ce:
            if "ValueNode" in edge[0].labels:   finding_method = finding_method_vn
            else:                               finding_method = finding_method_sn
            ce.append(Edge(finding_method(edge[0]), finding_method(edge[1])))
        se = []
        for edge in db_se:
            se.append(Edge(finding_method_vn(edge[0]), finding_method_sn(edge[1])))
        sn = list(map(lambda x : x[0], sn))
        return TSM([], vn, sn, ce, se)
    

    ################# query for testing db TSM validity ###############

    @staticmethod
    def Db_Validity_query():
        return """OPTIONAL MATCH (n) WHERE NOT n:ValueNode AND NOT n:SpecificationNode AND NOT n:AnnotationNode AND NOT n:FileNode WITH collect(n) = [] AS n_types
OPTIONAL MATCH (s:SpecificationNode) WHERE NOT (s)<-[:IS_SPECIFIED_BY]-(:ValueNode) AND NOT (s)<-[:ANNOTATES]-(:AnnotationNode) WITH s IS NULL AS value_for_spec, n_types
OPTIONAL MATCH p = (f:FileNode)-[:ANNOTATES]->(n) WHERE NOT n:ValueNode OR (n:ValueNode)<-[:CONTAINS]-() WITH collect(p) = [] AS file_annotation, value_for_spec, n_types
OPTIONAL MATCH p = (a:AnnotationNode)-[:ANNOTATES]->(n) WHERE NOT a:FileNode AND NOT n:SpecificationNode WITH collect(p) = [] AS option_annotation, file_annotation, value_for_spec, n_types
OPTIONAL MATCH p = (start:SpecificationNode)-[:CONTAINS]-(end:ValueNode) WITH collect(p) = [] AS e_contains, option_annotation, file_annotation, value_for_spec, n_types
OPTIONAL MATCH p = (start)-[:IS_SPECIFIED_BY]->(end) WHERE start:SpecificationNode OR end:ValueNode WITH collect(p) = [] as e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types
OPTIONAL MATCH (n:ValueNode) WHERE EXISTS{MATCH (m:ValueNode) WHERE m<>n AND m.identifier = n.identifier AND m.value = n.value} WITH collect(n) = [] AS duplicate, e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types
OPTIONAL MATCH (n:SpecificationNode) WHERE NOT (n)<-[:CONTAINS]-() WITH count(n) = 1 AS unique_root, duplicate, e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types
OPTIONAL MATCH (n) WHERE NOT (n)--() OR (n)--(n) WITH n IS NULL AS node_alone, unique_root, duplicate, e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types
OPTIONAL MATCH (n)-[:CONTAINS]->() WHERE (n:ValueNode AND n.value <> NULL) OR (n:SpecificationNode AND NOT n.type IN ['dict', 'list']) WITH n IS NULL AS node_structure, node_alone, unique_root, duplicate, e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types
OPTIONAL MATCH (m)<-[:IS_SPECIFIED_BY]-(n:ValueNode)-[:IS_SPECIFIED_BY]->(o) WITH n IS NULL as unique_spec, node_structure, node_alone, unique_root, duplicate, e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types
OPTIONAL MATCH (m)-[:CONTAINS]->(n:SpecificationNode)<-[:CONTAINS]-(o) WITH n IS NULL as unique_s_parent, unique_spec, node_structure, node_alone, unique_root, duplicate, e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types
OPTIONAL MATCH (n:ValueNode)-[:IS_SPECIFIED_BY]->(s:SpecificationNode) WHERE (s.type IN ['dict', 'list'] AND NOT n.value IS :: NULL) OR (s.type = 'bool' AND NOT n.value IS :: BOOLEAN) or (s.type = 'int' AND NOT n.value IS :: INTEGER) or (s.type = 'float' AND NOT n.value IS :: FLOAT) or (s.type = 'str' AND NOT n.value IS :: STRING) WITH n IS NULL as type_spec, unique_s_parent, unique_spec, node_structure, node_alone, unique_root, duplicate, e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types
OPTIONAL MATCH (msn:SpecificationNode)<-[:IS_SPECIFIED_BY]-(mvn:ValueNode)-[:CONTAINS]->(vn:ValueNode)-[:IS_SPECIFIED_BY]->(sn:SpecificationNode)<-[:CONTAINS]-(msn) WITH count(DISTINCT vn) AS prop_5, type_spec, unique_s_parent, unique_spec, node_structure, node_alone, unique_root, duplicate, e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types
MATCH (root:ValueNode) WHERE NOT (root)<-[:CONTAINS]-() WITH count(root) as nb_root, prop_5, type_spec, unique_s_parent, unique_spec, node_structure, node_alone, unique_root, duplicate, e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types
MATCH (n:ValueNode) WITH count(n) AS nb_node, nb_root, prop_5, type_spec, unique_s_parent, unique_spec, node_structure, node_alone, unique_root, duplicate, e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types
OPTIONAL MATCH (n)-[]->(m), cyclePath=shortestPath((m)-[*]->(n)) WITH cyclePath IS NULL as is_cycle, prop_5 = nb_node-nb_root AS spec_child_id_child_spec, type_spec, unique_s_parent, unique_spec, node_structure, node_alone, unique_root, duplicate, e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types
return all(elmnt in [is_cycle, spec_child_id_child_spec, type_spec, unique_s_parent, unique_spec, node_structure, node_alone, unique_root, duplicate, e_specifies, e_contains, option_annotation, file_annotation, value_for_spec, n_types] WHERE elmnt = TRUE) as is_db_valid"""






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

if __name__ == "__main__":
    args = sys.argv
    if len(args) == 1: main()
    elif args[1] == 'test':
        import tests.test_db_to_tsm as test
        test.validate_db()
    elif args[1] == 'prevalence':
        URI = "bolt://localhost:7687"
        AUTH = ("neo4j", "password")
        DB_NAME = AUTH[0]
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            driver.verify_connectivity()
            with driver.session(database = DB_NAME) as session:
                GraphFunctions.prevalence_without_optional_values(session, compute_with_occurrence = True, set_leaves_occurrences = True, set_in_db = True)