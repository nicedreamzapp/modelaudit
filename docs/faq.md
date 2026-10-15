---
title: modelaudit FAQ, model weight licenses, AGPL vs GPL, and more
description: >-
  Answers to common questions about modelaudit: is it legal advice, does it
  upload anything, why Llama and Gemma show as review, why GPL is fine for a
  service but AGPL is not, pip/npm support, and CI use.
---

# FAQ

## Is this legal advice?

No. It is a smoke detector that tells you where to look. Contested questions, like
whether a converted model is a derivative work or whether GPL-3.0 satisfies an
AGPL-3.0 upstream, are not answered by the tool.

## Does it upload my code or models anywhere?

No. It never sends file contents. The only outbound requests are public license
lookups:

- `https://api.github.com/repos/<owner>/<repo>` for checkouts with a GitHub remote
- `https://huggingface.co/api/models/<org>/<name>` for weights with a known repo id

`--offline` turns all of them off.

## Why do model weights need their own check?

Weights are often licensed separately from the code that runs them. FLUX.1-dev
has Apache-2.0 code and non-commercial weights. A scanner that only reads code
licenses would say you are clear.

## Why is FLUX.1-dev flagged when Hugging Face says "other"?

Hugging Face stores custom licenses as `license: other` and puts the real name in
`license_name`. modelaudit reads `license_name` when the license is `other` or
`unknown`, which gives `flux-1-dev-non-commercial-license`, a blocker.

## Why are Llama, Gemma and Apple models marked `review`?

They use vendor licenses that are not standard open source and can carry
acceptable-use or field-of-use terms. The tool puts them in `review` on purpose
instead of guessing. `review` is not a pass.

## Why is GPL fine for a service but AGPL is not?

GPL obligations attach to distribution. Running GPL code on your own server is not
distribution. AGPL-3.0 counts network use as distribution, so users of a service
can request your source. That is why `--ship` exists.

## Why are non-commercial weights a blocker even with `--ship private`?

The non-commercial rule in `licenses.py` does not look at the ship mode. Its
explanation is that the restriction usually follows the output too, so if anything
made with it is sold, it is a problem.

## Does it scan pip or npm dependencies?

Not yet. Only git checkouts and model weights.

## Is there a pip package?

Not yet. Clone the repo and run `python3 -m modelaudit`. See [Install](install.md).

## Which Python versions work?

The README says 3.8+, and it has no third-party dependencies.
<!-- TODO-VERIFY: only tested on Python 3.13 while writing these docs. -->

## Does it work on Windows?

<!-- TODO-VERIFY: untested. The Hugging Face cache snapshot check converts path separators, but the repo id regex in hf_repo_id() assumes "/" separators, so names for cache entries may come out wrong on Windows. -->
Not tested. The Hugging Face cache check converts path separators, but the code that turns a cache path into a repo id assumes `/` separators, so model names from a Windows cache may come out wrong.

## Can I use it in CI?

Yes. It exits with code `1` when there is a blocker and `--json` gives structured
output. See [Quickstart](quickstart.md#5-use-it-in-ci).

## How do I get results without the network softening AGPL?

Use `--offline`. The "already public" check needs the network, so offline copyleft
findings are never softened.

## What license is modelaudit under?

MIT.
