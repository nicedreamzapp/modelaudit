"""Helpers shared by the tests: a fake HTTP API and tiny on-disk trees."""

import io
import json
import os
import urllib.error

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def license_text(name):
    with open(os.path.join(FIXTURES, "licenses", name), encoding="utf-8") as f:
        return f.read()


class FakeAPI:
    """Stand-in for urllib.request.urlopen that serves canned JSON by URL."""

    def __init__(self, routes):
        self.routes = routes        # url -> dict, or an Exception to raise
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        resp = self.routes.get(req.full_url)
        if resp is None:
            raise urllib.error.URLError(f"no route for {req.full_url}")
        if isinstance(resp, Exception):
            raise resp
        return io.BytesIO(json.dumps(resp).encode())


def make_tree(root, spec):
    """Create files from {"rel/path": "contents"}; a trailing "/" makes a directory."""
    for rel, content in spec.items():
        p = os.path.join(str(root), rel)
        if rel.endswith("/"):
            os.makedirs(p, exist_ok=True)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
    return str(root)


def git_checkout(remote=None):
    """Files for a minimal fake git checkout (just enough for detect.py)."""
    cfg = "[core]\n\trepositoryformatversion = 0\n"
    if remote:
        cfg += f'[remote "origin"]\n\turl = {remote}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n'
    return {".git/config": cfg, ".git/HEAD": "ref: refs/heads/main\n"}
