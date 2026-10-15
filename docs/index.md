---
title: AI model license scanner for local weights and code
description: >-
  modelaudit scans a folder for git checkouts and downloaded model weights,
  reads their licenses (including Hugging Face model cards) and tells you which
  ones create real obligations for how you ship. Python, no dependencies.
---

# modelaudit

**Find the license landmines in a local AI stack, including the ones in the model weights.**

`modelaudit` is a small command-line tool. You point it at a folder. It finds the
code checkouts and downloaded model weights inside, works out the license for each
one, and tells you which licenses actually create obligations for the way you plan
to ship: as a distributed app, as a network service, or privately.

```
python3 -m modelaudit ~/.cache/huggingface/hub --ship service
```

On a Hugging Face cache that contains FLUX.1-dev, the finding looks like this
(example output taken from the project README):

```
✗ BLOCKER    black-forest-labs/FLUX.1-dev  (flux-1-dev-non-commercial-license, weights)
  Non-commercial license — you cannot sell what this produces
  This permits personal and research use but not commercial use. That restriction
  usually follows the output too, not just the software.
  ↳ ~/.cache/huggingface/hub/models--black-forest-labs--FLUX.1-dev/snapshots/3de623f...
  ↳ license from: https://huggingface.co/black-forest-labs/FLUX.1-dev
```

[Install](install.md){ .md-button .md-button--primary }
[Quickstart](quickstart.md){ .md-button }

## Who it is for

- People running models locally (Hugging Face downloads, GGUF files, diffusers
  pipelines) who plan to sell something built on them.
- Developers who have cloned other people's projects into their tree and want to
  know whether any of them are GPL or AGPL before shipping.
- Anyone who wants a blocker check in CI: the exit code is `1` whenever a
  blocker is found.

## Why ordinary dependency scanners miss this

**Model weights carry their own license, separate from the code that runs them.**
FLUX.1-dev is the standard example: the code is Apache-2.0, the weights are under a
non-commercial license. A scanner that reads manifests sees Apache-2.0 and reports
nothing.

Hugging Face also records a bespoke license as the literal string `"other"` and
puts the real name in a separate `license_name` field. `modelaudit` reads that
second field, so FLUX.1-dev comes back as `flux-1-dev-non-commercial-license`
instead of an unknown.

**Whether a license matters depends on how you ship.** The rules in
[`licenses.py`](https://github.com/nicedreamzapp/modelaudit/blob/main/modelaudit/licenses.py)
are keyed on the ship mode, not just the license name:

| | `--ship app` | `--ship service` | `--ship private` |
|---|---|---|---|
| **GPL-2.0 / GPL-3.0** | blocker | ok | ok |
| **AGPL-3.0** | blocker | blocker | obligation |
| **LGPL / MPL-2.0 / EPL-2.0 / CDDL-1.0** | obligation | ok | ok |
| **Non-commercial weights or code** | blocker | blocker | blocker |
| **Vendor licenses (Llama, Gemma, Apple, ...)** | review | review | review |
| **MIT / Apache-2.0 / BSD / ...** | attribution | attribution | attribution |

Copyleft code in a checkout whose GitHub repo is public is handled differently.
See [How it works](how-it-works.md#the-published-rule).

## What you get

- Runs on Python's standard library only. No packages to install.
- Works offline with `--offline`. Otherwise the only network calls are public
  license lookups on the GitHub and Hugging Face APIs.
- Every finding says where its license came from (a local file path or a URL),
  so you can check it.
- `review` is never a pass. Licenses the tool cannot safely interpret (Llama,
  Gemma, Apple, unknown) are flagged for a human to read.
- JSON output for CI.

!!! warning "Not legal advice"
    It is a smoke detector. It tells you where to look. Hard questions (is a
    converted model a derivative work? does GPL-3.0 satisfy an AGPL-3.0 upstream?)
    are contested, and the tool does not try to answer them.

## Screenshots

The repository does not contain any screenshots or GIFs yet. The sample output
above is plain text copied from the README.
<!-- TODO-VERIFY: add a terminal screenshot or GIF to the repo and reference it here. -->

## License

modelaudit is released under the [MIT license](https://github.com/nicedreamzapp/modelaudit/blob/main/LICENSE).
