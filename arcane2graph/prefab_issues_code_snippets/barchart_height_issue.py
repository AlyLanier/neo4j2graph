
from prefab_ui.app import PrefabApp
from prefab_ui.components import Button, Column, ForEach, Row, Combobox, ComboboxOption
from prefab_ui.actions import AppendState, PopState
from prefab_ui.rx import Rx, RESULT, ERROR, ITEM
from prefab_ui.actions.mcp import CallTool

from prefab_ui.components.charts import BarChart, ChartSeries
from fastmcp import FastMCP, FastMCPApp

class MCPxNeo4j:
    app = FastMCPApp("MyFirstApp")

    @staticmethod
    def query_specs():
        return [{'path': 'hello', 'id': 'some_id'}, {'path': 'world', 'id': 'some_other_id'}]

    @app.tool()
    @staticmethod
    def event_option(element_id):
        data = {'some_id': [{'value': 'True', 'count': 13}, {'value': 'False', 'count': 3}],
                'some_other_id': [{'value': x, 'count': 2*x} for x in range(10)]}
        return data[element_id]

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
                                        on_success=AppendState(options, RESULT), 
                                        on_error=AppendState(options, ERROR))],
                            css_class="w-fit mx-auto",
                            align='center'
                            ):
                    for data in members:
                        ComboboxOption(data['path'], value=data['id'])

                with ForEach(options):
                    with Row(gap=2):

                        BarChart(data=ITEM, series=[ChartSeries(data_key = 'count', label='Occurrences')], x_axis='value', height=100, horizontal=True, showLegend=True)
                        
                        Button(
                            "×", variant="ghost", size="sm",
                            on_click=PopState(options, "{{ $index }}"),
                        )
                    
        return app            

    ############################


mcp = FastMCP("Snippet Server", providers=[MCPxNeo4j.app])