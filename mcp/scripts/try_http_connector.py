"""Sign in to the Fjordvik connector over HTTP and see what your role can do.

Start the server first, in another terminal, from the mcp folder:

    .venv\\Scripts\\python -m fjordvik_mcp --http

Then run this script:

    .venv\\Scripts\\python scripts\\try_http_connector.py

It does what a Claude client does when you add a connector that needs sign-in:
finds the server's sign-in details, registers itself, opens your browser on the
Fjordvik sign-in page, waits for you to pick a role, swaps the code for a token,
then calls three tools and prints what that role gets back. Run it again and pick
another role to compare. Tokens stay in memory and are never printed.
"""

import argparse
import asyncio
import webbrowser
from urllib.parse import parse_qs, urlparse

import httpx2
from mcp import Client
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import AuthorizationCodeResult, OAuthClientMetadata

SCOPE = "fjordvik.read"
DONE_PAGE = (b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n"
             b"<!doctype html><title>Signed in</title><p style='font-family:sans-serif'>"
             b"Signed in. You can close this tab and go back to the terminal.</p>")


class MemoryStorage:
    """Where the client keeps its registration and tokens: memory only, gone on exit."""

    def __init__(self):
        self.tokens = self.client_info = None

    async def get_tokens(self):
        return self.tokens

    async def set_tokens(self, tokens):
        self.tokens = tokens

    async def get_client_info(self):
        return self.client_info

    async def set_client_info(self, client_info):
        self.client_info = client_info


class BrowserSignIn:
    """Opens the sign-in page and waits on a one-off local address for the code."""

    def __init__(self, callback_port: int, open_browser: bool):
        self.port, self.open_browser = callback_port, open_browser
        self.redirect_uri = f"http://127.0.0.1:{callback_port}/callback"
        self.result: asyncio.Future | None = None
        self.listener = None

    async def redirect_handler(self, url: str) -> None:
        self.result = asyncio.get_running_loop().create_future()
        self.listener = await asyncio.start_server(self._receive, "127.0.0.1", self.port)
        print("\nSign in here (your browser should open it):\n" + url + "\n", flush=True)
        if self.open_browser:
            webbrowser.open(url)

    async def callback_handler(self) -> AuthorizationCodeResult:
        try:
            query = await asyncio.wait_for(self.result, timeout=300)
        finally:
            self.listener.close()
        return AuthorizationCodeResult(code=query["code"][0], state=(query.get("state") or [None])[0])

    async def _receive(self, reader, writer):
        request_line = (await reader.readline()).decode("latin-1")
        while (await reader.readline()) not in (b"\r\n", b""):
            pass
        query = parse_qs(urlparse(request_line.split()[1]).query) if request_line else {}
        writer.write(DONE_PAGE)
        await writer.drain()
        writer.close()
        if "code" in query and not self.result.done():
            self.result.set_result(query)


def show(name: str, result) -> None:
    if result.is_error:
        print(f"  {name}: refused. {result.content[0].text}")
        return
    data = result.structured_content or {}
    if name == "describe_dataset":
        period = data.get("period", {})
        print(f"  {name}: {len(data.get('sites', []))} sites, "
              f"{period.get('first_month')} to {period.get('last_month')}")
    elif name == "sales_summary":
        for row in data.get("rows", []):
            print(f"  {name}: {row['region_name']} 2025 net sales EUR {row['net_sales_eur']:,.2f}")
    else:
        print(f"  {name}: {data.get('rows')}")


async def main(server: str, callback_port: int, open_browser: bool) -> None:
    sign_in = BrowserSignIn(callback_port, open_browser)
    oauth = OAuthClientProvider(
        server_url=server,
        client_metadata=OAuthClientMetadata(
            client_name="Fjordvik try-it script", redirect_uris=[sign_in.redirect_uri],
            grant_types=["authorization_code", "refresh_token"], response_types=["code"],
            scope=SCOPE, token_endpoint_auth_method="none"),
        storage=MemoryStorage(), redirect_handler=sign_in.redirect_handler,
        callback_handler=sign_in.callback_handler)
    async with httpx2.AsyncClient(auth=oauth, timeout=60) as http:
        async with Client(streamable_http_client(server, http_client=http)) as client:
            print("Signed in. What this role gets back:")
            show("describe_dataset", await client.call_tool("describe_dataset", {}))
            show("sales_summary", await client.call_tool(
                "sales_summary", {"group_by": ["region"], "year": 2025}))
            show("run_sql", await client.call_tool(
                "run_sql", {"query": "SELECT count(*) AS sales_rows FROM fact_sales"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--server", default="http://127.0.0.1:8765/mcp")
    parser.add_argument("--callback-port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true",
                        help="print the sign-in address instead of opening the browser")
    args = parser.parse_args()
    asyncio.run(main(args.server, args.callback_port, not args.no_browser))
