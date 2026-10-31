"""The connector over HTTP with sign-in: what a company deployment would need to prove.

The first group runs the HTTP app in-process and walks through each OAuth step by
hand, so every refusal can be checked on its own. The second group starts the real
server as a subprocess (python -m fjordvik_mcp --http) and signs in as each demo
role, then calls the tools as a Claude client would."""

import asyncio
import base64
import hashlib
import os
import secrets
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx2
import pytest
from mcp import Client
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import AuthorizationCodeResult, OAuthClientMetadata

from fjordvik_mcp.auth import ROLES, SCOPE
from fjordvik_mcp.server import build_server, http_security

REPO = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8765"
CALLBACK = "http://127.0.0.1:9/callback"   # never contacted: the code is read from the redirect
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
INITIALIZE = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                         "clientInfo": {"name": "test", "version": "1"}}}


def run(coro):
    return asyncio.run(coro)


def challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")


async def register(http) -> str:
    r = await http.post("/register", json={
        "redirect_uris": [CALLBACK], "client_name": "Fjordvik test client",
        "token_endpoint_auth_method": "none", "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"], "scope": SCOPE})
    assert r.status_code == 201, r.text
    return r.json()["client_id"]


async def get_code(http, client_id: str, role: str, verifier: str, base: str = URL) -> str:
    """/authorize, then the sign-in page, then the redirect back with the code."""
    r = await http.get("/authorize", params={
        "response_type": "code", "client_id": client_id, "redirect_uri": CALLBACK,
        "code_challenge": challenge(verifier), "code_challenge_method": "S256",
        "state": "s1", "scope": SCOPE, "resource": f"{base}/mcp"})
    assert r.status_code == 302, r.text
    login = urlparse(r.headers["location"])
    request_id = parse_qs(login.query)["request"][0]
    page = await http.get(f"/login?{login.query}")
    assert page.status_code == 200
    r = await http.post("/login", data={"request": request_id, "role": role})
    assert r.status_code == 302, r.text
    back = parse_qs(urlparse(r.headers["location"]).query)
    assert back["state"] == ["s1"]
    return back["code"][0]


async def exchange(http, client_id: str, code: str, verifier: str, base: str = URL):
    return await http.post("/token", data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": CALLBACK,
        "client_id": client_id, "code_verifier": verifier, "resource": f"{base}/mcp"})


async def sign_in(http, role: str, base: str = URL) -> str:
    client_id = await register(http)
    verifier = secrets.token_urlsafe(48)
    code = await get_code(http, client_id, role, verifier, base)
    r = await exchange(http, client_id, code, verifier, base)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@asynccontextmanager
async def in_process(wh):
    """The HTTP app with its lifespan running, called through httpx2 without a network."""
    server = build_server(wh, http_url=URL)
    app = server.streamable_http_app(transport_security=http_security(8765))
    async with app.router.lifespan_context(app):
        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url=URL) as http:
            yield http, server._auth_server_provider


# In-process: each step of the sign-in, and each refusal.

def test_no_token_is_refused_with_a_pointer_to_the_metadata(wh):
    async def go():
        async with in_process(wh) as (http, _):
            return await http.post("/mcp", json=INITIALIZE, headers=MCP_HEADERS)
    r = run(go())
    assert r.status_code == 401
    assert f"{URL}/.well-known/oauth-protected-resource/mcp" in r.headers["www-authenticate"]


def test_discovery_documents_name_the_server_and_pkce(wh):
    async def go():
        async with in_process(wh) as (http, _):
            return (await http.get("/.well-known/oauth-protected-resource/mcp")).json(), \
                   (await http.get("/.well-known/oauth-authorization-server")).json()
    resource, server = run(go())
    assert resource["resource"] == f"{URL}/mcp"
    assert [a.rstrip("/") for a in resource["authorization_servers"]] == [URL]
    assert server["code_challenge_methods_supported"] == ["S256"]
    assert server["registration_endpoint"] == f"{URL}/register"


def test_sign_in_page_lists_the_four_roles_and_asks_for_no_password(wh):
    async def go():
        async with in_process(wh) as (http, _):
            client_id = await register(http)
            r = await http.get("/authorize", params={
                "response_type": "code", "client_id": client_id, "redirect_uri": CALLBACK,
                "code_challenge": challenge("v" * 50), "code_challenge_method": "S256"})
            return (await http.get(r.headers["location"])).text
    page = run(go())
    for role in ROLES.values():
        assert role.name in page
    assert "password" not in page.split("Demo sign-in")[0].lower()


