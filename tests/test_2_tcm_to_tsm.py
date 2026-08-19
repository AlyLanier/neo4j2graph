from panoramix.tcm_to_tsm import *
from tests.test_graphs import *
from itertools import combinations

import unittest

class TestTCMtoTSM(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        all_tcms = [TCM(os.path.join("arc_json/arc_json_tests", filename), 'mahyco') for filename in os.listdir("arc_json/arc_json_tests") if filename.endswith(".json")]

        cls.TCM_COMBINATIONS = list(combinations(all_tcms, int(len(all_tcms)-2)))[::4] + [all_tcms]
        cls.TSM_COMBINATED = [TSM(list(comb)) for comb in cls.TCM_COMBINATIONS] + [TSM(all_tcms)]
    
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        del cls.TCM_COMBINATIONS, cls.TSM_COMBINATED
        return super().tearDownClass()

    def test_tsms(self):
        for tsm, comb in zip(self.TSM_COMBINATED, self.TCM_COMBINATIONS):
            self.structure_test(tsm)
            self.validity_test(tsm)
            self.TSM_contains_TCMs(tsm, comb)

    def structure_test(self, tsm):
        vn, sn, ce, se = tsm.get_model()
        self.assertTrue(is_correct_node_types((vn, VNode), (sn, SNode)), "Value nodes must be of type 'VNode' and Specification nodes must be of type 'SNode'")
        self.assertTrue(is_correct_edge_types(ce, Edge, [lambda edge: isinstance(edge.source(), (VNode, SNode)), lambda edge: type(edge.source()) == type(edge.target())]), 
                        "Containment edges must be of type 'Edge' and their ends must be of the same type, being either 'VNode' or 'SNode'")
        self.assertTrue(is_correct_edge_types(se, Edge, [lambda edge: isinstance(edge.source(), (VNode)) and isinstance(edge.target(), SNode)]), 
                        "Specification edges must be of type 'Edge', their sources of type 'VNode' and their targets of type 'SNode'")

    def validity_test(self, tsm):
        vn, sn, ce, se = tsm.get_model()

        self.assertFalse(is_duplicate(vn, sn, ce, se), "There must not be duplicate nodes or edges")
        self.assertTrue(is_unique_root((sn, ce)), "The graph must only have one specification root")
        self.assertTrue(is_nodes_in_one_edge((vn+sn, ce), (vn+sn, se)), "All nodes must be in at least 1 containment and specification edge and all nodes from edges are in the node list")
        self.assertTrue(is_all_different_edges(ce, se), "Two edges must not have the same source and target at the same time")
        # an edge source is not a leaf
        for edge in ce:
            if isinstance(edge.source(), VNode):self.assertIsNone(edge.source().val(), "The source value node of a containment edge must be a composite node (i.e. have 'None' as a value)")
            else:                               self.assertIn(edge.source().stype(), NODE_COMPOSITE_TYPES, f"The source value node of a containment edge must be a composite node (i.e. its virtual type must be one of these types : {NODE_COMPOSITE_TYPES})") 
        self.assertTrue(is_unique_parent((sn, ce)), "A specification node must only have one specification parent node")
        self.assertTrue(is_exact_unique_child((vn, se)), "A value node must be specified by exactly 1 specification node")
        self.vn_sn_type_verification(se) # all value nodes have their values of the type notified in their spec node
        self.vn_child_spec_is_vn_spec_child(tsm) # proposition 5 of research paper : if vn contains vn', spec(vn) contains spec(vn')
        self.acyclic(tsm) # acyclic graph
        
    def acyclic(self, tsm):
        vn, sn, _, _ = tsm.get_model()

        
        # for spec nodes
        # we know that :    there is exactly 1 root
        #                   each node only has 1 parent
        # so we just need to test for rings / if we follow the path from the root, 
        # we must catch all nodes and not find a seen_node
        spec_containment_edges = tsm.get_containment_specification_edges()
        root = TCM.search_root(spec_containment_edges, start_edge = len(spec_containment_edges)//2)
        seen_nodes = [root]
        self.acyclic_rec(root, spec_containment_edges, seen_nodes)
        self.assertEqual(len(seen_nodes), len(sn), "The specification part of the graph must be acyclic")

        # for value nodes
        # we know nothing, so for each root, we must show that a node from depth n doesn't have an edge going to depth m < n
        # in reality here, depth m = depth n + 1
        # and that each vn node is found by traversing each root
        val_containment_edges = tsm.get_containment_value_edges()
        roots = [root for root in vn if TCM.find_parents(root, val_containment_edges) == []]
        verified_nodes = {} # node to depth
        for root in roots:
            depth_counter = 0
            self.acyclic_extended_rec(root, val_containment_edges, verified_nodes, depth_counter)
        self.assertEqual(len(verified_nodes), len(vn), "The values part of the graph must be acyclic")


    def acyclic_rec(self, node, edges, seen_nodes):
        node_children = TCM.find_children(node, edges)
        for child in node_children:
            self.assertNotIn(child, seen_nodes, "Child node already seen, the specification graph is not acyclic")
            seen_nodes.append(child)
            self.acyclic_rec(child, edges, seen_nodes)

    def acyclic_extended_rec(self, node, edges, verified_nodes, depth_counter):
        if node in verified_nodes:
            self.assertGreaterEqual(verified_nodes[node], depth_counter, "A node must always be found at the same depth in the graph (tree)") # in reality verified_nodes[node] == depth_counter
            return
        node_children = TCM.find_children(node, edges)
        for child in node_children:
            self.acyclic_extended_rec(child, edges, verified_nodes, depth_counter+1)
        verified_nodes[node] = depth_counter

    def vn_sn_type_verification(self, spec_edges):
        for edge in spec_edges:
            self.assertTrue((edge.source().val() == None and edge.target().stype() in NODE_COMPOSITE_TYPES) or isinstance(edge.source().val(), edge.target().stype()),
                            "The type of the value of a value node must be the one depicted in its specification node; or 'None' for a dict or a list")

    def vn_child_spec_is_vn_spec_child(self, tsm):
        vce, sce = tsm.get_containment_value_edges(), tsm.get_containment_specification_edges()
        for edge in vce:
            self.assertEqual(len(TCM.find_edges(sce, tsm.spec(edge.source()), tsm.spec(edge.target()))), 1, 
                             "A child of a value node must be specified by the child of its mother's specification node")

    def TSM_contains_TCMs(self, tsm, tcms):
        vn, cve = tsm.get_value_nodes(), tsm.get_containment_value_edges()
        for tcm in tcms:
            nodes, edges = tcm.get_model()
            for node in nodes:
                exists = False
                for v_node in vn:
                    if v_node.corresponds_to(node):
                        exists = True
                        break
                self.assertTrue(exists, "Nodes of tcms must be contained in the tsm")
            for edge in edges:
                exists = False
                for v_edge in cve:
                    if v_edge.corresponds_to(edge):
                        exists = True
                        break
                self.assertTrue(exists, "Edges of tcms must be contained in the tsm")

    