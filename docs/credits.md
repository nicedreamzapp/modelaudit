---
title: modelaudit credits and upstream sources
description: >-
  The projects, data sources and research that modelaudit builds on: the
  Hugging Face Hub API, the GitHub REST API, SPDX, Ultralytics' AGPL guidance,
  Black Forest Labs' FLUX.1-dev, and MkDocs Material for this site.
---

# Credits

modelaudit was written by Matt Macosko. It is built on, and depends on, other
people's work.

## Data sources and prior work

From the repo's [CREDITS.md](https://github.com/nicedreamzapp/modelaudit/blob/main/CREDITS.md):

| Source | What it gave this project |
|---|---|
| [Ultralytics' licensing page](https://www.ultralytics.com/license) | A plain-English statement of what AGPL-3.0 obligates. The AGPL rules in `licenses.py` follow their wording. |
| [Black Forest Labs, FLUX.1-dev](https://huggingface.co/black-forest-labs/FLUX.1-dev) | The FLUX split (Apache-2.0 code, non-commercial weights) is the example the tool was built around. |
| [Hugging Face Hub API](https://huggingface.co/docs/hub/api) | Model card licenses, read at runtime. |
| [GitHub REST API](https://docs.github.com/en/rest) | Repository licenses and public/private status, read at runtime. |
| ["From Hugging Face to GitHub: Tracing License Drift"](https://arxiv.org/pdf/2509.09873) | Prior research on how license obligations change between dataset, weights and shipped software. |
| [SPDX](https://spdx.org/licenses/) | The license identifiers used throughout. |

The tool itself only uses Python's standard library.

## This documentation site

Built with [MkDocs](https://www.mkdocs.org/) and
[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/), and hosted on
GitHub Pages.

## Wording changes

If your work is listed here and you would like the wording changed, or something
is missing, [open an issue](https://github.com/nicedreamzapp/modelaudit/issues).
