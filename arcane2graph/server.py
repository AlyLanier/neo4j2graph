from collections import Counter
from neo4j import GraphDatabase
from data_hull import ChartDataMaker

from prefab_ui.app import PrefabApp
from prefab_ui.components import Button, Column, ForEach, Slider, Input, Muted, Row, Text, DataTable, DataTableColumn, Grid, Combobox, ComboboxOption, Label
from prefab_ui.actions import AppendState, PopState, SetState
from prefab_ui.rx import Rx

from prefab_ui.components.charts import LineChart, BarChart, ChartSeries
from fastmcp import FastMCP
from fastmcp.tools import tool

import functools
import plotille

class MCPxNeo4j:
    def __init__(self, uri, auth):
        self.uri = uri
        self.auth = auth


##################### getters #####################

    def get_uri(self):
        return self.uri

    def get_auth(self):
        return self.auth


#################### decorator for using neo4j ###################

    def _uses_db(func):
        @functools.wraps(func)
        def connexion_manager(self, *args, **kwargs):
            with GraphDatabase.driver(self.get_uri(), auth=self.get_auth()) as driver:
                driver.verify_connectivity()
                with driver.session(database=self.get_auth()[0]) as session:
                    return func(self, session, *args, **kwargs)

        return connexion_manager

################### functions to retrieve data from neo4j ##################

    @_uses_db
    def query_specs(self, session):
        members = []
        query = """match (root:SpecificationNode) where not (root)<-[:CONTAINS]-()
match p=(root)-[:CONTAINS*]->(s:SpecificationNode)
with reduce(occ="root", n in nodes(p)[1..]|occ+'.'+n.name) as path, s as spec
return spec.name, spec.type, path, elementId(spec)"""
        result = session.run(query)
        for n, t, p, uri in result:
            members.append({'name': n, 'type': t, 'path': p, 'id': uri})
        return members

    def query_spec(self, session, element_id):
        query = f"""match (s:SpecificationNode) where elementId(s) = '{element_id}'
match p=(root)-[:CONTAINS*]->(s) where not (root)<-[:CONTAINS]-()
with reduce(occ="root", n in nodes(p)[1..]|occ+'.'+n.name) as path, s

return s.name, path, s.type, s.occurrence""" #, a.range        optional match (a:AnnotationNode) where (a)-[:ANNOTATES]->(s)
        result = session.run(query).single()
        spec_name, spec_path, spec_type, spec_occ = result #, spec_range
        return {'name': spec_name, 'path': spec_path, 'type': spec_type, 'occurrence': spec_occ, 'range': None} #spec_range

    def query_values_of_spec(self, session, element_id):
        query = f"""match (s:SpecificationNode) where elementId(s) = '{element_id}'
match (vn:ValueNode) where (s)<-[:IS_SPECIFIED_BY]-(vn)
return vn.value, vn.occurrence"""
        result = session.run(query)
        ret = {}
        for value, occurrences in result:
            ret[value] = occurrences
        return ret

    @_uses_db
    def query_score(self, session, element_id):
        spec_data = self.query_spec(session, element_id)
        option = self.query_values_of_spec(session, element_id)
        
            

        
        a = """
        option = {
            .1: 13,
            2.5: 37,
            4.45: 2,
            4.7: 3,
            6: 17,
            7.5: 5,
            7.9: 6,
            8.33: 2,
            10.55: 35
        }"""

        return spec_data, option



#################### mcp tools ####################

    @tool
    def show_specs(self) -> PrefabApp:
        members = self.query_specs()
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

    def plot_as_string(self, x, y, x_score, score, x_of_values, score_of_values):
        fig = plotille.Figure()
        fig.width = 200
        fig.height = 20
        fig.set_x_limits(x[0], x[-1])
        fig.set_y_limits(0., max(y)*1.05)
        fig.plot(x, y, lc='cyan', label='Hull')
        fig.plot(x_score, score, lc='green', label='Score new options')
        fig.scatter(x_of_values, score_of_values, lc='red', label='Score old option')
        print(fig.show(True))

    def histogram_option(self, spec_data, options_data):
        print('HISTO')
        nb_occ_data = sum(options_data.values())
        if spec_data['occurrence'] != nb_occ_data:
            options_data['undefined'] = 1#spec_data['occurrence'] - nb_occ_data

        data = [{'value': value, 'count': occ} for value, occ in options_data.items()]

        with Grid(columns=[1], gap=4) as grid:
            BarChart(
                data=data,
                series=[ChartSeries(dataKey='count', label='Occurrence Count')],
                x_axis='value',
                showLegend=True
            )
        return grid

    def plot_option(self, spec_data, options_data):
        print('PLOT')
        sign = lambda x: 1. if x >= 0 else -1.
        power = lambda n: (lambda x: abs(x)**n, lambda a: (lambda x: sign(x)*a**n * abs(x)**(n+1)/(n+1)))
        distance_function = power(2)

        print('before')
        print(options_data)
        data_maker = ChartDataMaker(options_data, spec_data['range'], *distance_function)
        print('after')
        data = data_maker.generate_data(1000, True)
        self.plot_as_string(*data)

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

        with Grid(columns=[1], gap=4) as grid:
            LineChart(
                data=graph_data,
                series=[ChartSeries(data_key="y", label="Hull", color='blue'),
                        ChartSeries(data_key="score", label="Score of New Option", color='green')],
                x_axis="x",
                height=500,
                showLegend=True,
                showGrid=True,
            )
        return grid

    def event_option(self, element_id):
        spec_data, options = self.query_score(element_id)
        print(spec_data)
        print(options)
    
        if spec_data['type'] in ['bool', 'int', 'str']:
            return self.histogram_option(spec_data, options)
        elif spec_data['type'] == 'float':
            return self.plot_option(spec_data, options)


    @tool
    def show_option_score(self) -> PrefabApp:
        members = self.query_specs()
        with PrefabApp(mode='dark') as app:
            options = Rx("options")
            #print(options.key, options.prec)
            #test = Rx(lambda x: self.event_option(x))
            for spec in members:
                with Row(gap = 2):
                    data = self.event_option(spec['id'])
                    AppendState(options, data)

                    Button(
                        "Delete", variant="ghost", size="sm",
                        on_click=PopState(options, "{{$index}}"),
                    )
            
        return app
    ############################

    

if __name__ == '__main__':

    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")
    mcp = FastMCP("My First App")

    test = MCPxNeo4j(URI, auth=AUTH)
    test.event_option('4:f766f605-3643-4f9c-8554-440a213da53a:89')


else:

    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")
    mcp = FastMCP("My First App")

    test = MCPxNeo4j(URI, auth=AUTH)

    #mcp.add_tool(test.show_specs)
    mcp.add_tool(test.show_option_score)