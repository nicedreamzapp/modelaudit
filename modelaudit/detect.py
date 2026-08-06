"""Find what's actually installed, and work out the license for each thing.

Three kinds of thing get found, and they are genuinely different:

  code    — a git checkout of somebody's project sitting in your tree
  weights — a downloaded model. Its license is often NOT the license of the code
            that runs it. FLUX is the canonical trap: Apache-2.0 code, non-commercial
            weights. Every dependency scanner in the world reads the code license
            and tells you you're fine.
  package — an ordinary pip/npm dependency

Everything is resolved offline first. The network is only touched to read a Hugging
Face model card when a local model has no license recorded, and even that is optional.
"""

import json
import os
import re
import urllib.error
import urllib.request

UA = "modelaudit (+https://github.com/nicedreamzapp/modelaudit)"
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "site-packages",
             ".mypy_cache", ".pytest_cache", "build", "dist", ".cache"}

# Distinctive strings, longest/most specific first — order matters.
LICENSE_SIGNATURES = [
    ("AGPL-3.0", ("GNU AFFERO GENERAL PUBLIC LICENSE",)),
    ("GPL-3.0", ("GNU GENERAL PUBLIC LICENSE", "Version 3")),
    ("GPL-2.0", ("GNU GENERAL PUBLIC LICENSE", "Version 2")),
    ("LGPL-3.0", ("GNU LESSER GENERAL PUBLIC LICENSE", "Version 3")),
    ("LGPL-2.1", ("GNU LESSER GENERAL PUBLIC LICENSE", "Version 2.1")),
    ("Apache-2.0", ("Apache License", "Version 2.0")),
    ("MPL-2.0", ("Mozilla Public License Version 2.0",)),
    ("BSD-3-Clause", ("Redistribution and use in source and binary forms",
                      "Neither the name of")),
    ("BSD-2-Clause", ("Redistribution and use in source and binary forms",)),
    ("ISC", ("Permission to use, copy, modify, and/or distribute this software",)),
    ("Unlicense", ("This is free and unencumbered software released into the public domain",)),
    ("MIT", ("Permission is hereby granted, free of charge",)),
    ("CC-BY-NC-SA-4.0", ("Attribution-NonCommercial-ShareAlike",)),
    ("CC-BY-NC-4.0", ("Attribution-NonCommercial",)),
    ("CC-BY-SA-4.0", ("Attribution-ShareAlike",)),
]


def license_from_text(text):
    """Identify a license from its actual text."""
    if not text:
        return None
    head = text[:20000]
    for lid, needles in LICENSE_SIGNATURES:
        if all(n.lower() in head.lower() for n in needles):
            return lid
    if re.search(r"non-?commercial", head, re.I):
        return "non-commercial (custom)"
    return None


def find_license_file(d):
    try:
        for name in sorted(os.listdir(d)):
            if re.match(r"^(licen[cs]e|copying)", name, re.I):
                p = os.path.join(d, name)
                if os.path.isfile(p):
                    return p
    except OSError:
        pass
    return None


def read(p, limit=200000):
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except OSError:
        return ""


# ------------------------------------------------------------------ git checkouts

def git_remote(repo_dir):
    cfg = os.path.join(repo_dir, ".git", "config")
    if not os.path.exists(cfg):
        return None
    m = re.search(r"url\s*=\s*(\S+)", read(cfg, 20000))
    return m.group(1) if m else None