def test_full_sign_in_gives_a_one_hour_token_carrying_the_role(wh):
    async def go():
        async with in_process(wh) as (http, provider):
            token = await sign_in(http, "nordics_sales_manager")
            ok = await http.post("/mcp", json=INITIALIZE,
                                 headers={**MCP_HEADERS, "Authorization": f"Bearer {token}"})
            return provider.access_tokens[token], ok
    access, ok = run(go())
    assert access.subject == "nordics_sales_manager"
    assert access.resource == f"{URL}/mcp"
    assert 3590 < access.expires_at - time.time() <= 3600
    assert ok.status_code == 200


def test_wrong_code_verifier_is_refused(wh):
    """PKCE: a stolen code is useless without the verifier only the client holds."""
    async def go():
        async with in_process(wh) as (http, _):
            client_id = await register(http)
            code = await get_code(http, client_id, "group_analyst", secrets.token_urlsafe(48))
            return await exchange(http, client_id, code, secrets.token_urlsafe(48))
    r = run(go())
    assert r.status_code == 400 and r.json()["error"] == "invalid_grant"


def test_a_code_works_once(wh):
    async def go():
        async with in_process(wh) as (http, _):
            client_id = await register(http)
            verifier = secrets.token_urlsafe(48)
            code = await get_code(http, client_id, "group_analyst", verifier)
            return (await exchange(http, client_id, code, verifier),
                    await exchange(http, client_id, code, verifier))
    first, second = run(go())
    assert first.status_code == 200
    assert second.status_code == 400 and second.json()["error"] == "invalid_grant"


def test_an_unregistered_redirect_address_is_refused(wh):
    """A code is never sent to an address the client did not register."""
    async def go():
        async with in_process(wh) as (http, _):
            client_id = await register(http)
            return await http.get("/authorize", params={
                "response_type": "code", "client_id": client_id,
                "redirect_uri": "http://attacker.example/steal",
                "code_challenge": challenge("v" * 50), "code_challenge_method": "S256"})
    r = run(go())
    assert r.status_code == 400
    assert "attacker.example" not in r.headers.get("location", "")


def test_a_sign_in_page_can_be_used_once_and_only_for_a_known_role(wh):
    async def go():
        async with in_process(wh) as (http, _):
            client_id = await register(http)
            r = await http.get("/authorize", params={
                "response_type": "code", "client_id": client_id, "redirect_uri": CALLBACK,
                "code_challenge": challenge("v" * 50), "code_challenge_method": "S256"})
            request_id = parse_qs(urlparse(r.headers["location"]).query)["request"][0]
            unknown = await http.post("/login", data={"request": request_id, "role": "admin"})
            first = await http.post("/login", data={"request": request_id, "role": "group_analyst"})
            again = await http.post("/login", data={"request": request_id, "role": "group_analyst"})
            return unknown, first, again
    unknown, first, again = run(go())
    assert unknown.status_code == 400
    assert first.status_code == 302
    assert again.status_code == 400


def test_an_expired_token_is_refused(wh):
    async def go():
        async with in_process(wh) as (http, provider):
            token = await sign_in(http, "group_analyst")
            provider.access_tokens[token].expires_at = int(time.time()) - 1
            return await http.post("/mcp", json=INITIALIZE,
                                   headers={**MCP_HEADERS, "Authorization": f"Bearer {token}"})
    assert run(go()).status_code == 401


def test_a_token_issued_for_another_server_is_refused(wh):
    """The token names the server it is for (its resource); this server takes only its own."""
    async def go():
        async with in_process(wh) as (http, provider):
            token = await sign_in(http, "group_analyst")
            provider.access_tokens[token].resource = "http://127.0.0.1:9999/mcp"
            return await http.post("/mcp", json=INITIALIZE,
                                   headers={**MCP_HEADERS, "Authorization": f"Bearer {token}"})
    assert run(go()).status_code == 401


def test_a_request_naming_another_host_is_refused(wh):
    """DNS rebinding protection: a web page elsewhere cannot reach the local server."""
    async def go():
        async with in_process(wh) as (http, _):
            token = await sign_in(http, "group_analyst")
            return await http.post("/mcp", json=INITIALIZE, headers={
                **MCP_HEADERS, "Authorization": f"Bearer {token}", "Host": "evil.example"})
    assert run(go()).status_code in (400, 403, 421)


# The real server, as a subprocess: each role calls the tools.

