from arcane2graph.TCMtoTSM import VNode, SNode, Edge
import neo4j.graph as ng

def to_identifiers(*lists):
    ret = []
    for l in lists:
        ret.append(to_identifier(l))
    return ret

def to_identifier(obj):
    if isinstance(obj, VNode):
        return obj.get_identifier()
    elif isinstance(obj, SNode):
        return f"{obj.name()}:{obj.stype_name()}"
    elif isinstance(obj, Edge):
        return [to_identifier(obj.source()), to_identifier(obj.target())]
    elif isinstance(obj, ng.Node):
        if "ValueNode" in obj.labels:
            return obj['identifier']
        elif "SpecificationNode" in obj.labels:
            return f"{obj["name"]}:{obj["type"]}"
    elif isinstance(obj, list):
        return [to_identifier(o) for o in obj]

def check_ids(*lists):
    for db_list, tsm_list in lists:
        for node_element_id in db_list:
            if node_element_id in tsm_list:
                tsm_list.remove(node_element_id)
            else:
                return False
    return True

def verify_db_tsm(tsm, query_result):
    vn, sn, ce, se = to_identifiers(*tsm.get_model())
    db_vn, db_sn, db_ce, db_se = to_identifiers(*[e for e in query_result[0][0]])

    ret = len(vn) == len(db_vn) and len(sn) == len(db_sn) and len(ce) == len(db_ce) and len(se) == len(db_se)
    return ret and check_ids((db_vn, vn), (db_sn, sn), (db_ce, ce), (db_se, se))