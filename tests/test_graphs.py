from src.panoramix.json_to_tcm import *

def nodes_from_edges(edge_list):
    for edge in edge_list:
        yield edge.source()
        yield edge.target()

def format_types_isinstance(types):
    if not isinstance(types, tuple):
        if isinstance(types, list):
            types = tuple(types)
        else:
            types = (types,)
    return types

def is_correct_node_types(*node_list_and_types):
    result = []
    for node_list, node_types in node_list_and_types:
        types = format_types_isinstance(node_types)
        for node in node_list:
            if not isinstance(node, types):
                result.append(False)
                break
        else:
            result.append(True)
    return all(result)

def is_correct_edge_types(edge_list, edge_type, additional_conditions = []):
    types = format_types_isinstance(edge_type)
    for edge in edge_list:
        if not isinstance(edge, types): return False
        for condition in additional_conditions:
            if not condition(edge): return False
    return True

def is_duplicate(*lists):
    return any(map(lambda l: len(l) != len(set(l)), lists))

def is_unique_root(*node_list_and_edge_list):
    return all([(len([root for root in node_list if TCM.find_parents(root, edge_list) == []]) == 1) for node_list, edge_list in node_list_and_edge_list])

def is_nodes_in_one_edge(*node_list_and_edge_list):
    result = []
    for node_list, edge_list in node_list_and_edge_list:
        nodes_in_edges = set(node for node in nodes_from_edges(edge_list))
        if len(node_list) != len(nodes_in_edges): result.append(False)
        for node in node_list:
            if not node in nodes_in_edges:
                result.append(False)
                break
        else:
            result.append(True)
    return all(result)

def is_all_different_edges(*edge_lists):
    result = []
    for edge_list in edge_lists:
        for edge in edge_list:
            for other_edge in edge_list:
                if edge == other_edge: continue # same python object
                if other_edge.source() == edge.source() and other_edge.target() == edge.target():
                    result.append(False)
                    break
            else:
                continue
            break
        else:
            result.append(True)

    return all(result)

def is_unique_parent(*node_list_and_edge_list):
    result = []
    for node_list, edge_list in node_list_and_edge_list:
        for node in node_list:
            if len(TCM.find_parents(node, edge_list)) > 1:
                result.append(False)
                break
        else:
            result.append(True)
    return all(result)

def is_exact_unique_child(*node_list_and_edge_list):
    result = []
    for node_list, edge_list in node_list_and_edge_list:
        for node in node_list:
            if len(TCM.find_children(node, edge_list)) != 1:
                result.append(False)
                break
        else:
            result.append(True)
    return all(result)