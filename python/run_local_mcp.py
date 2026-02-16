from mcp import ClientSession
from mcp.server.fastmcp import FastMCP
from mcp.client.streamable_http import streamable_http_client
from threading import Thread

import asyncio
import json
import ollama
import time

"""
This class runs a simple implementation of MCP Server on localhost 
which any MCP client can connect to.

We verify the connection through a simple MCP client as well as
using an LLM running in local through Ollama.

The Ollama demonstration aims to show how a specific tool of an MCP 
server is selected and then used to return the final response of LLM.
"""


class MCPServer:
    def __init__(self, name="Simple MCP Server"):
        self.name = name

    def run(self):
        mcp = FastMCP(self.name, log_level="CRITICAL")

        @mcp.tool()
        def add(a: int, b: int) -> int:
            return a + b

        @mcp.tool()
        def multiply(a: int, b: int) -> int:
            return a * b

        mcp.run(transport="streamable-http")

    def run_as_daemon_thread(self):
        print("\n=== MCP Server ===")
        daemon_thread = Thread(target=self.run, daemon=True)
        daemon_thread.start()


class Client:
    def __init__(self, config_file="mcp.json"):
        try:
            with open(config_file) as f:
                self.servers = json.load(f)["servers"]
        except FileNotFoundError:
            config_dict = {"servers": {"calculator": {"url": "http://localhost:8000/mcp"}}}
            self.servers = config_dict["servers"]

    async def connect_using_mcp_client(self, server, tool, args):
        print("\n=== Direct MCP Client ===")
        print(f"MCP Server: {server}, tool: {tool}, args: {args}")

        server_url = self.servers[server]["url"]

        async with streamable_http_client(server_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments=args)
                print("Result:", result.content[0].text)

    async def connect_using_ollama_chat(self, model, prompt):
        print("\n=== Ollama Chat + MCP ===")
        print("Prompt: ", prompt)

        server_url = self.servers["calculator"]["url"]

        async with streamable_http_client(server_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()

                initial_resp = ollama_chat_with_tools(model=model,
                                                      messages=[{"role": "user", "content": prompt}],
                                                      tools=tools)

                if "tool_calls" in initial_resp:
                    tool_name = initial_resp["tool_calls"][0]["function"]["name"]
                    tool_args = initial_resp["tool_calls"][0]["function"]["arguments"]
                    tool_output = await session.call_tool(tool_name, arguments=tool_args)

                    final_resp = ollama_chat(
                        model=model,
                        messages=[
                            {"role": "user", "content": prompt},
                            initial_resp,
                            {"role": "tool", "name": tool_name, "content": str(tool_output)}
                        ]
                    )

                    print("Tool used: ", tool_name)
                    print("Result:", final_resp["content"])

                else:
                    print("Model answered without using tool")
                    print("Result:", initial_resp["content"])


def ollama_chat(model, messages):
    resp = ollama.chat(model=model, messages=messages)
    return resp["message"]


def ollama_chat_with_tools(model, messages, tools):
    mcp_server_tools = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema,
            },
        }
        for t in tools.tools
    ]

    resp = ollama.chat(model=model, messages=messages, tools=mcp_server_tools)
    return resp["message"]


if __name__ == '__main__':
    server = MCPServer()
    server.run_as_daemon_thread()

    print("Waiting for MCP server to be healthy..")
    time.sleep(10)

    client = Client()
    asyncio.run(client.connect_using_mcp_client("calculator", "add", {"a": 2, "b": 3}))
    asyncio.run(client.connect_using_ollama_chat("functiongemma", "Multiply 2 and 3"))
