import statistics
import os
from jsonToTCM import TCM, Edge, NODE_COMPOSITE_TYPES

class SNode:
    def __init__(self, name, stype, path = ""):
        self.n = name
        self.t = stype
        self.p = path
    
    def __repr__(self):
        return f"SN({self.name()}, {self.stype().__name__})"
    
    def get_identifier(self): #for neo4j
        return id(self)
    
    def name(self):
        return self.n

    def stype(self):
        return self.t
    
    def stype_name(self):
        return self.t.__name__

    def set_stype(self, t):
        self.t = t
    
class VNode:
    def __init__(self, identifier, value):
        self.i = identifier
        self.v = value
    
    def __repr__(self):
        return f"VN({self.val()})"
    
    def get_identifier(self):
        return self.i

    def val(self):
        return self.v

class TSM:

    def __init__(self, test_case_models = [], v_nodes = [], s_nodes = [], c_edges = [], s_edges = []):
        self.v_nodes, self.s_nodes, self.c_edges, self.s_edges = v_nodes, s_nodes, c_edges, s_edges
        for test_case in test_case_models:
            self.expand_tsm(test_case)
    
    ################### getters & list appends ###################

    def get_model(self):
        return self.get_value_nodes(), self.get_specification_nodes(), self.get_containment_edges(), self.get_specification_edges()

    def get_value_nodes(self):
        return self.v_nodes
    
    def add_value_node(self, new_node):
        self.v_nodes.append(new_node)
    
    def get_specification_nodes(self):
        return self.s_nodes
    
    def add_specification_node(self, new_node):
        self.s_nodes.append(new_node)

    def get_containment_edges(self):
        return self.c_edges
    
    def add_containment_edge(self, src, tgt):
        self.c_edges.append(TSM.create_edge(src, tgt))
    
    def get_specification_edges(self):
        return self.s_edges
    
    def add_specification_edge(self, src, tgt):
        self.s_edges.append(TSM.create_edge(src, tgt))
    

    def get_containment_value_edges(self):
        return [edge for edge in self.get_containment_edges() if isinstance(edge.source(), VNode)]
    
    def get_containment_specification_edges(self):
        return [edge for edge in self.get_containment_edges() if isinstance(edge.source(), SNode)]


    ############# ????????????????????? ###################

    def is_root(self, node):
        return [] == TSM.find_parents(node, self.get_containment_edges())
    
    def is_all_root(self, nodes):
        for node in nodes:
            if not self.is_root(node):
                return False
        return True

    

    ############### Create node or edge #######################
    
    @staticmethod
    def create_s_node(name, stype, path):
        return SNode(name, stype, path)

    @staticmethod
    def create_v_node(ident, value):
        return VNode(ident, value)

    @staticmethod
    def create_edge(src, tgt):
        return Edge(src, tgt)
    

    ################ SPEC binary relation ##################
    
    def spec(self, node):
        return TSM.find_node_from_edge(self.get_specification_edges(), node, True)
    
    def spec_multi(self, *v_nodes):
        res = []
        for node in v_nodes:
            res.append(self.spec(node))
        return res
    
    def ceps(self, s_node):
        return TSM.find_parents(s_node, self.get_specification_edges())
    

    ################ node/edge finder #############################

    @staticmethod
    def find_node_from_hash(node_list, node_to_match):
        condition = lambda node : node.get_identifier() == node_to_match.get_identifier()
        return TSM.find_node(node_list, condition, lambda x : x)

    @staticmethod
    def find_node_from_edge(edge_list, match_value, from_source):
        if from_source is None: return None
        
        if from_source: functions = (lambda edge : edge.source() == match_value), (lambda edge : edge.target())
        else:           functions = (lambda edge : edge.target() == match_value), (lambda edge : edge.source())

        return TSM.find_node(edge_list, *functions)

    @staticmethod
    def find_node(object_list, condition, return_value):
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


    ################ expand Test Suite Model with TCM #####################

    def expand_tsm(self, tcm):
        tcm_root = tcm.search_root()
        self.process_option_value(tcm_root, *tcm.get_model())
        return self

    def process_option_value(self, current_node, tcm_nodes, tcm_edges):
        v_nodes = self.get_value_nodes()
        for v_node in v_nodes:
            if v_node.get_identifier() == current_node.get_identifier(): return

        new_v_node = TSM.create_v_node(current_node.get_identifier(), TSM.value_cast(current_node.val()))
        self.add_value_node(new_v_node)

        tsm_mother_v_node, tsm_mother_s_node, tsm_s_node = None, None, None
        tcm_mother_node = TSM.find_node_from_edge(tcm_edges, current_node, from_source = False)
        if tcm_mother_node   is not None: tsm_mother_v_node = TSM.find_node_from_hash(v_nodes, tcm_mother_node)
        if tsm_mother_v_node is not None: tsm_mother_s_node = self.spec(tsm_mother_v_node)
        if tsm_mother_s_node is not None: tsm_s_node = TSM.find_node_from_edge(self.get_containment_edges(), tsm_mother_s_node, from_source = True)
    
            
        if tsm_s_node is not None and tsm_s_node.name() == current_node.name():
            TSM.process_type(current_node, tsm_s_node)
            self.add_specification_edge(new_v_node, tsm_s_node)
        else:
            new_s_node = TSM.create_s_node(current_node.name(), type(TSM.value_cast(current_node.val())), current_node.get_path())
            self.add_specification_edge(new_v_node, new_s_node)
            self.add_specification_node(new_s_node)
            if tsm_mother_s_node is not None: self.add_containment_edge(tsm_mother_s_node, new_s_node)
        
        current_node_children = TSM.find_children(current_node, tcm_edges)
        for current_node_child in current_node_children:
            self.process_option_value(current_node_child, tcm_nodes, tcm_edges)
            tsm_v_node_child = TSM.find_node_from_hash(v_nodes, current_node_child)
            self.add_containment_edge(new_v_node, tsm_v_node_child)
    
    @staticmethod
    def process_type(current_node, tsm_s_node):
        current_node_valtype = type(TSM.value_cast(current_node.val()))
        tsm_s_nodetype = tsm_s_node.stype()
        #change NoneType to current_node type if not None
        if tsm_s_nodetype == type(None) and current_node.val() is not None: tsm_s_node.set_stype(current_node_valtype)
        
        #check types and print warning if not correct
        if tsm_s_nodetype != current_node_valtype and current_node.val() is not None:
            if tsm_s_nodetype == bool and current_node_valtype in [int, float]:
                tsm_s_node.set_stype(current_node_valtype)
            elif tsm_s_nodetype in [bool, int] and current_node_valtype == float:
                tsm_s_node.set_stype(current_node_valtype)
            else: print(f"[WARNING] TCM node {current_node} has value type {current_node_valtype}, expected {tsm_s_nodetype}")

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
    
    ################# Option Coverage ##################

    def option_coverage(self, current_s_node):
        if current_s_node.stype() not in NODE_COMPOSITE_TYPES: return self.ceps(current_s_node)

        s_node_parents = TSM.find_children(current_s_node, self.get_containment_edges())
        res = []
        for s_node in s_node_parents:
            res += self.option_coverage(s_node)
        return res
    

    ################# TSM Slicing ##################

    def slicing(self, value_nodes):
        if value_nodes == [] : return TSM()

        value_nodes = set(value_nodes)
        if len(value_nodes) == 1 : return one_node_TSM(*value_nodes)

        base_node = value_nodes[0]
        all_parents = self.ancestors(base_node)
        edges = self.get_containment_edges()
        
        for other_node in value_nodes[1:]:
            layer = set(other_node)
            if self.is_process_ancestor_layer(layer, all_parents): continue
            
            while not self.is_all_root(layer):
                layer = self.next_layer(layer)
                if self.is_process_ancestor_layer(layer, all_parents): break
            
        if not all_parents: return None
        common_parents = all_parents[0]
        
        for parent in common_parents:
            return #TODO

    def one_node_TSM(self, from_value_node):
        spec_node = self.spec(from_value_node)
        return TSM(v_nodes = [from_value_node], s_nodes = [spec_node], s_edges = TSM.find_edges(self.get_specification_edges(), *value_nodes, spec_node))
    
    def ancestors(self, base_node):
        all_parents = []
        
        layer = set(base_node)
        edges = self.get_containment_edges()
        while not self.is_all_root(layer):
            all_parents.append(layer)
            new_layer = set()
            for node in layer:
                if not self.is_root(node): new_layer.update(TSM.find_parents(node, edges))
            layer = new_layer
        all_parents.append(layer)

        return all_parents
    
    def is_process_ancestor_layer(self, nodes_layer, ancestor_layers):
        for node in nodes_layer:
            cpt = 0
            for layer_base_node in all_parents:
                found_parents = [layer_node for layer_node in layer_base_node if node == layer_node]
                if found_parents:
                    ancestor_layers[cpt] = found_parents
                    del ancestor_layers[:cpt]
                    return True
                
                cpt += 1
        return False
    
    def next_layer(self, current_layer):
        edges = self.get_containment_edges()
        new_layer = set()
        for node in current_layer:
            if not self.is_root(node): new_layer.update(TSM.find_parents(node, edges))
        return new_layer

    

    ################# Option Value Prevalence #############

    def compute_prevalence(self): #TODO
        return
    

    ################# save/load tsm #################

def load_tsm_from_neo4j_database(driver): #TODO
    return


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
    
    test_tsm = TSM(processed_json)
    return

if __name__ == '__main__':
    main()
