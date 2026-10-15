"""Shared fixtures. Nothing in the suite may touch the network."""

import urllib.request

import pytest

from helpers import FakeAPI
from modelaudit import detect


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail loudly if any code path reaches for the network without a mock."""
    def refuse(*a, **k):
        raise AssertionError("test tried to use the network")
    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    detect._GH_CACHE.clear()
    detect._PUBLIC_CACHE.clear()
    yield
    detect._GH_CACHE.clear()
    detect._PUBLIC_CACHE.clear()


@pytest.fixture
def fake_api(monkeypatch):
    """Serve canned JSON instead of GitHub / Hugging Face. Returns the FakeAPI."""
    def install(routes):
        api = FakeAPI(routes)
        monkeypatch.setattr(urllib.request, "urlopen", api)
        return api
    return install
