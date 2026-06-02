import os
import json
import hashlib

NODE_SIMPLE_TYPES = (str, int, float, bool, type(None))
NODE_COMPOSITE_TYPES = (dict, list)
NODE_TYPES = (*NODE_SIMPLE_TYPES, *NODE_COMPOSITE_TYPES)

class Node:

    def __init__(self, name, value, path = None, _hidden_type = None):
        self.n = name
        self.v = value
        self.path = path
        self.signature = None
        self._type = _hidden_type
    
    def __repr__(self):
        return f"N({self.name()}, {self.val()}, {self._type})"
    
    def name(self):
        return self.n

    def val(self):
        return self.v
    
    def get_path(self):
        return self.path
    
    def get_signature(self):
        return self.signature
    
    def set_signature(self, sig):
        self.signature = sig
    
    def get_type(self):
        return (type(self.val()) if self._type is None else self._type)
    
    def get_stype(self):
        return self.get_type().__name__
    
    def set_type(self, t):
        self._type = t
    
    def get_v_node_creation_info(self):
        return self.get_identifier(), self.val()

    def get_s_node_creation_info(self):
        return self.name(), self.get_type()
    
    ############### hash function ###########################

    def hash_code(self):
        return hashlib.md5(repr((self.get_path(), self.get_signature())).encode()).hexdigest()
    
    def get_identifier(self):
        return self.hash_code()


class Edge:
    def __init__(self, source, target):
        assert source != target
        assert source is not None and target is not None
        self.src = source
        self.tgt = target
    
    def __repr__(self):
        return f"E({self.source()} -> {self.target()})"
    
    def source(self):
        return self.src

    def target(self):
        return self.tgt

