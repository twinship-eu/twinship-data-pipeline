"""Dagster resource for Keycloak OIDC token management."""

import time

import requests
from dagster import ConfigurableResource, EnvVar, Failure
from pydantic import PrivateAttr


class KeycloakTokenProvider(ConfigurableResource):
    """Provides JWT access tokens via Keycloak client credentials grant.

    Caches the token and refreshes it when expired.
    """

    server_url: str = EnvVar("KEYCLOAK_SERVER_URL").get_value("")
    realm: str = EnvVar("KEYCLOAK_REALM").get_value("twinship")
    client_id: str = EnvVar("KEYCLOAK_CLIENT_ID").get_value("")
    client_secret: str = EnvVar("KEYCLOAK_CLIENT_SECRET").get_value("")

    _cached_token: str | None = PrivateAttr(default=None)
    _token_expiry: float = PrivateAttr(default=0.0)

    @property
    def is_configured(self) -> bool:
        """Return True if Keycloak credentials are provided."""
        return bool(self.server_url and self.client_id and self.client_secret)

    @property
    def token_url(self) -> str:
        base = self.server_url.rstrip("/")
        return f"{base}/realms/{self.realm}/protocol/openid-connect/token"

    def get_access_token(self) -> str:
        """Get a valid access token, refreshing if expired."""
        if self._cached_token and time.time() < self._token_expiry:
            return self._cached_token

        try:
            response = requests.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10,
            )
        except requests.RequestException as e:
            raise Failure(f"Could not reach Keycloak at {self.token_url}: {e}") from e

        if response.status_code != 200:
            raise Failure(
                f"Keycloak token request failed. HTTP {response.status_code}: {response.text[:400]}"
            )

        data = response.json()
        self._cached_token = data["access_token"]
        # Refresh 30 seconds before actual expiry
        expires_in = data.get("expires_in", 300)
        self._token_expiry = time.time() + expires_in - 30

        return self._cached_token


# Default resource instance
keycloak_token_provider = KeycloakTokenProvider()
