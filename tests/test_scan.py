"""detect.scan(): walking a real directory tree built in tmp_path."""

import os

import pytest

from helpers import git_checkout, license_text, make_tree
from modelaudit.detect import scan

MIT = "Permission is hereby granted, free of charge, to any person obtaining a copy"
AGPL = "GNU AFFERO GENERAL PUBLIC LICENSE\nVersion 3, 19 November 2007\n"
GH = "https://api.github.com/repos/"
HF = "https://huggingface.co/api/models/"


def under(prefix, spec):
    return {f"{prefix}/{k}": v for k, v in spec.items()}


def by_name(results):
    return {r["name"]: r for r in results}


def test_empty_directory(tmp_path):
    assert scan(str(tmp_path), use_network=False) == []


def test_finds_code_checkout_with_local_license(tmp_path):
    make_tree(tmp_path, {
        **under("vendor/mlx", git_checkout("https://github.com/ml-explore/mlx.git")),
        "vendor/mlx/LICENSE": MIT,
    })
    (r,) = scan(str(tmp_path), use_network=False)
    assert r["kind"] == "code"
    assert r["name"] == "ml-explore/mlx"
    assert r["license"] == "MIT"
    assert r["source"].endswith(os.path.join("mlx", "LICENSE"))
    assert r["path"] == str(tmp_path / "vendor" / "mlx")
    assert r["published"] is False


def test_checkout_without_remote_uses_folder_name(tmp_path):
    make_tree(tmp_path, {**under("engine", git_checkout()), "engine/LICENSE": AGPL})
    (r,) = scan(str(tmp_path), use_network=False)
    assert r["name"] == "engine"
    assert r["license"] == "AGPL-3.0"


def test_checkout_with_unreadable_license_is_unknown(tmp_path):
    make_tree(tmp_path, {**under("x", git_checkout("git@github.com:o/x.git")),
                         "x/LICENSE": "All rights reserved."})
    (r,) = scan(str(tmp_path), use_network=False)
    assert r["license"] == "unknown"
    assert r["source"].endswith("LICENSE")     # still points at the file to read


def test_worktree_style_git_file_counts_as_checkout(tmp_path):
    make_tree(tmp_path, {"wt/.git": "gitdir: /elsewhere/.git/worktrees/wt\n",
                         "wt/LICENSE": MIT})
    (r,) = scan(str(tmp_path), use_network=False)
    assert (r["kind"], r["name"], r["license"]) == ("code", "wt", "MIT")


def test_same_repo_twice_reported_once(tmp_path):
    remote = "https://github.com/o/r"
    make_tree(tmp_path, {**under("a", git_checkout(remote)),
                         **under("b", git_checkout(remote))})
    assert len(scan(str(tmp_path), use_network=False)) == 1


def test_nested_checkouts_are_both_found(tmp_path):
    make_tree(tmp_path, {
        **under("app", git_checkout("https://github.com/o/app")),
        "app/LICENSE": MIT,
        **under("app/third_party/engine", git_checkout("https://github.com/o/engine")),
        "app/third_party/engine/LICENSE": AGPL,
    })
    found = by_name(scan(str(tmp_path), use_network=False))
    assert found["o/app"]["license"] == "MIT"
    assert found["o/engine"]["license"] == "AGPL-3.0"


def test_finds_weights_folder(tmp_path):
    make_tree(tmp_path, {
        "models/qwen/config.json": '{"_name_or_path": "mlx-community/Qwen-4bit"}',
        "models/qwen/model.safetensors": "",
        "models/qwen/LICENSE": license_text("Apache-2.0"),
    })
    (r,) = scan(str(tmp_path), use_network=False)
    assert r["kind"] == "weights"
    assert r["name"] == "mlx-community/Qwen-4bit"
    assert r["license"] == "Apache-2.0"


def test_weights_without_id_or_license(tmp_path):
    make_tree(tmp_path, {"m/thing.gguf": ""})
    (r,) = scan(str(tmp_path), use_network=False)
    assert (r["name"], r["license"], r["source"]) == ("m", "unknown", "")


def test_diffusers_model_is_one_finding(tmp_path):
    # FLUX / SD layout: only model_index.json at the root, weights in subfolders.
    make_tree(tmp_path, {
        "flux/model_index.json": "{}",
        "flux/transformer/diffusion_pytorch_model.safetensors": "",
        "flux/vae/diffusion_pytorch_model.safetensors": "",
        "flux/text_encoder/model.safetensors": "",
    })
    found = scan(str(tmp_path), use_network=False)
    assert [r["name"] for r in found] == ["flux"]


