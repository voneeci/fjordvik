"""The MCP layer: what Claude sees when it connects.

Most tests use the SDK's in-process client. The last one launches the server as
a real subprocess over stdio, exactly as Claude Desktop does."""

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

from fjordvik_mcp.server import build_server

REPO = Path(__file__).resolve().parents[1]
TOOLS = {"describe_dataset", "emissions_total", "emissions_intensity",
         "scope3_inventory", "sales_summary", "data_quality_report", "run_sql"}


def run(coro):
    return asyncio.run(coro)


def test_tools_are_listed_and_all_read_only(wh):
    async def go():
        async with Client(build_server(wh)) as c:
            return (await c.list_tools()).tools
    tools = run(go())
    assert {t.name for t in tools} == TOOLS
    for t in tools:
        assert t.annotations.read_only_hint is True, t.name
        assert t.annotations.destructive_hint is False, t.name
        assert t.description, t.name


def test_group_by_choices_are_in_the_tool_schema(wh):
    """Claude sees the allowed group_by values, so it rarely sends a wrong one."""
    async def go():
        async with Client(build_server(wh)) as c:
            return {t.name: t for t in (await c.list_tools()).tools}
    schema = json.dumps(run(go())["emissions_total"].input_schema)
    for value in ["year", "month", "site", "country", "scope", "source", "category",
                  "scope3_category", "location", "market"]:
        assert f'"{value}"' in schema


def test_tool_call_returns_structured_content(wh):
    async def go():
        async with Client(build_server(wh)) as c:
            return await c.call_tool("emissions_total", {"group_by": ["scope"], "year": 2025})
    res = run(go())
    assert res.is_error is False
    rows = res.structured_content["rows"]
    assert [r["scope"] for r in rows] == [1, 2, 3]
    assert res.structured_content["unit"] == "tCO2e"


def test_bad_input_returns_a_message_claude_can_act_on(wh):
    async def go():
        async with Client(build_server(wh)) as c:
            return await c.call_tool("emissions_total", {"site_id": "XX99"})
    res = run(go())
    assert res.is_error is True
    text = res.content[0].text
    assert "Unknown site_id" in text and "FI01" in text


def test_refused_sql_explains_why(wh):
    async def go():
        async with Client(build_server(wh)) as c:
            return await c.call_tool("run_sql", {"query": "DROP TABLE dim_site"})
    res = run(go())
    assert res.is_error is True
    assert "Only SELECT" in res.content[0].text


def test_resources_are_readable(wh):
    async def go():
        async with Client(build_server(wh)) as c:
            schema = await c.read_resource("fjordvik://schema")
            source = await c.read_resource("fjordvik://source")
            return schema.contents[0].text, source.contents[0].text
    schema, source = run(go())
    assert "fact_emissions" in schema and "illustrative" in schema
    assert json.loads(source)["tables"]["fact_emissions"]["rows"] == 1422


def test_server_runs_over_stdio_like_claude_desktop():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "fjordvik_mcp"], cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO / "src")})

    async def go():
        async with Client(params) as c:
            tools = {t.name for t in (await c.list_tools()).tools}
            res = await c.call_tool("data_quality_report", {})
            return tools, res
    tools, res = run(go())
    assert tools == TOOLS
    assert res.structured_content["failed"] == 0
