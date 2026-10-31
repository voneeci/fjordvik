"""Sign-in for the HTTP connector: a small OAuth 2.1 authorisation server for a demo.

A company connector would send people to its identity provider (Microsoft Entra ID,
for example) and read their groups from it. Here the sign-in page lets you pick one of
four demo roles instead: no passwords, nothing secret. Everything after the sign-in is
the standard flow that Claude clients use: dynamic client registration, an authorisation
code protected by PKCE (Proof Key for Code Exchange), then an access token that expires
after an hour. The MCP SDK checks the PKCE verifier, the redirect address and the code's
expiry; this module stores the clients, codes and tokens, in memory only.
"""

import html
import secrets
import time
from dataclasses import dataclass

from mcp.server.auth.provider import (AccessToken, AuthorizationCode, AuthorizationParams,
                                      RefreshToken, construct_redirect_uri)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

SCOPE = "fjordvik.read"
SIGN_IN_SECONDS = 300      # a sign-in page, and the code it issues, last five minutes
TOKEN_SECONDS = 3600       # an access token lasts an hour
REFRESH_SECONDS = 86400    # a refresh token lasts a day

ALL_TOOLS = frozenset({"describe_dataset", "emissions_total", "emissions_intensity",
                       "scope3_inventory", "sales_summary", "data_quality_report", "run_sql"})
EMISSION_TOOLS = frozenset({"describe_dataset", "emissions_total", "emissions_intensity",
                            "scope3_inventory", "data_quality_report"})
SALES_TOOLS = frozenset({"describe_dataset", "sales_summary"})


@dataclass(frozen=True)
class Role:
    name: str
    tools: frozenset[str]
    region_id: str | None = None   # a sales role sees this region's sales only
    summary: str = ""


# The same split as the Power BI security roles: region managers see their own sales.
# run_sql is for the group analyst only, because free SQL could read around any filter.
ROLES = {
    "group_analyst": Role("Group analyst", ALL_TOOLS,
                          summary="All seven tools and all data."),
    "sustainability_reviewer": Role("Sustainability reviewer", EMISSION_TOOLS,
                                    summary="Emissions, scope 3 and data quality; no sales."),
    "nordics_sales_manager": Role("Nordics sales manager", SALES_TOOLS, "NOR",
                                  summary="Sales for the Nordics only."),
    "western_europe_sales_manager": Role("Western Europe sales manager", SALES_TOOLS, "WEU",
                                         summary="Sales for Western Europe only."),
}


