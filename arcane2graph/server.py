from neo4j import GraphDatabase
from data_hull import ChartDataMaker

from prefab_ui.app import PrefabApp
from prefab_ui.components import Button, Column, ForEach, Row, Text, DataTable, DataTableColumn, Grid, Combobox, ComboboxOption, Label, If, Else, Elif
from prefab_ui.actions import AppendState, PopState, SetState
from prefab_ui.rx import Rx, RESULT, ERROR, ITEM
from prefab_ui.actions.mcp import CallTool

from prefab_ui.components.charts import LineChart, BarChart, ChartSeries
from fastmcp import FastMCP, FastMCPApp
from fastmcp.tools import tool

import functools
import plotille


class MCPxNeo4j:

    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")
    app = FastMCPApp("MyFirstApp")

#################### decorator for using neo4j ###################

    def _uses_db(func):
        @functools.wraps(func)
        def connexion_manager(*args, **kwargs):
            with GraphDatabase.driver(uri=MCPxNeo4j.URI, auth=MCPxNeo4j.AUTH) as driver:
                driver.verify_connectivity()
                with driver.session(database=MCPxNeo4j.AUTH[0]) as session:
                    return func(session, *args, **kwargs)

        return connexion_manager

################### functions to retrieve data from neo4j ##################

    @_uses_db
    @staticmethod
    def query_specs(session):
        members = []
        query = """match (root:SpecificationNode) where not (root)<-[:CONTAINS]-()
match p=(root)-[:CONTAINS*]->(s:SpecificationNode)
with reduce(occ="root", n in nodes(p)[1..]|occ+'.'+n.name) as path, s as spec
return spec.name, spec.type, path, elementId(spec)"""
        result = session.run(query)
        for n, t, p, uri in result:
            members.append({'name': n, 'type': t, 'path': p, 'id': uri})
        return members

    @staticmethod
    def query_spec(session, element_id):
        query = f"""match (s:SpecificationNode) where elementId(s) = '{element_id}'
match p=(root)-[:CONTAINS*]->(s) where not (root)<-[:CONTAINS]-()
with reduce(occ="root", n in nodes(p)[1..]|occ+'.'+n.name) as path, s

return s.name, path, s.type, s.occurrence""" #, a.range        optional match (a:AnnotationNode) where (a)-[:ANNOTATES]->(s)
        result = session.run(query).single()
        spec_name, spec_path, spec_type, spec_occ = result #, spec_range
        return {'name': spec_name, 'path': spec_path, 'type': spec_type, 'occurrence': spec_occ, 'range': None} #spec_range

    @staticmethod
    def query_values_of_leaf_spec(session, element_id):
        query = f"""match (s:SpecificationNode) where elementId(s) = '{element_id}'
match (vn:ValueNode) where (s)<-[:IS_SPECIFIED_BY]-(vn)
return vn.value, vn.occurrence"""
        result = session.run(query)
        ret = {}
        for value, occurrences in result:
            ret[value] = occurrences
        return ret

    @staticmethod
    def query_values_of_node_spec(session, element_id):
        query = f"""match (s:SpecificationNode) where elementId(s) = '{element_id}'
match (vn:ValueNode) where (s)<-[:IS_SPECIFIED_BY]-(vn)
return elementId(vn), vn.occurrence"""
        result = session.run(query)
        ret = {}
        for value, occurrences in result:
            ret[value] = occurrences
        return ret

    @_uses_db
    @staticmethod
    def query_score(session, element_id):
        spec_data = MCPxNeo4j.query_spec(session, element_id)
        option = MCPxNeo4j.query_values_of_node_spec(session, element_id) if spec_data['type'] in ['dict', 'list'] else MCPxNeo4j.query_values_of_leaf_spec(session, element_id)

        return spec_data, option



#################### mcp ui objects ####################

    #@app.ui()
    @staticmethod
    def show_specs():
        members = MCPxNeo4j.query_specs()
        with PrefabApp(mode='dark') as app:
            with Column(gap=4, css_class="p-6"):
                with Grid(columns=[1], gap=4):
                    DataTable(
                        columns=[
                            DataTableColumn(key="name", header="Name"),
                            DataTableColumn(key="type", header="Type"),
                            DataTableColumn(key="path", header="Path", sortable=True)
                        ],
                        rows=members,
                        search=True,
                    )
        return app
    ###############################

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
        members = MCPxNeo4j.query_specs()

        with PrefabApp(mode='dark') as app:
            options = Rx("options")
            with Column(gap=3):
                with Combobox(placeholder="Search options", 
                            searchPlaceholder="Filter by path",
                            onChange=[CallTool(MCPxNeo4j.event_option, 
                                        arguments={"element_id": "{{$event}}"}, 
                                        on_success=AppendState(options, RESULT, index=0), 
                                        on_error=AppendState(options, ERROR, index=0))],
                            css_class="w-fit mx-auto",
                            align='center'
                            ):
                    for data in members:
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
                                on_click=PopState(options, "{{ $index }}"),
                            )
                    
        return app

            

    ############################




if __name__ == '__main__':

    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")
    mcp = FastMCP("My First App")

    test = MCPxNeo4j(URI, auth=AUTH)
    test.event_option('4:f766f605-3643-4f9c-8554-440a213da53a:346')


else:
    mcp = FastMCP("Panoramix Server", providers=[MCPxNeo4j.app])