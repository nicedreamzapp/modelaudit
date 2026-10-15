---
title: modelaudit configuration, every flag and environment variable
description: >-
  Reference for every modelaudit command-line option (--ship, --offline, --json,
  --all, --depth), the environment variables it reads (GITHUB_TOKEN, GH_TOKEN,
  NO_COLOR), the JSON output format and exit codes.
---

# Configuration

`modelaudit` has no config file. Everything is set by command-line flags and a
few environment variables. This page is built from
[`__main__.py`](https://github.com/nicedreamzapp/modelaudit/blob/main/modelaudit/__main__.py)
and [`detect.py`](https://github.com/nicedreamzapp/modelaudit/blob/main/modelaudit/detect.py).

```
usage: modelaudit [-h] [--ship {app,private,service}] [--offline] [--json]
                  [--all] [--depth DEPTH]
                  [path]
```

## Options

### `path` {#path}

The directory to audit. Optional, defaults to `.` (the current directory). `~` is
expanded.

If it is not a directory, the tool prints
`modelaudit: error: not a directory: PATH` and exits with code `2`.

If `path` is itself a git repository it is reported as a `code` finding like any
other checkout.

### `--ship {app,service,private}` {#ship}

How the thing you build reaches other people. Default: `service`.

| Value | Description printed by the tool |
|---|---|
| `app` | You distribute a binary, app bundle, or installer to users. |
| `service` | Users reach it over a network. A site, an API, a phone app talking to your server. |
| `private` | Only you and your team run it. Nothing leaves the building. |

The ship mode changes the severity of GPL, AGPL and weak copyleft licenses. It does
not change non-commercial (always `blocker`), vendor (always `review`) or
permissive (always `attribution`) licenses. The full rule table is in
[How it works](how-it-works.md#severity-rules).

### `--offline` {#offline}

Never touch the network. Use only what is on disk.

With `--offline`, three lookups are turned off:

1. GitHub repo license lookup for a checkout with no recognizable local license file.
2. GitHub "is this repo public" check for each checkout with a GitHub remote.
   Because of this, `published` is always `false` offline, so copyleft code is
   never softened from `blocker` to `obligation`. See
   [the published rule](how-it-works.md#the-published-rule).
3. Hugging Face model card lookup for weights with no recognizable local license file.

Anything that needed a lookup gets the license `unknown`, which is classified as
`review`. The report header says `offline mode`.

### `--json` {#json}

Print one JSON object instead of the colored report:

```json
{
  "ship_mode": "service",
  "root": "/absolute/path/you/scanned",
  "findings": [
    {
      "kind": "code",
      "path": "/absolute/path/vendor/agpl",
      "name": "example/agpl-thing",
      "license": "AGPL-3.0",
      "source": "/absolute/path/vendor/agpl/LICENSE",
      "published": false,
      "severity": "blocker",
      "headline": "AGPL over a network \u2014 you owe users your source",
      "detail": "AGPL-3.0 is the one license where ..."
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `kind` | `code` (a git checkout) or `weights` (a model folder). |
| `path` | Absolute folder where it was found. |
| `name` | `owner/repo` from the GitHub remote, `org/name` for Hugging Face weights, else the folder name. |
| `license` | License id or name, or `unknown`. |
| `source` | Where the license came from: a local file path, a `https://github.com/...` or `https://huggingface.co/...` URL, or `""`. |
| `published` | Only present on `code` findings. `true` when the checkout's GitHub repo is publicly readable. |
| `severity` | `blocker`, `obligation`, `attribution`, `review` or `ok`. |
| `headline`, `detail` | The human-readable explanation. |

Notes taken from the code:

- `--json` always includes **every** finding, including `ok` and `attribution`.
  `--all` has no effect on JSON output.
- Findings are sorted by severity (`blocker`, `obligation`, `attribution`,
  `review`, `ok`) and then by name.
- Non-ASCII characters are escaped (for example the dash in headlines becomes `\u2014`), because the code uses
  `json.dumps` with its default `ensure_ascii`.
- For `code` findings where the local license file was not recognized, `source`
  can be the path of that file even though `license` is `unknown` or came from
  GitHub. <!-- TODO-VERIFY: confirm this is the intended value of `source` in that case (detect.py, `"source": src or (lf or "")`). -->

### `--all` {#all}

Also show `attribution` and `ok` findings in the terminal report. By default they
are counted in the summary line but not printed.

### `--depth N` {#depth}

How many folder levels to walk. Default: `6`.

What the code does: the folder you scan is depth `0`. A folder at depth `N` or
deeper is not inspected and not descended into. So the default inspects the root
and five levels below it. `--depth 0` inspects nothing and reports
`0 dependencies found`.

Folders recognized as model weights are never descended into, whatever the depth.
Folders recognized as git checkouts are descended into (so a model inside a
checkout is still found).

## Environment variables

| Variable | Effect |
|---|---|
| `GITHUB_TOKEN` | Sent as `Authorization: Bearer ...` on GitHub license lookups. Use it if you hit GitHub's API rate limit. |
| `GH_TOKEN` | Used instead when `GITHUB_TOKEN` is not set. |
| `NO_COLOR` | If set to any value (even empty), disables ANSI colors. |

Notes:

- Colors are also off whenever stdout is not a terminal (for example when piped
  or in most CI logs).
- The token is only sent on the license lookup. The separate "is this repo
  public" request is always unauthenticated. <!-- TODO-VERIFY: a private repo, or a rate-limited request, makes that check return false. Confirm that is intended. -->

There are no Hugging Face token settings. Lookups use the public
`https://huggingface.co/api/models/<repo_id>` endpoint without authentication.
<!-- TODO-VERIFY: gated models may return less card data without a token; not tested. -->

## Exit codes

| Code | When |
|---|---|
| `0` | Scan finished and there are no blockers. |
| `1` | At least one finding has severity `blocker` (terminal or `--json`). |
| `2` | Bad arguments, including a `path` that is not a directory (argparse error). |

## Fixed values (not configurable)

These are constants in the source. Changing them means editing the code.

| What | Value | Where |
|---|---|---|
| Skipped folder names | `.git` (handled separately), `node_modules`, `__pycache__`, `.venv`, `venv`, `site-packages`, `.mypy_cache`, `.pytest_cache`, `build`, `dist`, `.cache` | `SKIP_DIRS` in `detect.py` |
| Hidden folders | Any folder name starting with `.` is skipped | `scan()` in `detect.py` |
| Weight file suffixes | `.safetensors`, `.gguf`, `.bin`, `.mlmodelc`, `.mlpackage`, `.onnx`, `.pt`, `.pth`, `.tflite`, `.ckpt` | `WEIGHT_SUFFIXES` |
| License file names | Any file whose name starts with `license`, `licence` or `copying` (any case) | `find_license_file()` |
| License text read | First 200,000 characters of the file, first 20,000 matched | `read()`, `license_from_text()` |
| Network timeouts | 12 s for license lookups, 10 s for the public check | `hf_license()`, `_gh_license()`, `_is_public()` |
| User-Agent | `modelaudit (+https://github.com/nicedreamzapp/modelaudit)` | `UA` |
