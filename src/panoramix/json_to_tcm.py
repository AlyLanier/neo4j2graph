import os
import json
import hashlib
from numpy import format_float_scientific

NODE_SIMPLE_TYPES = (str, int, float, bool)
NODE_COMPOSITE_TYPES = (list, dict)
TYPES = {
    bool : 1,
    int : 2,
    float : 3,
    str : 4
}

class Node:

    def __init__(self, name: str, value: bool|int|float|str|None, path: str = None, _hidden_type: type = None):
        self.n = name
        self.v = value
        self.path = path
        self.signature = None
        self._type = _hidden_type
        self.identifier = None
    
    def __repr__(self) -> str:
        return f"N({self.name()}, {self.val()}, {self._type})"
    
    def corresponds_to(self, other: Node) -> bool:
        return self.get_identifier() == other.get_identifier()
    
    def name(self) -> str:
        return self.n

    def val(self) -> bool|int|float|str|None:
        return self.v

    def set_val(self, value: bool|int|float|str|None) -> None:
        self.v = value
    
    def cast(self, typ: type) -> None:
        if self.val() is None: return
        self.set_type(typ(self.val()))
    
    def get_path(self) -> str:
        return self.path
    
    def get_signature(self) -> str:
        return self.signature
    
    def set_signature(self, sig: str) -> None:
        self.signature = sig
        self.set_identifier()
    
    def get_type(self) -> type:
        return (type(self.val()) if self._type is None else self._type)
    
    def get_stype(self) -> str:
        return self.get_type().__name__
    
    def set_type(self, t: type) -> None:
        self._type = t
    
    def get_v_node_creation_info(self) -> tuple[str, bool|int|float|str|None]:
        return self.get_identifier(), self.val()

    def get_s_node_creation_info(self) -> tuple[str, type]:
        return self.name(), self.get_type()
    
    ############### hash function ###########################

    def hash_code(self) -> str:
        return hashlib.md5(repr((self.get_path(), self.get_signature())).encode()).hexdigest()
    
    def set_identifier(self) -> None:
        self.identifier = self.hash_code()

    def get_identifier(self) -> str:
        return self.identifier


class Edge:
    def __init__(self, source: Node, target: Node, index: int|None = None) -> None:
        self.src = source
        self.tgt = target
        if isinstance(index, list):     self.index = index
        elif isinstance(index, int):    self.index = [index]
        else:                           self.index = None
    
    def __repr__(self) -> str:
        return f"E({self.source()} -> {self.target()})"
    
    def corresponds_to(self, other: Edge) -> bool:
        return self.source().corresponds_to(other.source()) and self.target().corresponds_to(other.target())
    
    def source(self) -> Node:
        return self.src

    def target(self) -> Node:
        return self.tgt
    
    def get_index(self) -> list[int]:
        return self.index

    def concat_index(self, i: list[int]) -> None:
        for index in i:
            if index not in self.get_index(): self.index.append(index)