def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live():
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [sys.executable, "-m", "fjordvik_mcp", "--http", "--port", str(port)], cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
        # Not a pipe: nobody reads it, so a full pipe would stall the server's request log.
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(120):
            try:
                if httpx2.get(f"{base}/.well-known/oauth-authorization-server").status_code == 200:
                    break
            except httpx2.TransportError:
                time.sleep(0.25)
        else:
            pytest.fail("the HTTP server did not start")
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


CALLS = {
    "describe_dataset": {},
    "emissions_total": {"year": 2025},
    "emissions_intensity": {"per": "fte", "year": 2025},
    "scope3_inventory": {"year": 2025},
    "sales_summary": {"group_by": ["region"], "year": 2025},
    "data_quality_report": {},
    "run_sql": {"query": "SELECT count(*) AS n FROM fact_sales"},
}


async def as_role(base: str, role: str, calls: list[tuple[str, dict]]):
    async with httpx2.AsyncClient(base_url=base) as http:
        token = await sign_in(http, role, base)
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx2.AsyncClient(headers=headers, timeout=30) as authed:
        async with Client(streamable_http_client(f"{base}/mcp", http_client=authed)) as c:
            return [await c.call_tool(name, args) for name, args in calls]


@pytest.mark.parametrize("role_id", list(ROLES))
def test_each_role_can_use_exactly_its_tools(live, role_id):
    results = run(as_role(live, role_id, list(CALLS.items())))
    for (name, _), res in zip(CALLS.items(), results):
        if name in ROLES[role_id].tools:
            assert not res.is_error, (role_id, name, res.content)
        else:
            assert res.is_error, (role_id, name)
            assert "not available to this role" in res.content[0].text


def test_a_region_manager_sees_only_their_region(live):
    analyst, = run(as_role(live, "group_analyst", [("sales_summary", CALLS["sales_summary"])]))
    nordics, other = run(as_role(live, "nordics_sales_manager", [
        ("sales_summary", CALLS["sales_summary"]),
        ("sales_summary", {"region_id": "WEU", "year": 2025})]))
    all_regions = {r["region_id"]: r for r in analyst.structured_content["rows"]}
    rows = nordics.structured_content["rows"]
    assert len(all_regions) == 4
    assert [r["region_id"] for r in rows] == ["NOR"]
    assert rows[0]["net_sales_eur"] == all_regions["NOR"]["net_sales_eur"]
    assert other.is_error and "only region NOR" in other.content[0].text


def test_the_sdk_client_signs_in_on_its_own(live):
    """The flow a Claude client runs: discover, register, PKCE, sign in, token, tools.
    The browser step is played by a small handler that picks a role on the page."""
    page_role = "sustainability_reviewer"
    redirected: dict[str, str] = {}

    async def redirect_handler(url: str) -> None:
        async with httpx2.AsyncClient() as http:
            r = await http.get(url)
            login = urlparse(r.headers["location"])
            request_id = parse_qs(login.query)["request"][0]
            r = await http.post(f"{live}/login", data={"request": request_id, "role": page_role})
            redirected.update({k: v[0] for k, v in parse_qs(urlparse(r.headers["location"]).query).items()})

    async def callback_handler() -> AuthorizationCodeResult:
        return AuthorizationCodeResult(code=redirected["code"], state=redirected.get("state"))

    class Memory:
        tokens = client = None
        async def get_tokens(self): return self.tokens
        async def set_tokens(self, tokens): self.tokens = tokens
        async def get_client_info(self): return self.client
        async def set_client_info(self, info): self.client = info

    async def go():
        oauth = OAuthClientProvider(
            server_url=f"{live}/mcp",
            client_metadata=OAuthClientMetadata(
                client_name="Fjordvik test", redirect_uris=[CALLBACK],
                grant_types=["authorization_code", "refresh_token"], response_types=["code"],
                scope=SCOPE, token_endpoint_auth_method="none"),
            storage=Memory(), redirect_handler=redirect_handler, callback_handler=callback_handler)
        async with httpx2.AsyncClient(auth=oauth, timeout=30) as http:
            async with Client(streamable_http_client(f"{live}/mcp", http_client=http)) as c:
                return (await c.call_tool("scope3_inventory", {"year": 2025}),
                        await c.call_tool("sales_summary", {}))
    scope3, sales = run(go())
    assert not scope3.is_error
    assert sales.is_error and "Sustainability reviewer" in sales.content[0].text