def test_hf_cache_snapshot(tmp_path):
    snap = "models--black-forest-labs--FLUX.1-dev/snapshots/3de623fc3c33e44ffbe2bad470d0f45bccf2eb21"
    make_tree(tmp_path, {
        f"{snap}/transformer/diffusion_pytorch_model.safetensors": "",
        f"{snap}/README.md": "",
        "models--black-forest-labs--FLUX.1-dev/refs/main": "3de623f",
        "models--black-forest-labs--FLUX.1-dev/blobs/0a1b2c": "",
    })
    (r,) = scan(str(tmp_path), use_network=False)
    assert r["kind"] == "weights"
    assert r["name"] == "black-forest-labs/FLUX.1-dev"
    assert r["license"] == "unknown"


def test_skipped_and_hidden_directories(tmp_path):
    make_tree(tmp_path, {
        "node_modules/x/model.onnx": "",
        ".venv/lib/model.safetensors": "",
        "__pycache__/m.pt": "",
        "build/out.gguf": "",
        ".hidden/model.safetensors": "",
        ".cache/huggingface/hub/models--o--m/snapshots/abcdef0/model.safetensors": "",
    })
    assert scan(str(tmp_path), use_network=False) == []


def test_scan_root_inside_hidden_folder_is_walked(tmp_path):
    # Hidden folders are skipped while walking, but pointing at one directly works.
    hub = tmp_path / ".cache" / "huggingface" / "hub"
    make_tree(hub, {"models--o--m/snapshots/abcdef0/model.safetensors": ""})
    (r,) = scan(str(hub), use_network=False)
    assert r["name"] == "o/m"


def test_max_depth(tmp_path):
    make_tree(tmp_path, {"a/b/c/model.gguf": ""})
    assert scan(str(tmp_path), use_network=False, max_depth=4)
    assert scan(str(tmp_path), use_network=False, max_depth=3) == []


def test_tilde_is_expanded(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    make_tree(tmp_path, {"proj/m/model.gguf": ""})
    (r,) = scan("~/proj", use_network=False)
    assert r["path"] == str(tmp_path / "proj" / "m")


def test_offline_never_touches_network(tmp_path):
    # The autouse no_network fixture raises if urlopen is called at all.
    make_tree(tmp_path, {
        **under("r", git_checkout("https://github.com/o/r")),
        "models--o--m/snapshots/abcdef0/model.safetensors": "",
    })
    found = by_name(scan(str(tmp_path), use_network=False))
    assert found["o/r"]["license"] == "unknown"
    assert found["o/m"]["license"] == "unknown"


def test_online_fills_gaps_from_github_and_hf(tmp_path, fake_api):
    api = fake_api({
        GH + "o/r": {"license": {"spdx_id": "AGPL-3.0"}, "private": False},
        HF + "black-forest-labs/FLUX.1-dev": {"cardData": {
            "license": "other", "license_name": "flux-1-dev-non-commercial-license"}},
    })
    make_tree(tmp_path, {
        **under("r", git_checkout("https://github.com/o/r")),
        "models--black-forest-labs--FLUX.1-dev/snapshots/abcdef0/model_index.json": "{}",
    })
    found = by_name(scan(str(tmp_path), use_network=True))
    assert found["o/r"]["license"] == "AGPL-3.0"
    assert found["o/r"]["source"] == "https://github.com/o/r"
    assert found["o/r"]["published"] is True
    flux = found["black-forest-labs/FLUX.1-dev"]
    assert flux["license"] == "flux-1-dev-non-commercial-license"
    assert flux["source"] == "https://huggingface.co/black-forest-labs/FLUX.1-dev"
    assert all(r.get_header("User-agent") for r in api.requests)


def test_online_local_license_wins_over_api(tmp_path, fake_api):
    api = fake_api({GH + "o/r": {"private": True}})
    make_tree(tmp_path, {**under("r", git_checkout("https://github.com/o/r")),
                         "r/LICENSE": MIT})
    (r,) = scan(str(tmp_path), use_network=True)
    assert r["license"] == "MIT"
    assert r["published"] is False
    # Only the public/private check went out; the license lookup was skipped.
    assert len(api.requests) == 1


def test_online_lookup_failure_degrades_to_unknown(tmp_path, fake_api):
    fake_api({})          # every request fails
    make_tree(tmp_path, {**under("r", git_checkout("https://github.com/o/r")),
                         "models--o--m/snapshots/abcdef0/model.gguf": ""})
    found = by_name(scan(str(tmp_path), use_network=True))
    assert found["o/r"]["license"] == "unknown"
    assert found["o/r"]["published"] is False
    assert found["o/m"]["license"] == "unknown"
