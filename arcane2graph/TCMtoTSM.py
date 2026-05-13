from jsonToTestCaseModel import TCM, ExactEdge, ENode

class TSM:

    def __init__(self, test_case_models):
        self.v_nodes, self.s_nodes, self.c_edges, self.s_edges = [], [], [], []
    
    def get_value_nodes(self):
        return self.v_nodes
    
    def get_specification_nodes(self):
        return self.s_nodes

    def get_containment_edges(self):
        return self.c_edges
    
    def get_specification_edges(self):
        return self.s_edges

    def expand_tsm(self, tcm):
        tcm_root = tcm.search_root()
        self.process_option_value(tcm_root, tcm)

    def process_option_value(self, current_node, tcm):
        tcm_nodes, tcm_edges = tcm.get_model()

    
    def my_hash(node):
        return
    