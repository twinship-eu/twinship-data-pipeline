"""Dagster resource for GraphDB interaction."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pandas as pd
import requests
from dagster import ConfigurableResource, EnvVar, Failure
from pydantic import PrivateAttr

if TYPE_CHECKING:
    from dagster_pipeline.resources.keycloak import KeycloakTokenProvider


def _env_bool(var_name: str, default: bool) -> bool:
    """Parse a boolean from an environment variable string."""
    import os

    raw = os.getenv(var_name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(var_name: str, default: int) -> int:
    """Parse an integer from an environment variable string."""
    import os

    raw = os.getenv(var_name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _ttl_escape_literal(value: str) -> str:
    """Escape a string for use inside a TTL quoted literal."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _normalize_graphdb_base_url(base_url: str) -> str:
    """Strip trailing slashes from a GraphDB base URL."""
    return base_url.rstrip("/")


def _create_graphdb_repo_config(repository_id: str, title: str) -> str:
    """Generate a TTL repository configuration for GraphDB."""
    escaped_repo_id = _ttl_escape_literal(repository_id)
    escaped_title = _ttl_escape_literal(title)
    return f"""@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.
@prefix rep: <http://www.openrdf.org/config/repository#>.
@prefix sr: <http://www.openrdf.org/config/repository/sail#>.
@prefix sail: <http://www.openrdf.org/config/sail#>.
@prefix graphdb: <http://www.ontotext.com/config/graphdb#>.

[] a rep:Repository ;
    rep:repositoryID "{escaped_repo_id}" ;
    rdfs:label "{escaped_title}" ;
    rep:repositoryImpl [
        rep:repositoryType "graphdb:SailRepository" ;
        sr:sailImpl [
            sail:sailType "graphdb:Sail" ;
            graphdb:ruleset "empty" ;
            graphdb:check-for-inconsistencies "false" ;
            graphdb:disable-sameAs "true" ;
            graphdb:enable-context-index "true"
        ]
    ].
"""


def _raise_graphdb_error(message: str, response: requests.Response | None = None) -> None:
    """Raise a Dagster Failure with optional HTTP response details."""
    if response is None:
        raise Failure(message)

    body = response.text.strip()
    if len(body) > 400:
        body = f"{body[:397]}..."

    raise Failure(
        f"{message}. HTTP {response.status_code} {response.reason}. Response: {body or '<empty>'}"
    )


