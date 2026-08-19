from panoramix.json_to_tcm import *
from tests.test_graphs import *
import unittest

#################### TESTS ######################


class TestTCMCreation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.TCMS = [TCM(os.path.join("arc_json/arc_json_tests", filename), 'mahyco') for filename in os.listdir("arc_json/arc_json_tests") if filename.endswith(".json")]
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        del cls.TCMS
        return super().tearDownClass()

    def test_tcms(self):
        for tcm in self.TCMS:
            self.structure_test(tcm)
            self.validity_test(tcm)
            self.acyclic_test(tcm)

    def structure_test(self, tcm):
        nodes, edges = tcm.get_model()
        
        self.assertTrue(is_correct_node_types((nodes, Node)), "All nodes must be of type 'Node'")
        for node in nodes:
            self.assertNotEqual(node.val(), node._type, "A node should either have a value or a hidden type")
        
        self.assertTrue(is_correct_edge_types(edges, Edge, [lambda edge: isinstance(edge.source(), Node) and isinstance(edge.target(), Node)]), 
                        "All edges must be of type 'Edge', and all nodes at their ends must be of type 'Node'")

    def validity_test(self, tcm):
        nodes, edges = tcm.get_model()
        self.assertFalse(is_duplicate(nodes, edges), "There must not be duplicate nodes or edges")
        self.assertTrue(is_unique_root((nodes, edges)), "The graph must only have one root")
        self.assertTrue(is_nodes_in_one_edge((nodes, edges)), "All nodes must be in at least 1 edge and all nodes from edges are in the node list") 
        
        for node in nodes: self.assertTrue(isinstance(node.val(), NODE_SIMPLE_TYPES) or node.get_type() in NODE_COMPOSITE_TYPES, 
                                           f"A node must either have a simple value (i.e. the value must be one of these types : {NODE_SIMPLE_TYPES})\n or be a composite node (i.e. its virtual type must be one of these types : {NODE_COMPOSITE_TYPES})")
        for edge in edges:
            self.assertIsNone(edge.source().val(), "The source node of an edge must be a composite node (i.e. have 'None' as a value)")
            self.assertIn(edge.source().get_type(), NODE_COMPOSITE_TYPES, f"The source node of an edge must be a composite node (i.e. its virtual type must be one of these types : {NODE_COMPOSITE_TYPES})")
        
        self.assertTrue(is_all_different_edges(edges), "Two edges must not have the same source and target at the same time")
        self.assertTrue(is_unique_parent((nodes, edges)), "A node must only have one parent node")
        # a map node has all its children with distinct names
        # a list node has all its children with identical names to it
        for node in nodes:
            if node.get_type() in NODE_COMPOSITE_TYPES:
                children = tcm.find_children(node, edges)
                self.assertNotEqual(len(children), 0, "A composite node must have at least 1 children")
                children_names = set(map(lambda child: child.name(), children))
                if node.get_type() == list:
                    self.assertTrue(len(children_names) == 1 and node.name() in children_names, "A composite node of virtual type 'list' must have all its children have the same name as it")
                elif node.get_type() == dict:
                    self.assertEqual(len(children), len(children_names), "A composite node of virtual type 'dict' must have all its children have a different name")

    def acyclic_test(self, tcm):
        nodes, edges = tcm.get_model()
        
        # we know that :    there is exactly 1 root
        #                   each node only has 1 parent
        # so we just need to test for rings / if we follow the path from the root, 
        # we must catch all nodes and not find a seen_node
        root = tcm.search_root(edges)
        seen_nodes = [root]
        self.acyclic_rec(root, edges, seen_nodes)
        self.assertEqual(len(seen_nodes), len(nodes), "The graph must be acyclic")

    def acyclic_rec(self, node, edges, seen_nodes):
        node_children = TCM.find_children(node, edges)
        for child in node_children:
            self.assertNotIn(child, seen_nodes, "A node has been found to be a duplicate")
            seen_nodes.append(child)
            self.acyclic_rec(child, edges, seen_nodes)
