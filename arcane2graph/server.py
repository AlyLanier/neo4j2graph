from collections import Counter
from neo4j import GraphDatabase

from prefab_ui.app import PrefabApp
from prefab_ui.components import Column, DataTable, DataTableColumn, Grid
from prefab_ui.components.charts import PieChart
from fastmcp import FastMCP

import functools

class MCPxNeo4j:
    mcp = FastMCP("My First App")

    def __init__(self, uri, auth):
        self.uri = uri
        self.auth = auth

    def get_uri(self):
        return self.uri

    def get_auth(self):
        return self.auth

    def _uses_db(func):
        @functools.wraps(func)
        def connexion_manager(self, *args, **kwargs):
            with GraphDatabase.driver(self.get_uri(), auth=self.get_auth()) as driver:
                with driver.session(database=self.get_auth()[0]) as session:
                    func(self, session, *args, **kwargs)

        return connexion_manager


    @mcp.tool(app=True)
    @_uses_db
    def specs(self, session) -> PrefabApp:
        members = []
        query = 'MATCH (n:SpecificationNode) RETURN n.name as name, n.type as type'
        result = session.run(query)
        for n, t in result:
            members.append({'name': n, 'type': t})

        with PrefabApp(mode='dark') as app:
            with Column(gap=4, css_class="p-6"):
                with Grid(columns=[1], gap=4):
                    DataTable(
                        columns=[
                            DataTableColumn(key="name", header="Name", sortable=True),
                            DataTableColumn(key="role", header="Role", sortable=True),
                            DataTableColumn(key="office", header="Office", sortable=True),
                        ],
                        rows=members,
                        search=True,
                    )

        
        





    @mcp.tool(app=True)
    def team_directory() -> PrefabApp:
        """Browse the team directory."""
        members = [
            {"name": "Alice Chen", "role": "Staff Engineer", "office": "San Francisco"},
            {"name": "Bob Martinez", "role": "Lead Designer", "office": "New York"},
            {"name": "Carol Johnson", "role": "Senior Engineer", "office": "London"},
            {"name": "David Kim", "role": "Product Manager", "office": "San Francisco"},
            {"name": "Eva Mueller", "role": "Engineer", "office": "Berlin"},
            {"name": "Frank Lee", "role": "Data Scientist", "office": "San Francisco"},
            {"name": "Grace Park", "role": "Engineering Manager", "office": "New York"},
        ]

        office_counts = [{"office": office, "count": count} for office, count in Counter(m["office"] for m in members).items()]

        with PrefabApp(mode='dark') as app:
            with Column(gap=4, css_class="p-6"):
                with Grid(columns=[1, 2, 1], gap=4):
                    PieChart(
                        data=office_counts,
                        data_key="count",
                        name_key="office",
                        show_legend=True,
                    )
                    DataTable(
                        columns=[
                            DataTableColumn(key="name", header="Name", sortable=True),
                            DataTableColumn(key="role", header="Role", sortable=True),
                            DataTableColumn(key="office", header="Office", sortable=True),
                        ],
                        rows=members,
                        search=True,
                    )
                    PieChart(
                        data=office_counts,
                        data_key="count",
                        name_key="office",
                        show_legend=True,
                    )
            with Column(gap=6, css_class="p-6"):
                with Grid(columns=[1, 2, 1], gap=4):
                    PieChart(
                        data=office_counts,
                        data_key="count",
                        name_key="office",
                        show_legend=True,
                    )
                    DataTable(
                        columns=[
                            DataTableColumn(key="name", header="Name", sortable=True),
                            DataTableColumn(key="role", header="Role", sortable=True),
                            DataTableColumn(key="office", header="Office", sortable=True),
                        ],
                        rows=members,
                        search=True,
                    )
                    PieChart(
                        data=office_counts,
                        data_key="count",
                        name_key="office",
                        show_legend=True,
                    )
        return app

    @mcp.tool(app=True)
    def yaydirectory() -> PrefabApp:
        """Browse the team directory."""
        members = [
            {"name": "Alice Chen", "role": "Staff Engineer", "office": "San Francisco"},
            {"name": "Bob Martinez", "role": "Lead Designer", "office": "New York"},
            {"name": "Carol Johnson", "role": "Senior Engineer", "office": "London"},
            {"name": "David Kim", "role": "Product Manager", "office": "San Francisco"},
            {"name": "Eva Mueller", "role": "Engineer", "office": "Berlin"},
            {"name": "Frank Lee", "role": "Data Scientist", "office": "San Francisco"},
            {"name": "Grace Park", "role": "Engineering Manager", "office": "New York"},
        ]

        office_counts = [{"office": office, "count": count} for office, count in Counter(m["office"] for m in members).items()]

        with PrefabApp(mode='dark') as app:
            with Column(gap=4, css_class="p-6"):
                with Grid(columns=[1, 2, 1], gap=4):
                    PieChart(
                        data=office_counts,
                        data_key="count",
                        name_key="office",
                        show_legend=True,
                    )
                    DataTable(
                        columns=[
                            DataTableColumn(key="name", header="Name", sortable=True),
                            DataTableColumn(key="role", header="Role", sortable=True),
                            DataTableColumn(key="office", header="Office", sortable=True),
                        ],
                        rows=members,
                        search=True,
                    )
                    PieChart(
                        data=office_counts,
                        data_key="count",
                        name_key="office",
                        show_legend=True,
                    )
            with Column(gap=6, css_class="p-6"):
                with Grid(columns=[1, 2, 1], gap=4):
                    PieChart(
                        data=office_counts,
                        data_key="count",
                        name_key="office",
                        show_legend=True,
                    )
                    DataTable(
                        columns=[
                            DataTableColumn(key="name", header="Name", sortable=True),
                            DataTableColumn(key="role", header="Role", sortable=True),
                            DataTableColumn(key="office", header="Office", sortable=True),
                        ],
                        rows=members,
                        search=True,
                    )
                    PieChart(
                        data=office_counts,
                        data_key="count",
                        name_key="office",
                        show_legend=True,
                    )
        return app

if __name__ == '__main__':
    URI = "bolt://localhost:7687"
    AUTH = ("neo4j", "password")
    test = MCPxNeo4j(URI, auth=AUTH)
    test.specs()