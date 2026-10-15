---
title: modelaudit troubleshooting, common errors and surprising results
description: >-
  Fixes for common modelaudit problems: "not a directory" errors, the Hugging
  Face cache not being scanned, everything showing as unknown or review, GitHub
  rate limits, AGPL showing as obligation, and misidentified licenses.
---

# Troubleshooting

The GitHub issue tracker for this repo had no issues when this page was written,
so everything here comes from the error messages and behavior in the code, plus
test runs made while writing the docs.

## `modelaudit: error: not a directory: PATH`

The `path` argument must be an existing directory. The tool exits with code `2`.
Check for typos, and note that `~` is expanded by the tool but other shell syntax
in quotes is not.

## The Hugging Face cache is not scanned / `0 dependencies found`

Any folder whose name starts with `.` is skipped, and `.cache` is also in
`SKIP_DIRS`. Scanning your home folder will never reach `~/.cache/huggingface`.
Point at the hub folder:

```bash
python3 -m modelaudit ~/.cache/huggingface/hub
```

The same applies to models kept under any hidden folder, or under folders named
`build`, `dist`, `node_modules`, `venv`, `site-packages`, `__pycache__`,
`.mypy_cache` or `.pytest_cache`.

Also check `--depth`. With the default `6`, folders five levels below the root
are the deepest ones inspected. Raise it for deep trees.

## Everything shows as `unknown` / `review`

A license is `unknown` when no local license file was recognized **and** the
online lookup was skipped or failed. Causes:

- You used `--offline`.
- No network, a proxy blocking `api.github.com` or `huggingface.co`, or a
  timeout (12 seconds). Network errors are swallowed silently; there is no error
  message.
- A model folder has no Hugging Face repo id: no `models--org--name` in its path
  and no `_name_or_path` / `name_or_path` / `model_name` with a `/` in
  `config.json`. Then there is nothing to look up.
- A checkout's remote is not on `github.com`.
- The Hugging Face card or GitHub repo has no license recorded.

`unknown` always lands in `review`, never in a pass. Add a license file next to
the weights or read the model card yourself.

## GitHub rate limit

GitHub limits unauthenticated API requests. When a lookup fails it is treated
like any other network failure (license `unknown`, no message). Set a token:

```bash
export GITHUB_TOKEN=ghp_yourtoken    # or GH_TOKEN
```

The token is only used for the license lookup. The "is this repo public" check is
always unauthenticated, so on a rate limit it returns `false` and copyleft
findings stay `blocker`.

## AGPL shows as `obligation`, not `blocker`

Online, if a GPL or AGPL checkout's own GitHub repo is public, it is reported as
`obligation` with "Copyleft, and your source is already public — check the label
matches". This happens for most cloned upstream projects. See
[the published rule](how-it-works.md#the-published-rule). Run with `--offline` to
see the unsoftened severity.

## Only one of my non-GitHub checkouts shows up

Checkouts are de-duplicated by GitHub `owner/repo`. Every checkout without a
GitHub remote shares the same empty key, so only the first one found is reported.
This is a known limit in the README.

## My own project appears as a finding

If the folder you scan is a git repository, it counts as a checkout and is
reported like any other.

## A code folder is reported as `weights`

A folder counts as a model if it has a file ending in `.bin`, `.pt`, `.pth`,
`.ckpt` (and the other weight suffixes), a `model_index.json`, or a `config.json`
next to any file whose name starts with `model`. A source folder holding
`config.json` and `model.py` matches the last rule. The walk also stops descending
at that folder.

## A license is identified wrongly

License text is matched with simple substring signatures. Running the matcher over the license texts that ship with Debian in
`/usr/share/common-licenses` gave these results:

| File | Identified as |
|---|---|
| `Apache-2.0` | `Apache-2.0` |
| `BSD` | `BSD-3-Clause` |
| `GPL-2` | `GPL-2.0` |
| `GPL-3` | `GPL-3.0` |
| `LGPL-3` | `LGPL-3.0` |
| `LGPL-2.1` | `LGPL-2.1` |
| `MPL-2.0` | `MPL-2.0` |
| `LGPL-2` | `GPL-2.0` (wrong) |
| `GFDL-1.2`, `GFDL-1.3` | `non-commercial (custom)` (wrong) |
| `GPL-1` | `non-commercial (custom)` (wrong) |
| `CC0-1.0`, `Artistic`, `MPL-1.1` | not recognized |

`LGPL-2` is the older GNU *Library* General Public License, which has no
signature of its own, so the GPL-2.0 one matches. The GFDL and GPL-1 texts
contain the word "noncommercially", which triggers the non-commercial fallback. The `license from:`
line tells you which file was read, so check it by hand.
<!-- TODO-VERIFY: results above are from Debian's copies of these texts; other copies with different line wrapping may match differently. -->

If the file is not recognized at all and the network is allowed, the GitHub or
Hugging Face license is used instead.

## Colors in logs / garbage escape codes

Colors are only used when stdout is a terminal and `NO_COLOR` is unset. If your
terminal still shows escape codes, set `NO_COLOR=1`.

## CI fails even though the scan worked

Exit code `1` means at least one `blocker` was found. That is deliberate. Check the
`--ship` mode is right, then fix or replace the blocking dependency.

## Still stuck?

Open an issue at
[github.com/nicedreamzapp/modelaudit/issues](https://github.com/nicedreamzapp/modelaudit/issues)
with the command you ran and the `--json` output.
