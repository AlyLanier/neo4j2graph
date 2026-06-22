import os
import sys
from jsonToTCM import TCM, Edge, TYPES, NODE_COMPOSITE_TYPES

class SNode:
    def __init__(self, name, stype):
        self.n = name
        self.t = stype
    
    def __repr__(self):
        return f"SN({self.name()}, {self.stype_name()})"
    
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
    
    def corresponds_to(self, other):
        return self.get_identifier() == other.get_identifier()
    
    def get_identifier(self):
        return self.i

    def val(self):
        return self.v
    
    def cast(self, typ):
        if self.val() is None: return
        self.v = typ(self.val())

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
    

    ############### Create node or edge #######################
    
    @staticmethod
    def create_s_node(name, stype):
        return SNode(name, stype)

    @staticmethod
    def create_v_node(ident, value):
        return VNode(ident, value)

    @staticmethod
    def create_edge(src, tgt):
        return Edge(src, tgt)
    

    ################ SPEC binary relation ##################
    
    def spec(self, node):
        return TCM.find_node_from_edge(self.get_specification_edges(), node, True)
    
    def spec_multi(self, *v_nodes):
        res = []
        for node in v_nodes:
            res.append(self.spec(node))
        return res
    
    def ceps(self, s_node):
        return TCM.find_parents(s_node, self.get_specification_edges())


    ################ expand Test Suite Model with TCM #####################

    def expand_tsm(self, tcm):
        tcm_root = TCM.search_root(tcm.get_edges())
        self.process_option_value(tcm_root, *tcm.get_model())
        return self

    def process_option_value(self, current_node, tcm_nodes, tcm_edges):
        v_nodes = self.get_value_nodes()
        for v_node in v_nodes:
            if v_node.get_identifier() == current_node.get_identifier(): return
                # in theory we could process the type of the current_node to update its specification, but if current_node has a value consistent
                # with the nodes already in the tsm, no need to update the type for now

        new_v_node = TSM.create_v_node(*current_node.get_v_node_creation_info())
        self.add_value_node(new_v_node)

        tsm_mother_v_node, tsm_mother_s_node, tsm_s_node= None, None, None
        tcm_mother_node = TCM.find_node_from_edge(tcm_edges, current_node, from_source = False)
        if tcm_mother_node   is not None: tsm_mother_v_node = TCM.find_node_from_hash(v_nodes, tcm_mother_node)
        if tsm_mother_v_node is not None: tsm_mother_s_node = self.spec(tsm_mother_v_node)
        if tsm_mother_s_node is not None: tsm_s_node = TCM.find_node(self.get_containment_specification_edges(), lambda edge : edge.source() == tsm_mother_s_node and edge.target().name() == current_node.name(), lambda edge : edge.target())
        
        if tsm_s_node is not None:
            self.process_type(new_v_node, tsm_s_node)
            self.add_specification_edge(new_v_node, tsm_s_node)
        else:
            if TCM.is_root(current_node, tcm_edges):
                new_s_node = TCM.search_root(self.get_containment_edges())
                if new_s_node is None:
                    new_s_node = TSM.create_s_node(*current_node.get_s_node_creation_info())
                    self.add_specification_node(new_s_node)
            else:
                new_s_node = TSM.create_s_node(*current_node.get_s_node_creation_info())
                self.add_specification_node(new_s_node)
                self.add_containment_edge(tsm_mother_s_node, new_s_node)

            self.add_specification_edge(new_v_node, new_s_node)
        
        current_node_children = TCM.find_children(current_node, tcm_edges)
        for current_node_child in current_node_children:
            self.process_option_value(current_node_child, tcm_nodes, tcm_edges)
            tsm_v_node_child = TCM.find_node_from_hash(v_nodes, current_node_child)
            self.add_containment_edge(new_v_node, tsm_v_node_child)
    
    def process_type(self, tsm_v_node, tsm_s_node):
        if tsm_s_node.stype() in NODE_COMPOSITE_TYPES: return 
        tsm_new_v_type = type(tsm_v_node.val())
        tsm_s_nodetype = tsm_s_node.stype()
        if tsm_s_nodetype == tsm_new_v_type: return
        
        #check types and print warning if not correct
        if TYPES[tsm_s_nodetype] < TYPES[tsm_new_v_type]:
            tsm_s_node.set_stype(tsm_new_v_type)
            self.update_value_nodes_types(tsm_s_node)
        else:
            tsm_v_node.cast(tsm_s_nodetype)
    
    def update_value_nodes_types(self, s_node):
        # never used on s_node with type NoneType
        v_nodes = TCM.find_parents(s_node, self.get_specification_edges())
        for v_node in v_nodes:
            if v_node.val() is None: continue
            s_nodetype = s_node.stype()
            if type(v_node.val()) != s_nodetype:
                v_node.cast(s_nodetype)
    


def main():
    json_path = "arc_json"
    processed_json = []
    for filename in os.listdir(json_path):
        if filename.endswith(".json"):
            file_path = os.path.join(json_path, filename)
            print(file_path)
            test = TCM(file_path, 'mahyco')
            processed_json.append(test)
            if len(processed_json) >= 2:
                break
    
    test_tsm = TSM(processed_json)

if __name__ == "__main__":
    args = sys.argv
    if len(args) == 1: main()
    elif args[1] == 'test':
        import test_.test_TCMtoTSM
