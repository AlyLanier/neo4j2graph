from neo4j import GraphDatabase
from data_hull import ChartDataMaker

from prefab_ui.app import PrefabApp
from prefab_ui.components import Button, Column, ForEach, Row, Text, DataTable, DataTableColumn, Grid, GridItem, Combobox, ComboboxOption, Label, If, Else, Elif, Textarea, Div, P, Container, H2
from prefab_ui.actions import CallHandler, AppendState, PopState, SetState
from prefab_ui.rx import Rx, RESULT, ERROR, ITEM, EVENT, INDEX
from prefab_ui.actions.mcp import CallTool
from prefab_ui.css import Responsive

from prefab_ui.components.charts import LineChart, BarChart, ChartSeries
from fastmcp import FastMCP, FastMCPApp
from fastmcp.tools import tool

import functools
import plotille
import re


class MCPxNeo4j:

    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")
    app = FastMCPApp("MyFirstApp")
    members = None
    db_identifier = None

    @staticmethod
    def set_members():
        MCPxNeo4j.members, MCPxNeo4j.db_identifier = MCPxNeo4j.query_all_specs()

#################### decorator for using neo4j ###################

    def _uses_db(func):
        @functools.wraps(func)
        def connexion_manager(*args, **kwargs):
            with GraphDatabase.driver(uri=MCPxNeo4j.URI, auth=MCPxNeo4j.AUTH) as driver:
                driver.verify_connectivity()
                with driver.session(database=MCPxNeo4j.AUTH[0]) as session:
                    return func(*args, session = session, **kwargs)

        return connexion_manager

################### functions to retrieve data from neo4j ##################

    @_uses_db
    @staticmethod
    def query_all_specs(session = None):
        members = []
        query = """match (root:SpecificationNode) where not (root)<-[:CONTAINS]-()
return 'root' as name, root.type AS type, 'root' as path, elementId(root) AS id
UNION
match (root:SpecificationNode) where not (root)<-[:CONTAINS]-()
match p=(root)-[:CONTAINS*]->(s:SpecificationNode)
with reduce(occ="root", n in nodes(p)[1..]|occ+'.'+n.name) as path, s as spec
return spec.name AS name, spec.type AS type, path, elementId(spec) AS id ORDER BY path"""
        result = session.run(query)
        for n, t, p, uri in result:
            members.append({'name': n, 'type': t, 'path': p, 'id': uri})
        db_id = re.match(".*:.*:", members[0]['id']).group()
        
        return members, db_id

    @staticmethod
    def query_spec(element_id, session = None):
        query = f"""match (s:SpecificationNode) where elementId(s) = '{element_id}'
match p=(root)-[:CONTAINS*]->(s) where not (root)<-[:CONTAINS]-()
with reduce(occ="root", n in nodes(p)[1..]|occ+'.'+n.name) as path, s

return s.name, path, s.type, s.occurrence""" #, a.range        optional match (a:AnnotationNode) where (a)-[:ANNOTATES]->(s)
        result = session.run(query).single()
        spec_name, spec_path, spec_type, spec_occ = result #, spec_range
        return {'name': spec_name, 'path': spec_path, 'type': spec_type, 'occurrence': spec_occ, 'range': None} #spec_range

    @staticmethod
    def query_specs(element_ids, session = None):
        query = f"""match (s:SpecificationNode) where elementId(s) IN {str(element_ids)}
match p=(root)-[:CONTAINS*]->(s) where not (root)<-[:CONTAINS]-()
with reduce(occ="root", n in nodes(p)[1..]|occ+'.'+n.name) as path, s

return s.name, path, s.type, s.occurrence, elementId(s)""" #, a.range        optional match (a:AnnotationNode) where (a)-[:ANNOTATES]->(s)
        result = session.run(query)
        ret = []
        for spec_name, spec_path, spec_type, spec_occ, spec_id in result: #, spec_range
            ret.append({'name': spec_name, 'path': spec_path, 'type': spec_type, 'occurrence': spec_occ, 'range': None, 'id': spec_id})#spec_range

        return ret

    @staticmethod
    def query_value(element_id, session = None):
        query = f"""match (s:SpecificationNode) where elementId(s) = '{element_id}'
match (vn:ValueNode) where (s)<-[:IS_SPECIFIED_BY]-(vn)
return CASE vn.value WHEN IS NULL THEN elementId(vn) ELSE vn.value END, vn.occurrence"""
        result = session.run(query)
        ret = {}
        for value, occurrences in result:
            ret[value] = occurrences
        return ret

    @staticmethod
    def query_values(element_ids, session = None):
        query = f"""match (s:SpecificationNode) where elementId(s) IN {str(element_ids)}
match (vn:ValueNode) where (s)<-[:IS_SPECIFIED_BY]-(vn)
with collect([CASE vn.value WHEN IS NULL THEN elementId(vn) ELSE vn.value END, vn.occurrence]) as values, s
return values, elementId(s)"""
        result = session.run(query)

        ret = {}
        for values, e_id in result:
            temp = {}
            for v_id, occ in values:
                temp[v_id] = occ
            ret[e_id] = temp
        return ret

    @_uses_db
    @staticmethod
    def query_score(element_id, session = None):
        spec_data = MCPxNeo4j.query_spec(element_id, session = session)
        option = MCPxNeo4j.query_value(element_id, session = session)

        return spec_data, option

    @_uses_db
    @staticmethod
    def query_scores(element_ids, session = None):
        spec_data = MCPxNeo4j.query_specs(element_ids, session = session)
        option = MCPxNeo4j.query_values(element_ids, session = session)

        return [(s_data, option[s_data['id']]) for s_data in spec_data]



