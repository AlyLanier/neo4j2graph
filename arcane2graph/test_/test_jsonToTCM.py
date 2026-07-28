from jsonToTCM import *
from test_.test_graphs import *
import unittest
from ddt import ddt, data

#################### TESTS ######################

@ddt
class TestTCMCreation(unittest.TestCase):
    @staticmethod
    def get_TCMs():
        return TestTCMCreation.processed_tcm

    @classmethod
    def setUpClass(cls):
        json_path = "arc_json/arc_json_tests"
        cls.processed_tcm = []
        print(cls)
        for filename in os.listdir(json_path):
            if filename.endswith(".json"):
                file_path = os.path.join(json_path, filename)
                print(file_path)
                cls.processed_tcm.append(TCM(file_path, 'mahyco'))
                
    @data(*get_TCMs())
    def test_structure(self, tcm):
        nodes, edges = tcm.get_model()

        self.assertTrue(is_correct_node_types((nodes, Node)), "All nodes must be of type 'Node'")
        for node in nodes:
            self.assertNotEqual(node.val(), node._type, "A node should either have a value or a hidden type")
        
        self.assertTrue(is_correct_edge_types(edges, Edge, [lambda edge: isinstance(edge.source(), Node) and isinstance(edge.target(), Node)]), 
                        "All edges must be of type 'Edge', and all nodes at their ends must be of type 'Node'")

    @data(*get_TCMs())
    def test_validity(self, tcm):
        nodes, edges = tcm.get_model()

        self.assertFalse(is_duplicate(nodes, edges), "There must not be duplicate nodes or edges")
        self.assertTrue(is_unique_root((nodes, edges)), "The graph must only have one root")
        self.assertTrue(is_nodes_in_one_edge((nodes, edges)), "All nodes must be in at least 1 edge and all nodes from edges are in the node list") 
        
        for node in nodes: self.assertTrue(isinstance(node.val(), NODE_SIMPLE_TYPES) or node.get_type() in NODE_COMPOSITE_TYPES) # a node must have a value type in those 2 sets
        for edge in edges:
            self.assertIsNone(edge.source().val()) # an edge source is not a leaf
            #TODO edge.source().get_type() in NODE_COMPOSITE_TYPES
        
        self.assertTrue(is_all_different_edges(edges), "Two edges must not have the same source and target at the same time")
        self.assertTrue(is_unique_parent((nodes, edges)), "A node must only have one parent node")
        # a map node has all its children with distinct names
        # a list node has all its children with identical names to it
        for node in nodes:
            if node.get_type() in NODE_COMPOSITE_TYPES:
                children = tcm.find_children(node, edges)
                self.assertNotEqual(len(children), 0)
                children_names = set(map(lambda child: child.name(), children))
                if node.get_type() == list:
                    self.assertTrue(len(children_names) == 1 and node.name() in children_names)
                elif node.get_type() == dict:
                    self.assertEqual(len(children), len(children_names))
        

    @data(*get_TCMs())
    def test_acyclic(self, tcm):
        nodes = tcm.get_nodes()
        edges = tcm.get_edges()

        # edge does not have the same source and target
        for edge in edges:
            self.assertNotEqual(edge.source(), edge.target())
        
        # we know that :    there is exactly 1 root
        #                   each node only has 1 parent
        # so we just need to test for rings / if we follow the path from the root, 
        # we must catch all nodes and not find a seen_node
        root = tcm.search_root(edges, start_edge = len(edges)//2)
        seen_nodes = [root]
        TestTCMCreation.acyclic_rec(root, edges, seen_nodes)
        self.assertEqual(len(seen_nodes), len(nodes))

    @staticmethod
    def acyclic_rec(node, edges, seen_nodes):
        node_children = TCM.find_children(node, edges)
        for child in node_children:
            assert child not in seen_nodes
            seen_nodes.append(child)
            TestTCMCreation.acyclic_rec(child, edges, seen_nodes)

    
unittest.main()