def github_slug(url):
    if not url:
        return None
    m = re.search(r"github\.com[:/]+([^/]+)/([^/\s.]+)", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


# ------------------------------------------------------------------ HF weights

def hf_repo_id(model_dir):
    """Work out which Hugging Face repo a local model directory came from."""
    # 1. The HF cache encodes it in the path: models--org--name
    m = re.search(r"models--([^/]+?)--([^/]+)", model_dir)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    # 2. config.json often records where it came from
    cfg = os.path.join(model_dir, "config.json")
    if os.path.exists(cfg):
        try:
            d = json.loads(read(cfg, 100000))
            for key in ("_name_or_path", "name_or_path", "model_name"):
                v = d.get(key)
                if isinstance(v, str) and "/" in v and not v.startswith("/"):
                    return v
        except (json.JSONDecodeError, AttributeError):
            pass
    return None


def hf_license(repo_id, timeout=12):
    """Read the license off a model card. This is the step ordinary scanners skip."""
    url = f"https://huggingface.co/api/models/{repo_id}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None, None
    card = data.get("cardData") or {}
    lic = card.get("license")
    if isinstance(lic, list):
        lic = lic[0] if lic else None
    name = card.get("license_name") or None
    # Hugging Face records a bespoke license as the literal string "other" and puts the
    # real name in license_name. FLUX.1-dev is exactly this: license "other",
    # license_name "flux-1-dev-non-commercial-license". Taking "other" at face value
    # is how a scanner misses a non-commercial model entirely.
    if (not lic or str(lic).lower() in ("other", "unknown")) and name:
        lic = name
    return (lic or name), f"https://huggingface.co/{repo_id}"


WEIGHT_SUFFIXES = (".safetensors", ".gguf", ".bin", ".mlmodelc", ".mlpackage",
                   ".onnx", ".pt", ".pth", ".tflite", ".ckpt")


# A Hugging Face cache entry always looks like  models--org--name/snapshots/<hash>.
# Matching on that is exact, and it stops multi-component models from being reported
# as a pile of separate findings.
HF_SNAPSHOT = re.compile(r"models--[^/]+--[^/]+/snapshots/[0-9a-f]{6,}/?$")


def is_hf_snapshot(path):
    return bool(HF_SNAPSHOT.search(path.replace(os.sep, "/")))


def looks_like_model_dir(names):
    """A directory holding actual model weights, rather than code that loads them."""
    if any(n.endswith(WEIGHT_SUFFIXES) for n in names):
        return True
    # diffusers-style models (FLUX, SD) keep weights in subfolders and only a
    # model_index.json at the root. Missing these was the first real bug here.
    if "model_index.json" in names:
        return True
    return "config.json" in names and any(n.startswith("model") for n in names)


# ------------------------------------------------------------------ the walk

def scan(root, use_network=True, max_depth=6):
    """Yield dicts describing everything found, with a license attached where possible."""
    root = os.path.abspath(os.path.expanduser(root))
    seen_repos = set()
    results = []

    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath[len(root):].count(os.sep)
        if depth >= max_depth:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
                       or d == ".git"]

        names = set(filenames)

        # --- a git checkout of someone else's project
        if ".git" in dirnames or ".git" in names:
            slug = github_slug(git_remote(dirpath))
            lf = find_license_file(dirpath)
            lic = license_from_text(read(lf)) if lf else None
            src = lf if lic else None
            if not lic and slug and use_network:
                lic, src = _gh_license(slug)
            if slug not in seen_repos:
                seen_repos.add(slug)
                results.append({
                    "kind": "code",
                    "path": dirpath,
                    "name": slug or os.path.basename(dirpath),
                    "license": lic or "unknown",
                    "source": src or (lf or ""),
                    # Copyleft asks you to publish. If this checkout is a public repo,
                    # you already are, and the finding should say so instead of shouting.
                    "published": _is_public(slug) if (slug and use_network) else False,
                })
            dirnames[:] = [d for d in dirnames if d != ".git"]
            continue

        # --- a downloaded model
        if is_hf_snapshot(dirpath) or looks_like_model_dir(names):
            rid = hf_repo_id(dirpath)
            lic, src = (None, None)
            lf = find_license_file(dirpath)
            if lf:
                lic, src = license_from_text(read(lf)), lf
            if not lic and rid and use_network:
                lic, src = hf_license(rid)
            results.append({
                "kind": "weights",
                "path": dirpath,
                "name": rid or os.path.basename(dirpath),
                "license": lic or "unknown",
                "source": src or "",
            })
            dirnames[:] = []

    return results


_GH_CACHE = {}


def _gh_license(slug, timeout=12):
    if slug in _GH_CACHE:
        return _GH_CACHE[slug]
    url = f"https://api.github.com/repos/{slug}"
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/vnd.github+json"})
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
        lic = ((d.get("license") or {}).get("spdx_id")) or None
        out = (None if lic in (None, "NOASSERTION") else lic,
               f"https://github.com/{slug}")
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        out = (None, None)
    _GH_CACHE[slug] = out
    return out


_PUBLIC_CACHE = {}


def _is_public(slug):
    """Is this GitHub repo publicly readable? Used to soften copyleft findings."""
    if slug in _PUBLIC_CACHE:
        return _PUBLIC_CACHE[slug]
    req = urllib.request.Request(f"https://api.github.com/repos/{slug}",
                                 headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            out = not json.load(r).get("private", True)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        out = False
    _PUBLIC_CACHE[slug] = out
    return out
