---
title: modelaudit changelog
description: >-
  History of changes to modelaudit, the license scanner for local AI models and
  code, taken from the git history of the repository.
---

# Changelog

There are no tagged releases or version numbers yet. This list is built from the
git history of the `main` branch.

## Unreleased

- Test suite (`pytest`, offline, no GPU) and a CI workflow running it on Python
  3.8 to 3.13.
- LGPL-2.1 and MPL-2.0 license files are no longer read as GPL-2.0 and GPL-3.0.
- GitHub repo names containing dots (like `vercel/next.js`) are no longer cut
  short at the first dot.
- Folders holding Core ML `.mlpackage` or `.mlmodelc` bundles are reported as the
  model, instead of a folder named `weights` deep inside the bundle.
- The `ATTRIBUTION` label no longer runs into the dependency name in the terminal
  report.

## 2026-09-27

- README rewritten: plain summary, quick start, a "What I built" section and a
  "Known limits" list.
  ([nicedreamzapp/modelaudit#1](https://github.com/nicedreamzapp/modelaudit/pull/1),
  commit `84b5fc4`)

## 2026-08-06

- **Copyleft in a public repo is no longer a blocker.** If a GPL or AGPL checkout's
  GitHub repo is public, the finding becomes an `obligation` asking you to check
  that your license label matches upstream. Adds the `published` field to `code`
  findings. (commit `9219afc`)
- MIT license and `CREDITS.md` added. (commit `59000cd`)
- First version: scans git checkouts and model weights, reads Hugging Face model
  cards including the `license_name` field, judges each license against
  `--ship app|service|private`, terminal and JSON output. (commit `b0d93f7`)
