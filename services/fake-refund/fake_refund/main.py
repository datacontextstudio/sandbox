from fake_refund.server import mcp

if __name__ == "__main__":
    mcp.run(transport="sse")
