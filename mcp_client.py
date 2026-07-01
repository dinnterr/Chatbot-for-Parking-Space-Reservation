from fastmcp import Client

mcpClient = Client("mcp_textlog.py")

async def log_reservation_mcp(data, api_key):
    async with mcpClient:
        print("[MCP CLIENT] Connected.")
        print(f"[MCP CLIENT] Calling tool 'log_reservation' with data: {data}")
        result = await mcpClient.call_tool(
            "log_reservation",
            {
                "reservation": data,
                "api_key": api_key,
            },
        )
        print(f"[MCP CLIENT] Tool returned: {result}")
        print("[MCP CLIENT] Connection closed.")
    return result.content[0].text