class DemoOAuthProvider:
    """The OAuthAuthorizationServerProvider the MCP SDK calls at each step."""

    def __init__(self, base_url: str, resource_url: str):
        self.base_url = base_url.rstrip("/")
        self.resource_url = resource_url
        self.clients: dict[str, OAuthClientInformationFull] = {}
        self.sign_ins: dict[str, tuple[str, AuthorizationParams, float]] = {}
        self.codes: dict[str, AuthorizationCode] = {}
        self.access_tokens: dict[str, AccessToken] = {}
        self.refresh_tokens: dict[str, RefreshToken] = {}

    # Dynamic client registration: Claude clients register themselves on first use.
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self.clients[client_info.client_id] = client_info

    # /authorize: hold the request and send the browser to the sign-in page.
    async def authorize(self, client: OAuthClientInformationFull,
                        params: AuthorizationParams) -> str:
        request_id = secrets.token_urlsafe(24)
        self.sign_ins[request_id] = (client.client_id, params, time.time() + SIGN_IN_SECONDS)
        return f"{self.base_url}/login?request={request_id}"

    def complete_sign_in(self, request_id: str, role_id: str) -> str:
        """The person picked a role: issue a single-use code, return the client's redirect."""
        if role_id not in ROLES:
            raise ValueError("Unknown role.")
        held = self.sign_ins.pop(request_id, None)
        if held is None or held[2] < time.time():
            raise ValueError("This sign-in has expired or was already used. Start again from the client.")
        client_id, params, _ = held
        code = secrets.token_urlsafe(32)
        self.codes[code] = AuthorizationCode(
            code=code, scopes=params.scopes or [SCOPE], expires_at=time.time() + SIGN_IN_SECONDS,
            client_id=client_id, code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource, subject=role_id)
        return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state)

    # /token: swap the code (once) for tokens.
    async def load_authorization_code(self, client: OAuthClientInformationFull,
                                      authorization_code: str) -> AuthorizationCode | None:
        code = self.codes.get(authorization_code)
        return code if code and code.client_id == client.client_id else None

    async def exchange_authorization_code(self, client: OAuthClientInformationFull,
                                          authorization_code: AuthorizationCode) -> OAuthToken:
        self.codes.pop(authorization_code.code, None)
        return self._issue(client.client_id, authorization_code.scopes,
                           authorization_code.resource, authorization_code.subject)

    async def load_refresh_token(self, client: OAuthClientInformationFull,
                                 refresh_token: str) -> RefreshToken | None:
        token = self.refresh_tokens.get(refresh_token)
        return token if token and token.client_id == client.client_id else None

    async def exchange_refresh_token(self, client: OAuthClientInformationFull,
                                     refresh_token: RefreshToken, scopes: list[str]) -> OAuthToken:
        self.refresh_tokens.pop(refresh_token.token, None)
        return self._issue(client.client_id, scopes or refresh_token.scopes,
                           refresh_token.resource, refresh_token.subject)

    # Every MCP request: is this bearer token one we issued, and still in date?
    async def load_access_token(self, token: str) -> AccessToken | None:
        access = self.access_tokens.get(token)
        if access and access.expires_at and access.expires_at < time.time():
            self.access_tokens.pop(token, None)
            return None
        return access

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        self.access_tokens.pop(token.token, None)
        self.refresh_tokens.pop(token.token, None)

    def _issue(self, client_id: str, scopes: list[str], resource: str | None,
               subject: str | None) -> OAuthToken:
        now = int(time.time())
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        # The token is for this server only (its resource), so another server would refuse it.
        resource = resource or self.resource_url
        self.access_tokens[access] = AccessToken(
            token=access, client_id=client_id, scopes=scopes, expires_at=now + TOKEN_SECONDS,
            resource=resource, subject=subject)
        self.refresh_tokens[refresh] = RefreshToken(
            token=refresh, client_id=client_id, scopes=scopes, expires_at=now + REFRESH_SECONDS,
            resource=resource, subject=subject)
        return OAuthToken(access_token=access, token_type="Bearer", expires_in=TOKEN_SECONDS,
                          scope=" ".join(scopes), refresh_token=refresh)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Sign in to Fjordvik</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ font-family: Segoe UI, system-ui, sans-serif; max-width: 34rem; margin: 3rem auto;
       padding: 0 1rem; color: #1f2933; }}
button {{ display: block; width: 100%; text-align: left; margin: .5rem 0; padding: .8rem 1rem;
         border: 1px solid #9aa5b1; border-radius: 6px; background: #fff; font: inherit;
         cursor: pointer; }}
button:hover, button:focus {{ border-color: #1f6feb; outline: 2px solid #1f6feb; }}
small {{ color: #52606d; }}
</style></head><body>
<h1>Sign in to the Fjordvik connector</h1>
<p>{message}</p>
{body}
<p><small>Demo sign-in: pick a role, no password. A company connector would send you to its
identity provider (Microsoft Entra ID, for example) and read your role from your groups.
Fjordvik is a fictional company with synthetic data.</small></p>
</body></html>"""


def sign_in_routes(provider: DemoOAuthProvider):
    """The two routes behind the sign-in page: show the roles, then finish the sign-in."""

    async def show(request: Request) -> Response:
        request_id = request.query_params.get("request", "")
        if request_id not in provider.sign_ins:
            return HTMLResponse(PAGE.format(
                message="This sign-in has expired or was already used. Start again from the client.",
                body=""), status_code=400)
        buttons = "".join(
            f'<button name="role" value="{html.escape(role_id)}">'
            f"<strong>{html.escape(role.name)}</strong><br><small>{html.escape(role.summary)}</small>"
            "</button>"
            for role_id, role in ROLES.items())
        form = (f'<form method="post" action="/login">'
                f'<input type="hidden" name="request" value="{html.escape(request_id)}">{buttons}</form>')
        return HTMLResponse(PAGE.format(message="Who are you signing in as?", body=form))

    async def finish(request: Request) -> Response:
        form = await request.form()
        try:
            redirect = provider.complete_sign_in(str(form.get("request", "")), str(form.get("role", "")))
        except ValueError as e:
            return HTMLResponse(PAGE.format(message=html.escape(str(e)), body=""), status_code=400)
        return RedirectResponse(redirect, status_code=302)

    return show, finish