class TCM:

    def __init__(self, file_path):
        self.nodes, self.edges = self.json_to_tcm(file_path)
    

    ################# Loading data from json file #################

    def json_to_tcm(self, file):
        with open(file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"[ERROR] Failed to parse {file}: {e}")
        
        return self.nodify(data)
    

    ############ functions to transform data into Test Case Model ###########

    def nodify(self, data):
        data = data['case']['mahyco']
        path = "mahyco"
        nodes = [self.create_node("root", None, path)]
        edges = []
        self.nodify_rec(data, nodes[0], nodes, edges, path)
        return nodes, edges

    def nodify_rec(self, data, mother_node, nodes, edges, current_path):
        data_type, generator = TCM.create_generator(data, mother_node)
        mother_node.set_type(list if data_type == "list" else dict)

        signature_items = []
        for k, v in generator:
            signature_items.append(self.process_node(k, v, mother_node, nodes, edges, f"{current_path}.{k}"))
        
        signature = (mother_node.name(), (data_type, sorted(signature_items)))
        mother_node.set_signature(signature[1])
        return signature


    def process_node(self, k, v, mother_node, nodes, edges, current_path, _stype = None):
        if isinstance(v, NODE_SIMPLE_TYPES):
            casted_value = TCM.value_cast(v)
            new_node = self.create_node(k, casted_value, current_path)
            signature = (k, ("scalar", casted_value))
            new_node.set_signature(signature[1])
        else:
            new_node = self.create_node(k, None, current_path)
            signature = self.nodify_rec(v, new_node, nodes, edges, current_path)
        
        nodes.append(new_node)
        edges.append(self.create_edge(mother_node, new_node))
        
        return signature
    
    @staticmethod
    def create_generator(data, mother_node):
        if isinstance(data, dict):
            data_type = "dict"
            generator = ((k, v) for k, v in data.items())
        elif isinstance(data, list):
            data_type = "list"
            generator = ((mother_node.name(), v) for v in data)
        else:
            raise Exception(f"[ERROR] item {data} is type {type(data)}, expected list or dict")
        
        return data_type, generator

    @staticmethod
    def value_cast(obj):
        if isinstance(obj, str):
            if obj == "0": return False
            if obj == "1": return True

            try: return int(obj)
            except: pass
            try: return float(obj)
            except: pass
        return obj
        
    
    ###################### getters & node-edge creators ####################
    
    def get_nodes(self):
        return self.nodes

    def get_edges(self):
        return self.edges
    
    def get_model(self):
        return self.get_nodes(), self.get_edges()

    def create_node(self, label, value, path, stype=None):
        return Node(label, value, path, stype)
    
    def create_edge(self, source, target):
        return Edge(source, target)


    ################ node/edge finder #############################

    @staticmethod
    def find_node_from_hash(node_list, node_to_match):
        condition = lambda node : node.get_identifier() == node_to_match.get_identifier()
        return TCM.find_node(node_list, condition, lambda x : x)

    @staticmethod
    def find_node_from_edge(edge_list, match_value, from_source):
        if from_source: functions = (lambda edge : edge.source() == match_value), (lambda edge : edge.target())
        else:           functions = (lambda edge : edge.target() == match_value), (lambda edge : edge.source())

        return TCM.find_node(edge_list, *functions)

    @staticmethod
    def find_node(object_list, condition, return_value = lambda x : x):
        for obj in object_list:
            if condition(obj): return return_value(obj)
        return None
    
    @staticmethod
    def find_parents(node, edge_list):
        return [edge.source() for edge in edge_list if edge.target() == node]
    
    @staticmethod
    def find_children(node, edge_list):
        return [edge.target() for edge in edge_list if edge.source() == node]
    
    @staticmethod
    def find_edges(edge_list, from_node = None, to_node = None):
        if from_node is not None and to_node is not None:
            node_condition = lambda edge : edge.source() == from_node and edge.target() == to_node
        elif from_node is not None :
            node_condition = lambda edge : edge.source() == from_node
        elif to_node is not None:
            node_condition = lambda edge : edge.target() == to_node
        else:
            return edge_list
        
        return [edge for edge in edge_list if node_condition(edge)]

    
    ################# Visualize Graph ######################        

    def show_tcm(self, alinea_length = 4, search_root=False):
        nodes, edges = self.get_model()
        root_node = TCM.search_root(nodes, edges) if search_root else nodes[0]
        print(self.show_tcm_rec("", root_node, 0, alinea_length))

    def show_tcm_rec(self, return_string, current_node, current_alinea, alinea_length):
        return_string += f"{current_node}\n"

        nodes, edges = self.get_model()
        children = [x.target() for x in edges if x.source() == current_node]
        if children == [] : return return_string

        next_alinea = current_alinea + alinea_length
        for child in children:
            return_string = self.show_tcm_rec(return_string + next_alinea*" ", child, next_alinea, alinea_length)
        
        return return_string


    ################ searching root of graph ################

    @staticmethod
    def is_root(node, edge_list):
        return [] == TCM.find_parents(node, edge_list)
    
    @staticmethod
    def search_root(edge_list, start_edge = 0):
        if edge_list == []: return None
        if start_edge >= len(edge_list):raise(f"[ERROR] searched root from {start_edge}th edge but there only are {len(edge_list)} edges")
        
        current_node = edge_list[start_edge].source()
        return TCM.search_root_rec(edge_list, current_node)

    @staticmethod
    def search_root_rec(edge_list, current_node):
        for edge in edge_list:
            if edge.target() == current_node:
                return self.search_root_rec(edge.source(), edges)
        return current_node

        


def main():
    json_path = "arc_json"
    processed_json = []
    max_process = 2
    for filename in os.listdir(json_path):
        if filename.endswith(".json"):
            file_path = os.path.join(json_path, filename)
            print(file_path)
            test = TCM(file_path)
            processed_json.append(test)
            if len(processed_json) >= max_process:
                break

    max_show = 2
    for tcm in processed_json[:max_show]:
        tcm.show_tcm()
        #for node in tcm.get_nodes():
        #    print(node.get_path(), node.get_signature())
            



if __name__ == "__main__":
    main()