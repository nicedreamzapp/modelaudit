"""detect.py: license text matching, repo/model identification, and the remote lookups."""

import os
import urllib.error

import pytest

from helpers import license_text, make_tree
from modelaudit import detect
from modelaudit.detect import (
    github_slug, git_remote, find_license_file, hf_repo_id, is_hf_snapshot,
    license_from_text, looks_like_model_dir, read,
)


# ------------------------------------------------------------------ license_from_text

@pytest.mark.parametrize("fixture, expected", [
    ("GPL-2", "GPL-2.0"),
    ("GPL-3", "GPL-3.0"),
    ("LGPL-2.1", "LGPL-2.1"),
    ("LGPL-3", "LGPL-3.0"),
    ("MPL-2.0", "MPL-2.0"),
    ("Apache-2.0", "Apache-2.0"),
])
def test_real_license_texts(fixture, expected):
    assert license_from_text(license_text(fixture)) == expected


MIT = """MIT License

Copyright (c) 2024 Example

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction..."""

BSD3 = """Copyright (c) 2024 Example
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
3. Neither the name of the copyright holder nor the names of its contributors..."""

BSD2 = """Copyright (c) 2024 Example
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice."""


@pytest.mark.parametrize("text, expected", [
    (MIT, "MIT"),
    (BSD3, "BSD-3-Clause"),
    (BSD2, "BSD-2-Clause"),
    ("Permission to use, copy, modify, and/or distribute this software for any purpose",
     "ISC"),
    ("This is free and unencumbered software released into the public domain.",
     "Unlicense"),
    ("GNU AFFERO GENERAL PUBLIC LICENSE\nVersion 3, 19 November 2007", "AGPL-3.0"),
    ("Mozilla Public License Version 2.0\n==================================", "MPL-2.0"),
    ("Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International",
     "CC-BY-NC-SA-4.0"),
    ("Creative Commons Attribution-NonCommercial 4.0 International", "CC-BY-NC-4.0"),
    ("Creative Commons Attribution-ShareAlike 4.0 International", "CC-BY-SA-4.0"),
])
def test_license_signatures(text, expected):
    assert license_from_text(text) == expected


def test_gpl3_mentioning_agpl_is_still_gpl3():
    # GPL-3.0 section 13 is titled "Use with the GNU Affero General Public License".
    # Here it falls inside the part of the file that gets read.
    text = license_text("GPL-3")
    i = text.index("  13. Use with the GNU Affero")
    assert license_from_text(text[:3000] + text[i:]) == "GPL-3.0"


def test_matching_is_case_insensitive():
    assert license_from_text(MIT.upper()) == "MIT"


@pytest.mark.parametrize("text", [
    "You may use these weights for non-commercial research only.",
    "Licensed for NonCommercial purposes.",
    "noncommercial use permitted",
])
def test_bespoke_non_commercial_text_is_caught(text):
    assert license_from_text(text) == "non-commercial (custom)"


@pytest.mark.parametrize("text", [None, "", "All rights reserved. Do not copy."])
def test_unrecognized_text_returns_none(text):
    assert license_from_text(text) is None


def test_only_the_head_of_a_huge_file_is_read():
    # A signature beyond the first 20000 characters is not considered.
    assert license_from_text("x" * 20001 + MIT) is None
    assert license_from_text("x" * 100 + MIT) == "MIT"


# ------------------------------------------------------------------ files on disk

@pytest.mark.parametrize("name", ["LICENSE", "LICENSE.md", "license.txt", "LICENCE",
                                  "COPYING", "COPYING.LESSER", "License-MIT"])
def test_find_license_file_names(tmp_path, name):
    make_tree(tmp_path, {name: MIT, "README.md": "hi"})
    assert find_license_file(str(tmp_path)) == os.path.join(str(tmp_path), name)


def test_find_license_file_ignores_directories_and_lookalikes(tmp_path):
    make_tree(tmp_path, {"LICENSES/": None, "MY_LICENSE": MIT, "unlicensed.txt": ""})
    assert find_license_file(str(tmp_path)) is None


def test_find_license_file_picks_first_sorted(tmp_path):
    make_tree(tmp_path, {"LICENSE": MIT, "COPYING": "x"})
    assert os.path.basename(find_license_file(str(tmp_path))) == "COPYING"


def test_find_license_file_missing_dir(tmp_path):
    assert find_license_file(str(tmp_path / "nope")) is None


