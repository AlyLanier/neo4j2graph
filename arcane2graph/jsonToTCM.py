import os
import json
import hashlib

NODE_SIMPLE_TYPES = (str, int, float, bool, type(None))
NODE_COMPOSITE_TYPES = (dict, list)
NODE_TYPES = (*NODE_SIMPLE_TYPES, *NODE_COMPOSITE_TYPES)

class Node:

    def __init__(self, name, value, node_id = None, path = None):
        self.n = name
        self.v = value
        self._id = node_id
        self.path = path
        self.signature = None
    
    def __repr__(self):
        return f"N({self.name()}, {self.val()})"
    
    def repr_for_edge(self):
        return f"#{self._id}"
    
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
    
    ############### hash function ###########################

    def hash_code(self):
        return hashlib.md5(repr((self.get_path(), self.get_signature())).encode()).hexdigest()
    
    def get_identifier(self):
        return self.hash_code()


class Edge:
    def __init__(self, source, target):
        self.src = source
        self.tgt = target
    
    def __repr__(self):
        return f"E({self.source().repr_for_edge()} -> {self.target().repr_for_edge()})"
    
    def source(self):
        return self.src

    def target(self):
        return self.tgt

class TCM:

    def __init__(self, file_path, node_id = -1):
        self.node_id = node_id
        self.nodes, self.edges = self.json_to_tcm(file_path)
    

    ################# Loading data from json file #################

    def json_to_tcm(self, file):
        with open(file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"[ERROR] Failed to parse {file_path}: {e}")
        
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

        signature_items = []
        for k, v in generator:
            signature_items.append(self.process_node(k, v, mother_node, nodes, edges, current_path))
        
        signature = (mother_node.name(), (data_type, sorted(signature_items))) # or not add name here but just for return
        mother_node.set_signature(signature) # ie signature[1] TODO
        return signature


    def process_node(self, k, v, mother_node, nodes, edges, current_path):
        new_path = f"{current_path}.{k}"
        new_node = self.create_node(k, v, new_path)
        nodes.append(new_node)
        edges.append(self.create_edge(mother_node, new_node))
        
        if isinstance(v, NODE_SIMPLE_TYPES):
            signature = (k, ("s", v)) # or not add k here but just for return
            new_node.set_signature(signature) # ie signature[1] TODO
        else:
            signature = self.nodify_rec(v, new_node, nodes, edges, new_path)
        
        return signature
    
    @staticmethod
    def create_generator(data, mother_node):
        if isinstance(data, dict):
            data_type = "d"
            generator = ((k, v) for k, v in data.items())
        elif isinstance(data, list):
            data_type = "l"
            generator = ((mother_node.name(), v) for v in data)
        else:
            raise f"[ERROR] item {data} is type {type(data)}, expected list or dict"
        
        return data_type, generator

        
    
    ###################### getters & node-edge creators ####################
    
    def get_nodes(self):
        return self.nodes

    def get_edges(self):
        return self.edges
    
    def get_model(self):
        return self.get_nodes(), self.get_edges()
    
    def get_node_id(self):
        return self.node_id
    
    def get_next_node_id(self):
        self.node_id += 1
        return self.get_node_id()

    def create_node(self, label, value, path):
        return Node(label, value, self.get_next_node_id(), path)
    
    def create_edge(self, source, target):
        return Edge(source, target)

    
    ################# Visualize Graph ######################        

    def show_tcm(self, alinea_length = 4, search_root=False):
        nodes, edges = self.get_model()
        root_node = search_root(nodes, edges) if search_root else nodes[0]
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

    def search_root(self, start_node = 0):
        return self.search_root_rec(self.get_nodes()[start_node])

    def search_root_rec(self, current_node):
        for edge in self.get_edges():
            if edge.target() == current_node:
                return self.search_root_rec(edge.source(), edges)
        return current_node
    

        


def main():
    json_path = "arc_json"
    processed_json = []
    for filename in os.listdir(json_path):
        if filename.endswith(".json"):
            file_path = os.path.join(json_path, filename)
            print(file_path)
            test = TCM(file_path)
            processed_json.append(test)
            if len(processed_json) >= 2:
                break
    
    for tcm in processed_json[0:1]:
        for node in tcm.get_nodes():
            print(node.get_signature())
            



if __name__ == "__main__":
    main()