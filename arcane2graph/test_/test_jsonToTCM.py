from jsonToTCM import *

#################### TESTS ######################""

def test_node(node):
    assert node.val() is None or node._type is None

def test_structure(tcm):
    nodes = tcm.get_nodes()
    edges = tcm.get_edges()

    for obj in nodes:
        assert isinstance(obj, Node)
        test_node(obj)
    
    for obj in edges:
        assert isinstance(obj, Edge)
        assert isinstance(obj.target(), Node)
        assert isinstance(obj.source(), Node)

def test_validity(tcm):
    nodes = tcm.get_nodes()
    edges = tcm.get_edges()
    nodes_in_edges = set(nodes_from_edges(edges))

    assert len(nodes) == len(nodes_in_edges)

    for node in nodes:
        assert isinstance(node.val(), NODE_SIMPLE_TYPES) or node.get_type() in NODE_COMPOSITE_TYPES
        assert node in nodes_in_edges

    for edge in edges:
        src = edge.source()
        tgt = edge.target()
        assert src.val() is None and src.get_type() in NODE_COMPOSITE_TYPES

        for other_edge in edges: #TODO check si pas 2 même edges 
            pass
    
    # a map node has all its children with distinct names
    # a list node has all its children with identical names to it
    for node in nodes:
        if node.get_type() in NODE_COMPOSITE_TYPES:
            children = tcm.find_children(node, edges)
            assert len(children) != 0
            children_names = set(map(lambda child: child.name(), children))
            if node.get_type() == list:
                assert len(children_names) == 1 and node.name() in children_names
            elif node.get_type() == dict:
                assert len(children) == len(children_names)
    
    test_acyclic(tcm)
    

def test_acyclic(tcm):
    nodes = tcm.get_nodes()
    edges = tcm.get_edges()

    for edge in edges:
        assert edge.source() != edge.target() # made on object id as __eq__ or __neq__ was not defined for Node





        

################### Utils ####################

def nodes_from_edges(edge_list):
    for edge in edge_list:
        yield edge.source()
        yield edge.target()
    