def test_read_missing_file_returns_empty(tmp_path):
    assert read(str(tmp_path / "missing")) == ""


def test_read_tolerates_bad_utf8_and_limits(tmp_path):
    p = tmp_path / "f"
    p.write_bytes(b"ok \xff\xfe and more")
    assert read(str(p)).startswith("ok ")
    assert read(str(p), limit=2) == "ok"


# ------------------------------------------------------------------ git checkouts

@pytest.mark.parametrize("url, slug", [
    ("https://github.com/ml-explore/mlx", "ml-explore/mlx"),
    ("https://github.com/ml-explore/mlx.git", "ml-explore/mlx"),
    ("git@github.com:ml-explore/mlx-lm.git", "ml-explore/mlx-lm"),
    ("ssh://git@github.com/Blaizzy/mlx-vlm", "Blaizzy/mlx-vlm"),
    ("https://user:token@github.com/org/repo.git", "org/repo"),
    ("https://github.com/org/repo/", "org/repo"),
    # Repo names may contain dots.
    ("https://github.com/vercel/next.js", "vercel/next.js"),
    ("https://github.com/socketio/socket.io.git", "socketio/socket.io"),
    ("git@github.com:black-forest-labs/flux.1.git", "black-forest-labs/flux.1"),
])
def test_github_slug(url, slug):
    assert github_slug(url) == slug


@pytest.mark.parametrize("url", [None, "", "https://gitlab.com/org/repo.git",
                                 "/srv/git/repo.git"])
def test_github_slug_non_github(url):
    assert github_slug(url) is None


def test_git_remote_reads_config(tmp_path):
    make_tree(tmp_path, {".git/config":
                         '[remote "origin"]\n\turl = git@github.com:a/b.git\n'})
    assert git_remote(str(tmp_path)) == "git@github.com:a/b.git"


def test_git_remote_without_remote(tmp_path):
    make_tree(tmp_path, {".git/config": "[core]\n\tbare = false\n"})
    assert git_remote(str(tmp_path)) is None


def test_git_remote_not_a_checkout(tmp_path):
    assert git_remote(str(tmp_path)) is None


# ------------------------------------------------------------------ model identification

def test_hf_repo_id_from_cache_path():
    p = "/home/u/.cache/huggingface/hub/models--black-forest-labs--FLUX.1-dev/snapshots/abc123"
    assert hf_repo_id(p) == "black-forest-labs/FLUX.1-dev"


def test_hf_repo_id_from_config(tmp_path):
    make_tree(tmp_path, {"config.json": '{"_name_or_path": "mlx-community/Qwen-4bit"}'})
    assert hf_repo_id(str(tmp_path)) == "mlx-community/Qwen-4bit"


@pytest.mark.parametrize("cfg", [
    '{"_name_or_path": "/Users/someone/models/local"}',   # a local path, not a repo id
    '{"_name_or_path": "bert-base-uncased"}',             # no org
    '{"_name_or_path": 7}',
    '{}',
    '[1, 2, 3]',
    'not json at all',
])
def test_hf_repo_id_unusable_config(tmp_path, cfg):
    make_tree(tmp_path, {"config.json": cfg})
    assert hf_repo_id(str(tmp_path)) is None


def test_hf_repo_id_nothing_to_go_on(tmp_path):
    assert hf_repo_id(str(tmp_path)) is None


@pytest.mark.parametrize("path, expected", [
    ("/x/hub/models--org--name/snapshots/0123abcdef", True),
    ("/x/hub/models--org--name/snapshots/0123abcdef/", True),
    ("/x/hub/models--org--name/snapshots/0123abcdef/transformer", False),
    ("/x/hub/models--org--name/snapshots", False),
    ("/x/hub/models--org--name/snapshots/main", False),
    ("/x/hub/datasets--org--name/snapshots/0123abcdef", False),
])
def test_is_hf_snapshot(path, expected):
    assert is_hf_snapshot(path) is expected


@pytest.mark.parametrize("names, expected", [
    ({"model.safetensors", "config.json"}, True),
    ({"llama-3-8b.Q4_K_M.gguf"}, True),
    ({"weights.onnx"}, True),
    ({"model_index.json", "README.md"}, True),           # diffusers root
    ({"config.json", "model-00001-of-00002.safetensors"}, True),
    ({"config.json", "README.md"}, False),
    ({"train.py", "README.md"}, False),
    (set(), False),
])
def test_looks_like_model_dir(names, expected):
    assert looks_like_model_dir(names) is expected