#################### mcp ui objects ####################

    ############# All Specs as table #################""

    @app.ui()
    @staticmethod
    def show_specs():
        with PrefabApp(mode='dark') as app:
            DataTable(
                columns=[
                    DataTableColumn(key="name", header="Name"),
                    DataTableColumn(key="type", header="Type"),
                    DataTableColumn(key="path", header="Path", sortable=True)
                ],
                rows=MCPxNeo4j.members,
                search=True,
            )
        return app
    
    ############### Choose score to display ################

    @staticmethod
    def chart_as_string(data):
        ret = ""
        width = 200
        max_value_length = max(map(lambda x: len(str(x)), data.keys()))
        max_occ = max(data.values())
        for value, occ in data.items():
            string = str(value)
            ret += string + (max_value_length - len(string))*" " + " : " + int((width - (max_value_length + 3))*(occ/max_occ))*'*'+'\n'
        print(ret)

    @staticmethod
    def histogram_option(spec_data, options_data):
        print('HISTO')

        nb_occ_data = sum(options_data.values())
        if spec_data['occurrence'] != nb_occ_data:
            difference = spec_data['occurrence'] - nb_occ_data
            if difference > 0 : options_data['undefined'] = difference
        
        MCPxNeo4j.chart_as_string(options_data)
        data = [{'value': str(value), 'count': occ} for value, occ in options_data.items()]

        return {'data': data, 'name': spec_data['name'], 'view': 'Histo'}

    @staticmethod
    def plot_as_string(x, y, x_score, score, x_of_values, score_of_values, x_scale='linear'):
            fig = plotille.Figure()
            fig.width = 200
            fig.height = 20
            fig.set_x_limits(x[0], x[-1])
            fig.set_y_limits(0., max(y)*1.05)
            if x_scale == 'log':
                fig.x_label = 'Log(X)'
            fig.plot(x, y, lc='cyan', label='Hull')
            fig.plot(x_score, score, lc='green', label='Score new options')
            fig.scatter(x_of_values, score_of_values, lc='red', label='Score old option')
            print(fig.show(True))

    @staticmethod
    def plot_option(spec_data, options_data):
        print('PLOT')
        sign = lambda x: 1. if x >= 0 else -1.
        power = lambda n: (lambda x: abs(x)**n, lambda a: (lambda x: sign(x)*a**n * abs(x)**(n+1)/(n+1)))
        distance_function = power(2)

        data_maker = ChartDataMaker(options_data, spec_data['range'], *distance_function)
        data = data_maker.generate_data(1000, True)
        MCPxNeo4j.plot_as_string(*data, x_scale=data_maker.get_scale())

        x, y, x_score, score, x_of_values, score_of_values = data #f that
        graph_data = []
        size_score = len(x_score)
        counter = 0
        for abscissa, ordinate in zip(x, y):
            temp = {"x": abscissa, "y": ordinate}
            if counter < size_score and x_score[counter] == abscissa:
                temp["score"] = score[counter]
                counter += 1
            graph_data.append(temp)

        return {'data': graph_data, 'name': spec_data['name'], 'view': 'Plot'}

    @app.tool()
    @staticmethod
    def event_option(element_id):
        spec_data, options = MCPxNeo4j.query_score(element_id)
        print(spec_data)
        print(options)
    
        if spec_data['type'] in ['bool', 'int', 'str', 'list', 'dict']:
            return MCPxNeo4j.histogram_option(spec_data, options)
        elif spec_data['type'] == 'float':
            return MCPxNeo4j.plot_option(spec_data, options)

    @app.ui()
    @staticmethod
    def show_option_score():
        with PrefabApp(mode='dark') as app:
            options = Rx("options")
            with Column(gap=3):
                with Combobox(placeholder="Search options", 
                            searchPlaceholder="Filter by path",
                            onChange=[CallTool(MCPxNeo4j.event_option, 
                                        arguments={"element_id": EVENT}, 
                                        on_success=AppendState(options, RESULT, index=0), 
                                        on_error=AppendState(options, ERROR, index=0))],
                            css_class="w-fit mx-auto",
                            align='center'
                            ):
                    for data in MCPxNeo4j.members:
                        ComboboxOption(data['path'], value=data['id'])

                with ForEach(options):
                    with Column(gap=2):
                        Text(ITEM.name, align='center')
                        with Row(gap=2):
                            with If(ITEM.view == 'Histo'):
                                BarChart(data=ITEM.data, series=[ChartSeries(data_key = 'count', label='Occurrences')], x_axis='value', horizontal=True, showLegend=True)
                            with Elif(ITEM.view == 'Plot'):
                                LineChart(data=ITEM.data, series=[ChartSeries(data_key="y", label="Hull", color='blue'), ChartSeries(data_key="score", label="Score of New Option", color='green')],
                                          x_axis="x", height=500, showLegend=True, showGrid=True)
                                            
                            
                            Button(
                                "×", variant="ghost", size="sm",
                                on_click=PopState(options, INDEX),
                            )
                    
        return app

    ############# Write score to display ###############

    @staticmethod
    def event_options(element_ids):
        spec_data_option = MCPxNeo4j.query_scores(element_ids)
        ret = []

        for spec_data, options in spec_data_option:
            if spec_data['type'] in ['bool', 'int', 'str', 'list', 'dict']:
                ret.append(MCPxNeo4j.histogram_option(spec_data, options))
            elif spec_data['type'] == 'float':
                ret.append(MCPxNeo4j.plot_option(spec_data, options))
        return ret


    @app.tool()
    @staticmethod
    def process_text(text, sep=" "):
        elements = re.split(sep, text)

        found_elements = []
        for m in MCPxNeo4j.members:
            for e in elements:
                if e == m['path']:
                    found_elements.append(m['id'])
                    break
                elif e == m['id']:
                    found_elements.append(e)
                    break

        return MCPxNeo4j.event_options(found_elements)

    #@app.ui()
    @staticmethod
    def show_option_score_text():
        with PrefabApp(mode='dark') as app:
            options = Rx("options")
            with Column(gap=3):

                with Row(gap=10):
                    ta = Textarea(rows=5, placeholder="root.environment.environment.eos-model or 4:f766f605-3643-4f9c-8554-440a213da53a:380")
                    Button("process", variant="outline", 
                           on_click=CallTool(MCPxNeo4j.process_text,
                                             arguments={'text': ta.rx}, 
                                             on_success=AppendState(options, RESULT), on_error=AppendState(options, ERROR)))

                with ForEach(options):
                    with Row(gap=2):
                        with Column(gap=2):
                            with ForEach(ITEM):
                                with Column(gap=2):
                                    Text(ITEM.name, align='center')
                                    
                                    with If(ITEM.view == 'Histo'):
                                        BarChart(data=ITEM.data, series=[ChartSeries(data_key = 'count', label='Occurrences')], x_axis='value', horizontal=True, showLegend=True)
                                    with Elif(ITEM.view == 'Plot'):
                                        LineChart(data=ITEM.data, series=[ChartSeries(data_key="y", label="Hull", color='blue'), ChartSeries(data_key="score", label="Score of New Option", color='green')],
                                                x_axis="x", height=500, showLegend=True, showGrid=True)
                                                
                        Button(
                            "×", variant="ghost", size="sm",
                            on_click=PopState(options, INDEX),
                        )
        return app

    ################ Option Coverage ##############

    @_uses_db
    @staticmethod
    def query_option_coverage(element_id, session = None):
        query = f"""MATCH (sn:SpecificationNode) WHERE elementId(sn) = '{element_id}' AND NOT sn.type IN ['dict', 'list']
MATCH (sn)<-[:IS_SPECIFIED_BY]-(vn:ValueNode)
return sn.name as path, collect(vn.value)
UNION
MATCH p = (sn:SpecificationNode)-[:CONTAINS*]->(s:SpecificationNode) WHERE elementId(sn) = '{element_id}' AND NOT s.type IN ['dict', 'list']
MATCH (s)<-[:IS_SPECIFIED_BY]-(vn:ValueNode)
return reduce(occ=sn.name, n in nodes(p)[1..]|occ+'.'+n.name) as path, collect(vn.value)"""
        result = session.run(query)
        ret = []
        for path, values in result:
            ret.append({'path': path, 'values': values})
        return ret

    @app.tool()
    @staticmethod
    def event_option_coverage(element_id):
        return MCPxNeo4j.query_option_coverage(element_id)

    #@app.ui()
    @staticmethod
    def show_option_coverage():
        with PrefabApp(mode='dark') as app:
            options = Rx("options")
            with Column(gap=3):
                with Combobox(placeholder="Search options", 
                            searchPlaceholder="Filter by path",
                            onChange=[CallTool(MCPxNeo4j.event_option_coverage, 
                                        arguments={"element_id": EVENT}, 
                                        on_success=AppendState(options, RESULT, index=0), 
                                        on_error=AppendState(options, ERROR, index=0))],
                            css_class="w-fit mx-auto",
                            align='center'
                            ):
                    for data in MCPxNeo4j.members:
                        ComboboxOption(data['path'], value=data['id'])

                with ForEach(options):
                        
                    with Row(gap=2):
                        DataTable(
                            columns=[DataTableColumn(key='path', header='Specification Path'),
                                        DataTableColumn(key='values', header='Possible Values')],
                            rows=ITEM
                        )

                        Button(
                            "×", variant="ghost", size="sm",
                            on_click=PopState(options, INDEX),
                        )
                    
        return app

    ################ Combinatorial coverage ###################

    @staticmethod
    def path_ids_map_of_valuenodes(element_ids, session):
        query = f"""MATCH (vn:ValueNode) WHERE elementId(vn) IN {str(element_ids)}
MATCH (root:SpecificationNode) WHERE NOT (root)<-[:CONTAINS]-()
MATCH p=(root)-[:CONTAINS*]->(s:SpecificationNode)<-[:IS_SPECIFIED_BY]-(vn)
WITH vn, reduce(occ="root", n in nodes(p)[1..-1]|occ+'.'+n.name) as path
RETURN collect(elementId(vn)), path"""
        result = session.run(query)
        ret = {}
        for elements_ids, path in result:
            ret[path] = elements_ids

        return ret

    @_uses_db
    @staticmethod
    def query_combinatorial_coverage(element_ids, session = None):
        query = f"""MATCH (vn:ValueNode) WHERE elementId(vn) IN {str(element_ids)}
MATCH (root:ValueNode) WHERE NOT (root)<-[:CONTAINS]-()
MATCH (vn) WHERE (root)-[:CONTAINS*]->(vn) 
WITH collect(vn) AS coverage, root AS _
UNWIND apoc.coll.combinations(coverage, 2) as node_couple
WITH node_couple, count(node_couple) AS weight
CALL apoc.coll.elements(node_couple) YIELD _1n, _2n
return _1n, weight, _2n"""
        result = session.run(query)
        ret = []
        for n1, w, n2 in result:
            ret.append((n1, w, n2))
        
        return ret, MCPxNeo4j.path_ids_map_of_valuenodes(element_ids, session)

    @staticmethod
    def add_element(dic: dict[str, list[tuple[str, float]]], node1, weight, node2):
        node_id = node1.element_id
        if node_id in dic:
            dic[node_id].append((node2.element_id, weight/node1["occurrence"]))
        else:
            dic[node_id] = [(node2.element_id, weight/node1["occurrence"])]

    @app.tool()
    @staticmethod
    def get_combinatorial_coverage(element_ids):
        relations, mapping = MCPxNeo4j.query_combinatorial_coverage(element_ids)
        elements = {}
        for n1, w, n2 in relations:
            MCPxNeo4j.add_element(elements, n1, w, n2)
            MCPxNeo4j.add_element(elements, n2, w, n1)

        return {"elements": elements, "mapping": mapping}

    @app.tool()
    @staticmethod
    def process_text_combinatorial_coverage(text, sep = " "):
        elements = re.split(sep, text)
        return MCPxNeo4j.get_combinatorial_coverage([MCPxNeo4j.db_identifier + e for e in elements])

    #@app.ui()
    @staticmethod
    def show_combinatorial_coverage():
        with PrefabApp(mode='dark') as app:
            #options = Rx("options", [])
            heat_data = Rx("data")
            is_process = Rx("process")
            with Column(gap=3):
                with Row(gap=10):
                    ta = Textarea(rows=5, placeholder="root.environment.environment.eos-model or 4:f766f605-3643-4f9c-8554-440a213da53a:380")
                    Button("process", variant="outline", 
                            on_click=[
                                SetState(is_process, True),
                                CallTool(MCPxNeo4j.process_text_combinatorial_coverage,
                                         arguments={'text': ta.rx}, 
                                         on_success=SetState(heat_data, RESULT), on_error=SetState(heat_data, ERROR))])

                    '''
                    with Combobox(placeholder="Search options", 
                                searchPlaceholder="Filter by path",
                                onChange=[AppendState(options, EVENT)],
                                css_class="w-fit mx-auto",
                                align='center'
                                ):
                        for data in MCPxNeo4j.members:
                            ComboboxOption(data['path'])
                    

                    Button("process", variant="outline", 
                           on_click=[SetState(is_process, True), 
                                     CallTool(MCPxNeo4j.get_combinatorial_coverage,
                                              arguments = {"paths": options},
                                              on_success = SetState(heat_data, RESULT),
                                              on_error = SetState(heat_data, ERROR))])
                
                with Grid(columns=3): #TODO maybe let elements place themselves next to one another and wrapping at end of screen IF POSSIBLE
                    with ForEach(options):
                        with Row(gap=1):
                            Text(ITEM)
                            Button("×", variant="ghost", size="sm", on_click=PopState(options, INDEX))'''

                
                    
                with If(is_process):
                    #Text(heat_data)
                    
                    with Row(gap = 1):
                        with Column(gap = 2):
                            H2("Heat Map", align='center')
                            with Row(gap = 2):
                                with Grid(columns=Responsive(), gap=0):
                                    pass

                                Div(css_class="w-10 border", style={
                                    "background": "linear-gradient(to top, #00FF00 0%, #FF0000 100%)"
                                })


                                '''
                                size = 11
                                colors = ["#5BCEFA", "#F5A9B8", "#FFFFFF", "#F5A9B8", "#5BCEFA"]
                                specs = [str(i) for i in range(size-1)]
                                with Grid(columns=size, gap=0, align="center"):
                                    for i in range(size):
                                        color = colors[(i-1)//2]
                                        for j in range(size):
                                            if i == 0 or j == 0:
                                                with Div(css_class=f"h-10 border items-center", style={"background-color": "black"}):
                                                    if i==0 and j>0:
                                                        P(specs[j-1], align='center')
                                                    elif j==0 and i>0:
                                                        P(specs[i-1], align='center')
                                            else:
                                                Div(css_class=f"h-10 border", style={"background-color": color})

                                Div(css_class="w-10 border", style={
                                    "background": "linear-gradient(to top, #5BCEFA 0%, #F5A9B8 30%, #FFFFFF 50%, #F5A9B8 70%, #5BCEFA 100%)"
                                })'''

                                

                        Button("×", variant="ghost", size="sm", on_click=SetState(is_process, False))
                                

        return app


MCPxNeo4j.set_members()
mcp = FastMCP("Panoramix Server", providers=[MCPxNeo4j.app])