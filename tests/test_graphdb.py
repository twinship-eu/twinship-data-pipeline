"""Tests for the GraphDB resource."""

import pytest
from dagster import Failure

from dagster_pipeline.resources.graphdb import GraphDBClient, _create_graphdb_repo_config


class TestAuthValidation:
    def test_no_credentials(self):
        client = GraphDBClient(username="", password="")
        assert client._auth is None

    def test_both_credentials(self):
        client = GraphDBClient(username="admin", password="secret")
        assert client._auth == ("admin", "secret")

    def test_username_only_raises(self):
        client = GraphDBClient(username="admin", password="")
        with pytest.raises(Failure, match="both username and password"):
            _ = client._auth

    def test_password_only_raises(self):
        client = GraphDBClient(username="", password="secret")
        with pytest.raises(Failure, match="both username and password"):
            _ = client._auth


class TestCreateRepoConfig:
    def test_contains_repository_id_and_title(self):
        config = _create_graphdb_repo_config("my-repo", "My Repository")
        assert 'rep:repositoryID "my-repo"' in config
        assert 'rdfs:label "My Repository"' in config

    def test_escapes_special_chars(self):
        config = _create_graphdb_repo_config('repo"test', "title\\bad")
        assert 'rep:repositoryID "repo\\"test"' in config
        assert 'rdfs:label "title\\\\bad"' in config
