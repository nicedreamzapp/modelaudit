---
title: How modelaudit works, detection and license rules
description: >-
  Architecture of modelaudit: how it walks a folder, detects git checkouts and
  model weights (including Hugging Face cache snapshots and diffusers models),
  resolves licenses from files, GitHub and Hugging Face, and assigns severity by ship mode.
---

# How it works

The whole tool is three Python files, about 550 lines in total:

| File | Job |
|---|---|
| [`modelaudit/detect.py`](https://github.com/nicedreamzapp/modelaudit/blob/main/modelaudit/detect.py) | Walks the folder, finds checkouts and model folders, works out each license. |
| [`modelaudit/licenses.py`](https://github.com/nicedreamzapp/modelaudit/blob/main/modelaudit/licenses.py) | The rules. Turns `(license, ship mode)` into a severity and an explanation. |
| [`modelaudit/__main__.py`](https://github.com/nicedreamzapp/modelaudit/blob/main/modelaudit/__main__.py) | Command line, terminal report, JSON output, exit code. |

```
path ──► scan()  ──► [{kind, path, name, license, source, published?}, ...]
          detect.py              │
                                 ▼
                     classify(license, ship, kind, published)
                          licenses.py
                                 │
                                 ▼
               sort by severity ──► report or JSON ──► exit 0 / 1
                              __main__.py
```

## 1. The walk

`scan()` uses `os.walk` from the root you give it.

- Folder depth is counted from the root (root is `0`). At depth `--depth` or more
  the walk stops going down.
- Folders in `SKIP_DIRS` and any folder whose name starts with `.` are skipped.
  `~/.cache` is skipped for this reason, so scan `~/.cache/huggingface/hub` directly.
- Each folder is checked as a git checkout first, then as a model folder.

## 2. Git checkouts (`kind: code`)

A folder counts as a checkout if it contains `.git` (a directory, or a file as in
submodules and worktrees).

1. The remote URL is the first `url = ...` line in `.git/config`. If it points at
   `github.com`, the name becomes `owner/repo`.
2. The license comes from the first file (sorted by name) starting with `license`,
   `licence` or `copying`, matched by text (see [license matching](#license-matching)).
3. If that gives nothing and the network is allowed, it asks
   `https://api.github.com/repos/owner/repo` for the SPDX id. `NOASSERTION` counts as nothing.
4. If the network is allowed, a second request to the same endpoint checks
   whether the repo is public. This sets `published`.

Checkouts are de-duplicated by GitHub slug. Every checkout without a GitHub remote
has the slug `None`, so only the **first** of them is reported. This is a known
limit listed in the README.

The walk keeps going into a checkout's subfolders, so vendored models or nested
checkouts inside it are still found.

## 3. Model weights (`kind: weights`)

A folder is treated as a model when any of these is true:

- its path ends in a Hugging Face cache snapshot,
  `models--<org>--<name>/snapshots/<hex hash>`;
- it holds a file ending in `.safetensors`, `.gguf`, `.bin`, `.mlmodelc`,
  `.mlpackage`, `.onnx`, `.pt`, `.pth`, `.tflite` or `.ckpt`, or a Core ML
  bundle folder ending in `.mlpackage` or `.mlmodelc`;
- it holds `model_index.json` (diffusers models such as FLUX and Stable Diffusion
  keep their weights in subfolders);
- it holds `config.json` and any file whose name starts with `model`.

Once a folder is a model, the walk does not go inside it. That keeps a
multi-part diffusers model as one finding.

The Hugging Face repo id comes from the `models--org--name` part of the path, or
else from `_name_or_path`, `name_or_path` or `model_name` in `config.json` (a value
containing `/` that does not start with `/`).

License resolution:

1. A local license file, matched by text.
2. If none was recognized and there is a repo id and the network is allowed,
   `https://huggingface.co/api/models/<repo_id>` is read. The license is
   `cardData.license` (first item if it is a list). If that is missing, `other`
   or `unknown`, `cardData.license_name` is used instead. This is how FLUX.1-dev
   resolves to `flux-1-dev-non-commercial-license`.
3. Otherwise `unknown`.

## License matching

`license_from_text()` reads the first 20,000 characters and checks these
signatures case-insensitively. A signature matches when every string is present.
License texts name each other (LGPL-2.1 builds on "the GNU General Public
License", MPL-2.0 lists the GPL family as secondary licenses), so when several
match, the one whose first string appears earliest in the text wins. That is
normally the license's own title. Ties go to the earlier row:

| Result | Must contain |
|---|---|
| `AGPL-3.0` | "GNU AFFERO GENERAL PUBLIC LICENSE" |
| `GPL-3.0` | "GNU GENERAL PUBLIC LICENSE" and "Version 3" |
| `GPL-2.0` | "GNU GENERAL PUBLIC LICENSE" and "Version 2" |
| `LGPL-3.0` | "GNU LESSER GENERAL PUBLIC LICENSE" and "Version 3" |
| `LGPL-2.1` | "GNU LESSER GENERAL PUBLIC LICENSE" and "Version 2.1" |
| `Apache-2.0` | "Apache License" and "Version 2.0" |
| `MPL-2.0` | "Mozilla Public License Version 2.0" |
| `BSD-3-Clause` | "Redistribution and use in source and binary forms" and "Neither the name of" |
| `BSD-2-Clause` | "Redistribution and use in source and binary forms" |
| `ISC` | "Permission to use, copy, modify, and/or distribute this software" |
| `Unlicense` | "This is free and unencumbered software released into the public domain" |
| `MIT` | "Permission is hereby granted, free of charge" |
| `CC-BY-NC-SA-4.0` | "Attribution-NonCommercial-ShareAlike" |
| `CC-BY-NC-4.0` | "Attribution-NonCommercial" |
| `CC-BY-SA-4.0` | "Attribution-ShareAlike" |

If nothing matches but the text contains "non-commercial" or "noncommercial", the
result is `non-commercial (custom)`, which is a blocker.

Substring matching can still misread some texts. See
[Troubleshooting](troubleshooting.md#a-license-is-identified-wrongly).

## Severity rules

`classify()` in `licenses.py` checks these groups in this order. The first match decides.

| Group | Licenses (as in the code) | `app` | `service` | `private` |
|---|---|---|---|---|
| Network copyleft | `AGPL-3.0`, `-only`, `-or-later` | blocker | blocker | obligation |
| Strong copyleft | `GPL-2.0`, `GPL-3.0` and their `-only` / `-or-later` forms | blocker | ok | ok |
| Weak copyleft | `LGPL-2.1`, `LGPL-3.0`, `MPL-2.0`, `EPL-2.0`, `CDDL-1.0` (+ some `-only` forms) | obligation | ok | ok |
| Non-commercial | `CC-BY-NC-*`, `creativeml-openrail-m`, `flux-1-dev-non-commercial-license`, `non-commercial (custom)` | blocker | blocker | blocker |
| Needs reading | `apple-amlr`, `apple-ascl`, `llama2`, `llama3`, `llama3.1`, `llama3.2`, `gemma`, `gemma-terms-of-use`, `openrail`, `bigscience-openrail-m`, `stabilityai-ai-community`, `nvidia-open-model-license`, `qwen`, `deepseek`, `other`, `unknown`, `NOASSERTION` | review | review | review |
| Permissive | `MIT`, `Apache-2.0`, `BSD-2/3-Clause`, `ISC`, `Unlicense`, `0BSD`, `Zlib`, `PSF-2.0`, `BSL-1.0`, `MIT-0`, `CC0-1.0`, `CC-BY-4.0`, `CC-BY-3.0`, `CC-BY-SA-4.0`, `CC-BY-SA-3.0` | attribution | attribution | attribution |
| Anything else | | review ("Unrecognized license") | review | review |

Copyleft ids are compared upper-cased with `_` turned into `-`, so Hugging Face's
lower-case `agpl-3.0` matches. The non-commercial and needs-reading lists are
compared lower-cased.

`creativeml-openrail-m` sits in the non-commercial group in the code, with the
comment "conditional use restrictions".
<!-- TODO-VERIFY: CreativeML OpenRAIL-M generally permits commercial use with use-based restrictions. Confirm that treating it as a non-commercial blocker is intended. -->

### The severity levels

- **blocker**: a real obligation in the mode you chose. Causes exit code `1`.
- **obligation**: you owe something, usually attribution or keeping a component separable.
- **review**: a license the tool cannot safely interpret. Not a pass.
- **attribution**: permissive, keep the notice.
- **ok**: nothing triggered in this mode (only shown with `--all`).

### The published rule

Before any of the groups above, `classify()` checks whether the finding is
`published` and its license is GPL or AGPL. If so, the result is always
**obligation** with the headline "Copyleft, and your source is already public —
check the label matches", whatever the ship mode.

`published` is only ever true for `code` findings, online, when the GitHub API says
the checkout's own repo is not private. The README notes the side effect: most
AGPL upstreams you have cloned are public, so they show as `obligation`, not
`blocker`.

Two things follow from the code as written:

- It is the checkout's repo that is checked, not your own project's repo.
  <!-- TODO-VERIFY: the docstring describes "the source of the thing using this" as public; the code checks the dependency's repo. -->
- A public GPL checkout in `--ship service` or `--ship private` becomes
  `obligation`, where an unpublished one would be `ok`.
  <!-- TODO-VERIFY: confirm this upgrade from ok to obligation is intended. -->

## Output

`__main__.py` sorts findings by severity, then name. The terminal report prints a
header (path, ship mode, count), one block per finding, a summary line of counts,
and a note when any `review` findings exist. JSON output is described in
[Configuration](configuration.md#json).

## What is not scanned

- pip, npm and other package manifests. The `Finding` dataclass and docstrings
  mention a `package` kind, but nothing in the code produces it.
- Datasets.
- License text inside source file headers.
