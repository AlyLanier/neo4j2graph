from jsonToTestCaseModel import TCM, ExactEdge, ExactNode

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
        self.c_edges.append(self.create_edge(src, tgt))
    
    def get_specification_edges(self):
        return self.s_edges
    
    def add_specification_edge(self, src, tgt):
        self.s_edges.append(self.create_edge(src, tgt))
    

    ############### Create node or edge #######################
    
    def create_node(self, hash_or_name, value):
        return ExactNode(hash_or_name, value)
    
    def create_edge(self, src, tgt):
        return ExactEdge(src, tgt)
    

    ################ SPEC binary relation ##################
    
    def spec(self, v_node):
        for s_edge in self.get_specification_edges()
            if s_edge.source() == v_node:
                return s_edge.target()
        return None
    

    ################ node finder #############################

    def find_node_from_identifier(in_this_list, node_to_match):
        condition = lambda node : node.get_identifier() == node_to_match.get_identifier()
        return self.find_node(in_this_list, condition, lambda x : x)

    def find_node_from_edge(in_this_list, match_value, from_source)
        if from_source is None: return None
        
        if from_source: functions = lambda edge : edge.source() == match_value, lambda edge : edge.target()
        else:           functions = lambda edge : edge.target() == match_value, lambda edge : edge.source()

        return self.find_node(in_this_list, *functions)

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

        new_v_node = self.create_node(current_node.get_identifier(), current_node.val())
        self.add_value_node(new_v_node)

        tcm_mother_node = self.find_node_from_edge(tcm_edges, current_node, from_source : False)
        if tcm_mother_node is not None  : tsm_mother_v_node = self.find_node_from_identifier(v_nodes, tcm_mother_node)
        if tsm_mother_v_node is not None: tsm_mother_s_node = self.spec(tsm_mother_v_node)
        if tsm_mother_s_node is not None: tsm_s_node = self.find_node_from_edge(self.get_containment_edges(), tsm_mother_s_node, from_source : True)
    
            
        if tsm_s_node is not None and tsm_s_node.name() == current_node.name():
            self.add_specification_edge(new_v_node, tsm_s_node)
        else:
            new_s_node = self.create_node(current_node.name(), type(current_node.val()))
            self.add_specification_edge(new_v_node, new_s_node)
            self.add_specification_node(new_s_node)
            self.add_containment_edge(tsm_mother_s_node, new_s_node)
        
        current_node_children = [edge.target() for edge in tcm_edges if edge.source() == current_node]
        for current_node_child in current_node_children:
            self.process_option_value(current_node_child, tcm_nodes, tcm_edges)
            tsm_v_node_child = self.find_node_from_identifier(v_nodes, current_node_child)
            self.add_containment_edge(new_v_node, tsm_v_node_child)
        

    
    def my_hash(node):
        return
    