class TCM:

    def __init__(self, file_path: str, data_key: str = None) -> None:
        self.annotations = {"filenames": {}, "nonexistent_nodes": {}}
        self.nodes, self.edges = self.json_to_tcm(file_path, data_key)
        self.add_annotation("filenames", self.search_root(self.get_edges()).get_identifier(), file_path)
        self.process_nonexistent_nodes_annotation()
    

    ################# Loading data from json file #################

    def json_to_tcm(self, file: str, data_key: str) -> None:
        with open(file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"[ERROR] Failed to parse {file}: {e}")
        return self.nodify(data, data_key)
    
    @staticmethod
    def find_real_data(data: dict, key: str) -> dict|None:
        if key is None: return data
        if key in data: return data[key]
        else:
            for values in data.values():
                if isinstance(values, dict):
                    ret = TCM.find_real_data(values, key)
                    if ret is not None: return ret
    

    ############ functions to transform data into Test Case Model ###########

    def nodify(self, data: dict, data_key: str) -> tuple[list[Node], list[Edge]]:
        data = TCM.find_real_data(data, data_key)
        path = 'root'
        root = self.create_node("root", None, path)
        nodes = [root]
        edges = []
        sig = self.nodify_rec(data, root, nodes, edges, path)
        if sig is None: return [], []
        return nodes, edges

    def nodify_rec(self, data: dict, mother_node: Node, nodes: list[Node], edges: list[Edge], current_path: str) -> tuple[str, any]:
        data_type, generator = TCM.create_generator(data, mother_node)
        mother_node.set_type(list if data_type == "list" else dict)

        signature_items = []
        for i, (k, v) in enumerate(generator):
            sig = self.process_node(k, v, mother_node, nodes, edges, f"{current_path}.{k}", i)
            if sig: signature_items.append(sig)
        
        if signature_items == []: return None
        signature_item = (data_type, sorted(signature_items)) if data_type == "dict" else (data_type, signature_items)
        mother_node.set_signature(signature_item)
        
        signature = (mother_node.name(), signature_item)
        return signature

    def process_node(self, k: any, v: bool|int|float|str|list|dict|None, mother_node: Node, nodes: list[Node], edges: list[Edge], current_path: str, list_index: list|None) -> tuple[str, any]|None:
        if isinstance(v, NODE_SIMPLE_TYPES):
            casted_value = TCM.value_cast(v)
            new_node = self.create_node(k, casted_value, current_path)
            signature = (k, ("scalar", TCM.cast_for_signature(casted_value)))
            new_node.set_signature(signature[1])
        elif v is not None:
            new_node = self.create_node(k, None, current_path)
            signature = self.nodify_rec(v, new_node, nodes, edges, current_path)
            if signature is None:
                self.add_annotation("nonexistent_nodes", mother_node, k)
                return None
        else:
            self.add_annotation("nonexistent_nodes", mother_node, k)
            return None

        nodes.append(new_node)
        edges.append(self.create_edge(mother_node, new_node, list_index if mother_node.get_type() == list else None))
        
        return signature
    
    @staticmethod
    def create_generator(data: list|dict, mother_node: Node) -> tuple[str, iter[tuple[str, any]]]:
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
    def value_cast(obj: any) -> bool|int|float|str:
        if isinstance(obj, str):
            if obj == "0": return False
            if obj == "1": return True

            try: return int(obj)
            except: pass
            try: return float(obj)
            except: pass
        return obj
    
    @staticmethod
    def cast_for_signature(obj: bool|int|float|str) -> str:
        if isinstance(obj, (bool, int, float)): return format_float_scientific(obj)
        else:                                   return obj
        
    
    ###################### getters & node-edge creators ####################
    
    def get_nodes(self) -> list[Node]:
        return self.nodes

    def get_edges(self) -> list[Edge]:
        return self.edges
    
    def get_model(self) -> tuple[list[Node], list[Edge]]:
        return self.get_nodes(), self.get_edges()

    def create_node(self, label: str, value: any, path: str, stype: type = None) -> Node:
        return Node(label, value, path, stype)
    
    def create_edge(self, source: Node, target: Node, index: list[int] = None) -> Edge:
        return Edge(source, target, index)
    
    def get_annotations(self, annotation_type: str = "all") -> any:
        if annotation_type == "all":
            return self.annotations
        else:
            return self.annotations[annotation_type]
    
    def add_annotation(self, annotation_type: str, k: any, v: any) -> None:
        if k in self.annotations[annotation_type]:  self.annotations[annotation_type][k].append(v)
        else:                                       self.annotations[annotation_type][k] = [v]

    def get_leaves(self, source_node: Node) -> list[Node]:
        edges = self.get_edges()
        ret = []

        to_process = TCM.find_children(source_node, edges)
        for node in to_process:
            if TCM.is_leaf(node, edges):ret.append(node)
            else:                       to_process += TCM.find_children(node, edges)

        return ret


    ################ node/edge finder #############################

    @staticmethod
    def find_node_from_hash(node_list: list[Node], hash: str) -> Node|None:
        condition = lambda node : node.get_identifier() == hash
        return TCM.find_node(node_list, condition, lambda x : x)

    @staticmethod
    def find_node_from_edge(edge_list: list[Edge], match_node: Node, from_source: bool) -> Node:
        if from_source: functions = (lambda edge : edge.source() == match_node), (lambda edge : edge.target())
        else:           functions = (lambda edge : edge.target() == match_node), (lambda edge : edge.source())

        return TCM.find_node(edge_list, *functions)

    @staticmethod
    def find_node(object_list: list, condition: function, return_value: function = lambda x : x) -> Node|None:
        for obj in object_list:
            if condition(obj): return return_value(obj)
        return None
    
    @staticmethod
    def find_parents(node: Node, edge_list: list[Edge]) -> list[Node]:
        return [edge.source() for edge in edge_list if edge.target() == node]
    
    @staticmethod
    def find_children(node: Node, edge_list: list[Edge]) -> list[Node]:
        return [edge.target() for edge in edge_list if edge.source() == node]
    
    @staticmethod
    def find_edges(edge_list: list[Edge], from_node: Node|None = None, to_node: Node|None = None) -> list[Edge]:
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

    def show_tcm(self, alinea_length: int = 4, search_root:bool = False) -> None:
        nodes, edges = self.get_model()
        root_node = TCM.search_root(nodes, edges) if search_root else nodes[0]
        print(self.show_tcm_rec("", root_node, 0, alinea_length))

    def show_tcm_rec(self, return_string: str, current_node: Node, current_alinea: int, alinea_length: int) -> str:
        return_string += f"{current_node}\n"

        _, edges = self.get_model()
        children = [x.target() for x in edges if x.source() == current_node]
        if children == [] : return return_string

        next_alinea = current_alinea + alinea_length
        for child in children:
            return_string = self.show_tcm_rec(return_string + next_alinea*" ", child, next_alinea, alinea_length)
        
        return return_string


    ################ searching root of graph ################

    @staticmethod
    def is_root(node: Node, edge_list: list[Edge]) -> bool:
        return [] == TCM.find_parents(node, edge_list)

    @staticmethod
    def is_leaf(node: Node, edge_list: list[Edge]) -> bool:
        return [] == TCM.find_children(node, edge_list)
    
    @staticmethod
    def search_root(edge_list: list[Edge], start_edge:int = 0) -> Node:
        if edge_list == []: return None
        if start_edge >= len(edge_list):raise(f"[ERROR] searched root from {start_edge}th edge but there only are {len(edge_list)} edges")
        
        current_node = edge_list[start_edge].source()
        return TCM.search_root_rec(edge_list, current_node)

    @staticmethod
    def search_root_rec(edge_list: list[Edge], current_node: Node) -> Node:
        for edge in edge_list:
            if edge.target() == current_node:
                return TCM.search_root_rec(edge_list, edge.source())
        return current_node
    

    ################# Unify TCM types #########################

    def unify_types(self) -> None:
        paths = {}
        for node in self.get_nodes():
            if node.get_path() in paths:
                paths[node.get_path()].append(node)
            else:
                paths[node.get_path()] = [node]
        
        for nodes in paths.values():
            types = set(map(lambda n : n.get_type(), nodes))
            if len(types) != 1:
                if dict in types or list in types: raise Exception(f"Invalid types for nodes {nodes}, all of them must be the same type, either 'dict' or 'list'")
                best_type = type(None)
                for node in nodes:
                    if TYPES[best_type] < TYPES[node.get_type()]: best_type = node.get_type()
                
                for node in nodes:
                    node.cast(best_type)
    

    ################# process annotations ##################

    def process_nonexistent_nodes_annotation(self) -> None:
        annotations_to_add, annotations_to_del = [], []
        for ne_parent_node, ne_names in self.get_annotations("nonexistent_nodes").items():
            for ne_name in ne_names:
                if ne_parent_node.get_identifier(): #if parent has not been integrated because it was null
                    annotations_to_add.append(("nonexistent_nodes", ne_parent_node.get_identifier(), ne_name))
            annotations_to_del.append(ne_parent_node)
        for annotation in annotations_to_add:
            self.add_annotation(*annotation)
        for annotation in annotations_to_del:
            del self.get_annotations("nonexistent_nodes")[annotation]
        


def main():
    json_path = "arc_json"
    processed_json = []
    max_process = 2
    for filename in os.listdir(json_path):
        if filename.endswith(".json"):
            file_path = os.path.join(json_path, filename)
            print(file_path)
            test = TCM(file_path, 'mahyco')
            processed_json.append(test)
            if len(processed_json) >= max_process:
                break

    max_show = 2
    for tcm in processed_json[:max_show]:
        tcm.show_tcm()
        print(tcm.get_annotations())
            



if __name__ == "__main__":
    main()