# ------------------------------------------------------------------ Hugging Face lookup

HF = "https://huggingface.co/api/models/"


def test_hf_license_reads_license_name_when_license_is_other(fake_api):
    # FLUX.1-dev's real card: license "other", the real name in license_name.
    fake_api({HF + "black-forest-labs/FLUX.1-dev": {"cardData": {
        "license": "other", "license_name": "flux-1-dev-non-commercial-license"}}})
    lic, src = detect.hf_license("black-forest-labs/FLUX.1-dev")
    assert lic == "flux-1-dev-non-commercial-license"
    assert src == "https://huggingface.co/black-forest-labs/FLUX.1-dev"


@pytest.mark.parametrize("card, expected", [
    ({"license": "apache-2.0"}, "apache-2.0"),
    ({"license": ["mit", "apache-2.0"]}, "mit"),
    ({"license": []}, None),
    ({"license": "other"}, "other"),
    ({"license": "unknown", "license_name": "custom-thing"}, "custom-thing"),
    ({"license_name": "only-a-name"}, "only-a-name"),
    ({}, None),
])
def test_hf_license_card_shapes(fake_api, card, expected):
    fake_api({HF + "o/m": {"cardData": card}})
    assert detect.hf_license("o/m")[0] == expected


def test_hf_license_without_card_data(fake_api):
    fake_api({HF + "o/m": {"id": "o/m", "cardData": None}})
    assert detect.hf_license("o/m")[0] is None


@pytest.mark.parametrize("err", [
    urllib.error.URLError("down"),
    urllib.error.HTTPError(HF + "o/m", 404, "Not Found", {}, None),
    TimeoutError(),
    OSError("reset"),
])
def test_hf_license_network_failure(fake_api, err):
    fake_api({HF + "o/m": err})
    assert detect.hf_license("o/m") == (None, None)


def test_hf_license_sends_user_agent(fake_api):
    api = fake_api({HF + "o/m": {"cardData": {"license": "mit"}}})
    detect.hf_license("o/m")
    assert api.requests[0].get_header("User-agent") == detect.UA


# ------------------------------------------------------------------ GitHub lookup

GH = "https://api.github.com/repos/"


@pytest.mark.parametrize("payload, expected", [
    ({"license": {"spdx_id": "AGPL-3.0"}}, "AGPL-3.0"),
    ({"license": {"spdx_id": "NOASSERTION"}}, None),
    ({"license": None}, None),
    ({}, None),
])
def test_gh_license(fake_api, payload, expected):
    fake_api({GH + "o/r": payload})
    lic, src = detect._gh_license("o/r")
    assert lic == expected
    assert src == "https://github.com/o/r"


def test_gh_license_failure(fake_api):
    fake_api({GH + "o/r": urllib.error.URLError("rate limited")})
    assert detect._gh_license("o/r") == (None, None)


def test_gh_license_is_cached(fake_api):
    api = fake_api({GH + "o/r": {"license": {"spdx_id": "MIT"}}})
    detect._gh_license("o/r")
    detect._gh_license("o/r")
    assert len(api.requests) == 1


@pytest.mark.parametrize("var", ["GITHUB_TOKEN", "GH_TOKEN"])
def test_gh_license_uses_token(fake_api, monkeypatch, var):
    monkeypatch.setenv(var, "secret123")
    api = fake_api({GH + "o/r": {"license": {"spdx_id": "MIT"}}})
    detect._gh_license("o/r")
    assert api.requests[0].get_header("Authorization") == "Bearer secret123"


def test_gh_license_no_token_no_auth_header(fake_api):
    api = fake_api({GH + "o/r": {"license": {"spdx_id": "MIT"}}})
    detect._gh_license("o/r")
    assert api.requests[0].get_header("Authorization") is None


@pytest.mark.parametrize("payload, expected", [
    ({"private": False}, True),
    ({"private": True}, False),
    ({}, False),
])
def test_is_public(fake_api, payload, expected):
    fake_api({GH + "o/r": payload})
    assert detect._is_public("o/r") is expected


def test_is_public_failure_is_not_public(fake_api):
    fake_api({GH + "o/r": urllib.error.HTTPError(GH + "o/r", 404, "nf", {}, None)})
    assert detect._is_public("o/r") is False
