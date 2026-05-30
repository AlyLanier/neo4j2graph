import os
from jsonToTCM import TCM, Edge, NODE_COMPOSITE_TYPES

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
    
    def get_identifier(self):
        return self.i

    def val(self):
        return self.v
    
    def cast(self, typ):
        self.v = typ(self.v)

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

        new_v_node = TSM.create_v_node(*current_node.get_v_node_creation_info())
        self.add_value_node(new_v_node)

        tsm_mother_v_node, tsm_mother_s_node, tsm_s_nodes, tsm_filtered_s_node, tsm_s_node = None, None, [], [], None
        tcm_mother_node = TCM.find_node_from_edge(tcm_edges, current_node, from_source = False)
        if tcm_mother_node   is not None: tsm_mother_v_node = TCM.find_node_from_hash(v_nodes, tcm_mother_node)
        if tsm_mother_v_node is not None: tsm_mother_s_node = self.spec(tsm_mother_v_node)
        if tsm_mother_s_node is not None: tsm_s_nodes = TCM.find_children(tsm_mother_s_node, self.get_containment_specification_edges())
        if tsm_s_nodes             != []: tsm_filtered_s_node = list(filter(lambda x: x.name() == current_node.name(), tsm_s_nodes))
        if tsm_filtered_s_node     != []: tsm_s_node = tsm_filtered_s_node[0]

        if tsm_s_node is not None:
            #print(f"found specification for node {current_node} : {tsm_s_node}")
            self.process_type(current_node, tsm_s_node)
            self.add_specification_edge(new_v_node, tsm_s_node)
        else:
            if TCM.is_root(current_node, tcm_edges):
                new_s_node = TCM.search_root(self.get_containment_edges())
                if new_s_node is None:
                    new_s_node = TSM.create_s_node(*current_node.get_s_node_creation_info())
                    self.add_specification_node(new_s_node)
                    #print(f"did not find root, created node {new_s_node}")
                #else: print("found root, no need to create it")
            else:
                #print(tcm_mother_node, tsm_mother_v_node, tsm_mother_s_node, tsm_s_node)
                new_s_node = TSM.create_s_node(*current_node.get_s_node_creation_info())
                #print(f"did not find specification for node {current_node}, created node {new_s_node}")
                self.add_specification_node(new_s_node)
                self.add_containment_edge(tsm_mother_s_node, new_s_node)

            self.add_specification_edge(new_v_node, new_s_node)
        
        current_node_children = TCM.find_children(current_node, tcm_edges)
        for current_node_child in current_node_children:
            self.process_option_value(current_node_child, tcm_nodes, tcm_edges)
            tsm_v_node_child = TCM.find_node_from_hash(v_nodes, current_node_child)
            self.add_containment_edge(new_v_node, tsm_v_node_child)
    
    def process_type(self, current_node, tsm_s_node):
        current_node_valtype = type(current_node.val())
        tsm_s_nodetype = tsm_s_node.stype()
        
        #check types and print warning if not correct
        if tsm_s_nodetype != current_node_valtype and current_node.val() is not None:
            if tsm_s_nodetype == type(None) or (tsm_s_nodetype == bool and current_node_valtype in [int, float]) or (tsm_s_nodetype in [bool, int] and current_node_valtype == float):
                tsm_s_node.set_stype(current_node_valtype)
                self.update_value_nodes_types(tsm_s_node)
            else: print(f"[WARNING] TCM node {current_node} has value type {current_node_valtype}, expected {tsm_s_nodetype}")
    
    def update_value_nodes_types(self, s_node):
        if s_node.stype() == type(None): return
        v_nodes = TCM.find_parents(s_node, self.get_specification_edges())
        for v_node in v_nodes:
            v_nodetype = type(v_node.val())
            s_nodetype = s_node.stype()
            if v_nodetype != s_nodetype and v_nodetype in [int, float, bool]:
                print(f"value node type : {v_nodetype} for value {v_node.val()}")
                v_node.cast(s_nodetype)
                print(f"value node casted to : {s_nodetype} for value {v_node.val()}")


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
    for s in test_tsm.get_specification_nodes():
        print(s)
    return

if __name__ == '__main__':
    main()