class GraphDBClient(ConfigurableResource):
    """Dagster resource for interacting with a GraphDB triplestore."""

    base_url: str = EnvVar("GRAPHDB_BASE_URL").get_value("http://localhost:7200")
    repository_id: str = EnvVar("GRAPHDB_REPOSITORY_ID").get_value("twinship")
    repository_title: str = EnvVar("GRAPHDB_REPOSITORY_TITLE").get_value("TwinShip Data Repository")
    clear_before_upload: bool = _env_bool("GRAPHDB_CLEAR_BEFORE_UPLOAD", True)
    timeout_seconds: int = _env_int("GRAPHDB_TIMEOUT_SECONDS", 30)
    max_readiness_checks: int = _env_int("GRAPHDB_MAX_READINESS_CHECKS", 20)
    readiness_check_interval_seconds: int = _env_int("GRAPHDB_READINESS_CHECK_INTERVAL_SECONDS", 3)
    username: str = EnvVar("GRAPHDB_USERNAME").get_value("")
    password: str = EnvVar("GRAPHDB_PASSWORD").get_value("")

    _keycloak_token_provider: KeycloakTokenProvider | None = PrivateAttr(default=None)

    @property
    def normalized_base_url(self) -> str:
        return _normalize_graphdb_base_url(self.base_url)

    def _get_keycloak_provider(self) -> KeycloakTokenProvider | None:
        """Lazily create a KeycloakTokenProvider from env vars."""
        if self._keycloak_token_provider is None:
            from dagster_pipeline.resources.keycloak import KeycloakTokenProvider

            provider = KeycloakTokenProvider()
            if provider.is_configured:
                self._keycloak_token_provider = provider
        return self._keycloak_token_provider

    def _request_kwargs(self) -> dict:
        """Return auth kwargs for requests calls.

        Uses JWT bearer token if Keycloak is configured, otherwise falls back
        to basic auth (or no auth).
        """
        provider = self._get_keycloak_provider()
        if provider is not None and provider.is_configured:
            token = provider.get_access_token()
            return {"headers": {"Authorization": f"Bearer {token}"}}

        # Basic auth fallback
        if not self.username and not self.password:
            return {}
        if not self.username or not self.password:
            raise Failure(
                "GraphDB credentials misconfigured: both username and password are required."
            )
        return {"auth": (self.username, self.password)}

    def _merge_kwargs(self, extra_headers: dict | None = None, **kwargs: object) -> dict:
        """Merge _request_kwargs with additional request arguments."""
        base = self._request_kwargs()
        if extra_headers:
            existing_headers = base.get("headers", {})
            existing_headers.update(extra_headers)
            base["headers"] = existing_headers
        base.update(kwargs)
        return base

    def wait_for_readiness(self) -> None:
        """Block until GraphDB responds to a repository listing request."""
        base_url = self.normalized_base_url
        repositories_url = f"{base_url}/rest/repositories"
        attempts = self.max_readiness_checks

        for attempt in range(1, attempts + 1):
            try:
                response = requests.get(
                    repositories_url, timeout=self.timeout_seconds, **self._request_kwargs()
                )
            except requests.RequestException:
                response = None

            if response is not None and response.status_code == 200:
                return

            if response is not None and response.status_code in {401, 403}:
                _raise_graphdb_error(
                    "GraphDB is reachable but authentication failed while listing repositories",
                    response,
                )

            if attempt < attempts:
                time.sleep(self.readiness_check_interval_seconds)

        _raise_graphdb_error(
            f"GraphDB at {base_url} did not become ready after "
            f"{attempts} checks with {self.readiness_check_interval_seconds}s interval"
        )

    def ensure_repository(self, repo_id: str | None = None, title: str | None = None) -> bool:
        """Create the repository if it does not already exist.

        Args:
            repo_id: Repository ID to create. Defaults to self.repository_id.
            title: Repository title. Defaults to self.repository_title.

        Returns True if a new repository was created, False if it already existed.
        """
        repo_id = repo_id or self.repository_id
        title = title or self.repository_title
        base_url = self.normalized_base_url

        # Check existence
        try:
            response = requests.get(
                f"{base_url}/rest/repositories/{repo_id}",
                timeout=self.timeout_seconds,
                **self._request_kwargs(),
            )
        except requests.RequestException as e:
            _raise_graphdb_error(f"Could not reach GraphDB while checking repository: {e}")

        if response.status_code == 200:
            return False
        if response.status_code != 404:
            _raise_graphdb_error(f"Could not check repository '{repo_id}'", response)

        # Create
        try:
            response = requests.post(
                f"{base_url}/rest/repositories",
                files={
                    "config": (
                        "repo-config.ttl",
                        _create_graphdb_repo_config(repo_id, title),
                        "text/turtle",
                    )
                },
                timeout=self.timeout_seconds,
                **self._request_kwargs(),
            )
        except requests.RequestException as e:
            _raise_graphdb_error(
                f"Could not reach GraphDB while creating repository '{repo_id}': {e}"
            )

        if response.status_code not in {200, 201, 204}:
            _raise_graphdb_error(f"Could not create GraphDB repository '{repo_id}'", response)

        return True

    def clear_repository(self, repo_id: str | None = None) -> None:
        """Delete all statements from the repository."""
        repo_id = repo_id or self.repository_id
        base_url = self.normalized_base_url

        try:
            response = requests.delete(
                f"{base_url}/repositories/{repo_id}/statements",
                timeout=self.timeout_seconds,
                **self._request_kwargs(),
            )
        except requests.RequestException as e:
            _raise_graphdb_error(
                f"Could not reach GraphDB while clearing repository '{repo_id}': {e}"
            )

        if response.status_code not in {200, 204}:
            _raise_graphdb_error(
                f"Could not clear GraphDB repository '{repo_id}' before upload",
                response,
            )

    def upload_ttl(self, ttl_data: str, repo_id: str | None = None) -> None:
        """Upload Turtle data to the repository."""
        repo_id = repo_id or self.repository_id
        base_url = self.normalized_base_url

        try:
            response = requests.post(
                f"{base_url}/repositories/{repo_id}/statements",
                data=ttl_data.encode("utf-8"),
                timeout=self.timeout_seconds,
                **self._merge_kwargs(extra_headers={"Content-Type": "text/turtle; charset=utf-8"}),
            )
        except requests.RequestException as e:
            _raise_graphdb_error(
                f"Could not reach GraphDB while uploading data to '{repo_id}': {e}"
            )

        if response.status_code not in {200, 204}:
            _raise_graphdb_error(f"Could not upload data to repository '{repo_id}'", response)

    def triple_count(self, repo_id: str | None = None) -> int | None:
        """Return the number of triples in the repository, or None on failure."""
        repo_id = repo_id or self.repository_id
        base_url = self.normalized_base_url

        try:
            response = requests.get(
                f"{base_url}/repositories/{repo_id}/size",
                timeout=self.timeout_seconds,
                **self._request_kwargs(),
            )
        except requests.RequestException:
            return None

        if response.status_code != 200:
            return None
        try:
            return int(response.text.strip())
        except ValueError:
            return None

    def run_select_query(self, query: str, repo_id: str | None = None) -> pd.DataFrame:
        """Execute a SPARQL SELECT query and return results as a DataFrame."""
        repo_id = repo_id or self.repository_id
        base_url = self.normalized_base_url

        try:
            response = requests.post(
                f"{base_url}/repositories/{repo_id}",
                data={"query": query},
                timeout=self.timeout_seconds,
                **self._merge_kwargs(extra_headers={"Accept": "application/sparql-results+json"}),
            )
        except requests.RequestException as e:
            _raise_graphdb_error(f"Could not query GraphDB repository '{repo_id}': {e}")

        if response.status_code != 200:
            _raise_graphdb_error(
                f"GraphDB SPARQL query failed for repository '{repo_id}'",
                response,
            )

        try:
            payload = response.json()
        except ValueError:
            _raise_graphdb_error(
                f"GraphDB returned a non-JSON response for repository '{repo_id}'",
                response,
            )

        columns = payload.get("head", {}).get("vars", [])
        bindings = payload.get("results", {}).get("bindings", [])

        rows = [{col: binding.get(col, {}).get("value") for col in columns} for binding in bindings]
        return pd.DataFrame(rows, columns=columns)


# Default resource instance
graphdb_client = GraphDBClient()
