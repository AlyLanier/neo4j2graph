import statistics
from jsonToTestCaseModel import TCM, Edge, NODE_COMPOSITE_TYPES

class SNode:
    def __init__(self, name, stype):
        self.n = name
        self.t = stype
    
    def __repr__(self):
        return f"SN({self.name()}, {self.stype()})"
    
    def name(self):
        return self.n

    def stype(self):
        return self.t
    
class VNode:
    def __init__(self, identifier, value):
        self.i = identifier
        self.v = value
    
    def __repr__(self):
        return f"VN({self.get_identifier()}, {self.val()})"
    
    def get_identifier(self):
        return self.i

    def val(self):
        return self.v

class TSM:

    def __init__(self, test_case_models):
        self.v_nodes, self.s_nodes, self.c_edges, self.s_edges = [], [], [], []
    
    ################### getters & list appends ###################

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
    

    ############### Create node or edge #######################
    
    @staticmethod
    def create_s_node(self, name, stype):
        return SNode(name, stype)

    @staticmethod
    def create_v_node(self, ident, value)
        return VNode(ident, value)

    @staticmethod
    def create_edge(self, src, tgt):
        return Edge(src, tgt)
    

    ################ SPEC binary relation ##################
    
    def spec(self, v_node):
        return TSM.find_node_from_edge(self.get_specification_edges(), v_node, True)
    
    def ceps(self, s_node):
        return [edge.source() for edge in self.get_specification_edges() if edge.target() == s_node]
    

    ################ node finder #############################

    @staticmethod
    def find_node_from_hash(in_this_list, node_to_match):
        condition = lambda node : node.get_identifier() == node_to_match.get_identifier()
        return TSM.find_node(in_this_list, condition, lambda x : x)

    @staticmethod
    def find_node_from_edge(in_this_list, match_value, from_source)
        if from_source is None: return None
        
        if from_source: functions = lambda edge : edge.source() == match_value, lambda edge : edge.target()
        else:           functions = lambda edge : edge.target() == match_value, lambda edge : edge.source()

        return TSM.find_node(in_this_list, *functions)

    @staticmethod
    def find_node(in_this_list, condition, return_value):
        for obj in in_this_list:
            if condition(obj): return return_value(obj)
        return None


    ################ expand Test Suite Model with TCM #####################

    def expand_tsm(self, tcm):
        tcm_root = tcm.search_root()
        self.process_option_value(tcm_root, *tcm.get_model())
        return self

    def process_option_value(self, current_node, tcm_nodes, tcm_edges):
        v_nodes = self.get_value_nodes()
        for v_node in v_nodes:
            if v_node.get_identifier() = current_node.get_identifier(): return

        new_v_node = TSM.create_v_node(current_node.get_identifier(), current_node.val())
        self.add_value_node(new_v_node)

        tcm_mother_node = TSM.find_node_from_edge(tcm_edges, current_node, from_source : False)
        if tcm_mother_node   is not None: tsm_mother_v_node = TSM.find_node_from_hash(v_nodes, tcm_mother_node)
        if tsm_mother_v_node is not None: tsm_mother_s_node = self.spec(tsm_mother_v_node)
        if tsm_mother_s_node is not None: tsm_s_node = TSM.find_node_from_edge(self.get_containment_edges(), tsm_mother_s_node, from_source : True)
    
            
        if tsm_s_node is not None and tsm_s_node.name() == current_node.name(): # maybe previous tsm_s_node still set TODO
            self.add_specification_edge(new_v_node, tsm_s_node)
        else:
            new_s_node = TSM.create_s_node(current_node.name(), type(current_node.val()))
            self.add_specification_edge(new_v_node, new_s_node)
            self.add_specification_node(new_s_node)
            self.add_containment_edge(tsm_mother_s_node, new_s_node)
        
        current_node_children = [edge.target() for edge in tcm_edges if edge.source() == current_node]
        for current_node_child in current_node_children:
            self.process_option_value(current_node_child, tcm_nodes, tcm_edges)
            tsm_v_node_child = TCM.find_node_from_hash(v_nodes, current_node_child)
            self.add_containment_edge(new_v_node, tsm_v_node_child)
        
    
    ################# Option Coverage ##################

    def option_coverage(self, current_s_node):
        if current_s_node.stype() not in NODE_COMPOSITE_TYPES: return self.ceps(current_s_node)

        s_node_parents = [edge.source() for edge in self.get_containment_edges() if edge.target() == current_s_node]
        res = []
        for s_node in s_node_parents:
            res += self.option_coverage(s_node)
        return res
    

    ################# TSM Slicing ##################

    def Slicing(self, value_nodes): #TODO
        return
    

    ################# Option Value Prevalence #############

    def compute_prevalence(self): #TODO
        return
    


if __name__ == '__main__':
    # test the code Alyssia
    return
