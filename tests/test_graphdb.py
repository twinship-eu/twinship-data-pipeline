"""Tests for the GraphDB resource."""

import pytest
from dagster import Failure

from dagster_pipeline.resources.graphdb import GraphDBClient, _create_graphdb_repo_config


class TestAuthValidation:
    def test_no_credentials(self):
        client = GraphDBClient(username="", password="")
        assert client._request_kwargs() == {}

    def test_both_credentials(self):
        client = GraphDBClient(username="admin", password="secret")
        assert client._request_kwargs() == {"auth": ("admin", "secret")}

    def test_username_only_raises(self):
        client = GraphDBClient(username="admin", password="")
        with pytest.raises(Failure, match="both username and password"):
            client._request_kwargs()

    def test_password_only_raises(self):
        client = GraphDBClient(username="", password="secret")
        with pytest.raises(Failure, match="both username and password"):
            client._request_kwargs()


class TestCreateRepoConfig:
    def test_contains_repository_id_and_title(self):
        config = _create_graphdb_repo_config("my-repo", "My Repository")
        assert 'rep:repositoryID "my-repo"' in config
        assert 'rdfs:label "My Repository"' in config

    def test_escapes_special_chars(self):
        config = _create_graphdb_repo_config('repo"test', "title\\bad")
        assert 'rep:repositoryID "repo\\"test"' in config
        assert 'rdfs:label "title\\\\bad"' in config


class _Response:
    status_code = 204
    text = ""
    reason = "No Content"


class TestNamedGraphs:
    """Requests sent for named-graph uploads and clears (no GraphDB needed)."""

    GRAPH = "https://twin-ship.eu/graphs/test-vessel/components"

    @pytest.fixture
    def calls(self, monkeypatch):
        calls = []

        def record(method):
            def fake(url, **kwargs):
                calls.append((method, url, kwargs))
                return _Response()

            return fake

        for method in ("delete", "post"):
            monkeypatch.setattr(
                f"dagster_pipeline.resources.graphdb.requests.{method}", record(method)
            )
        return calls

    @pytest.fixture
    def client(self):
        return GraphDBClient(base_url="http://graphdb:7200", username="", password="")

    def test_clear_without_contexts_clears_everything(self, client, calls):
        client.clear_repository(repo_id="r")
        assert calls[0][2]["params"] is None

    def test_clear_named_and_default_graph(self, client, calls):
        client.clear_repository(repo_id="r", contexts=[self.GRAPH, None])
        assert calls[0][2]["params"] == [("context", f"<{self.GRAPH}>"), ("context", "null")]

    def test_upload_into_named_graph(self, client, calls):
        client.upload_ttl("<a> <b> <c> .", repo_id="r", context=self.GRAPH)
        assert calls[0][2]["params"] == {"context": f"<{self.GRAPH}>"}

    def test_upload_without_context_uses_default_graph(self, client, calls):
        client.upload_ttl("<a> <b> <c> .", repo_id="r")
        assert calls[0][2]["params"] is None

    def test_server_import_into_named_graph(self, client, calls):
        client.import_server_files(["ontology/x.ttl"], repo_id="r", context=self.GRAPH)
        assert calls[0][2]["json"] == {
            "fileNames": ["ontology/x.ttl"],
            "importSettings": {"context": self.GRAPH},
        }


def test_vessel_graph_iri():
    from dagster_pipeline.assets.harmonisation import vessel_graph

    assert vessel_graph("futuristic-vessel", "voyages") == (
        "https://twin-ship.eu/graphs/futuristic-vessel/voyages"
    )
