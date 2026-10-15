---
title: modelaudit quickstart, scan a project and the Hugging Face cache
description: >-
  Run your first modelaudit scan. Audit a project folder and your Hugging Face
  model cache for GPL, AGPL and non-commercial licenses, pick a ship mode, and
  use JSON output and exit codes in CI.
---

# Quickstart

These steps assume you have cloned the repo and are in its folder. See
[Install](install.md).

## 1. Scan a project

```bash
python3 -m modelaudit ~/MyProject --ship service
```

`--ship` tells the tool how your work reaches other people. It is the single most
important flag. Pick the one that matches reality:

| Mode | Meaning (from `SHIP_MODES` in `licenses.py`) |
|---|---|
| `app` | You distribute a binary, app bundle, or installer to users. |
| `service` | Users reach it over a network. A site, an API, a phone app talking to your server. **Default.** |
| `private` | Only you and your team run it. Nothing leaves the building. |

## 2. Scan your Hugging Face cache

The walk skips every hidden folder, which includes `~/.cache`. Point at the hub
folder directly:

```bash
python3 -m modelaudit ~/.cache/huggingface/hub --ship service
```

Each `models--org--name/snapshots/<hash>` folder is reported once, named
`org/name`. If there is no license file on disk the tool reads the license off the
Hugging Face model card.

## 3. Read the report

Here is real output from a small test folder built while writing these docs, run
with `--offline --ship service --all` (paths shortened):

```
modelaudit  /…/demo/proj
shipping as: service — Users reach it over a network. A site, an API, a phone app talking to your server.
5 dependencies found, offline mode

✗ BLOCKER    example/agpl-thing  (AGPL-3.0, code)
  AGPL over a network — you owe users your source
  ...
  ↳ /…/demo/proj/vendor/agpl
  ↳ license from: /…/demo/proj/vendor/agpl/LICENSE

✗ BLOCKER    sd  (CC-BY-NC-4.0, weights)
  Non-commercial license — you cannot sell what this produces
  ...

· ATTRIBUTIONmit  (MIT, weights)
  Permissive — just keep the notice
  ...

? REVIEW     someorg/tiny  (unknown, weights)
  Custom vendor license — somebody has to read it
  ...

· OK         example/voice-engine  (GPL-3.0, code)
  GPL, but you only run it server-side
  ...

──────────────────────────────────────────────────────────────────────
2 blocker  1 attribution  1 review  1 ok
```

Each finding has:

- a severity and mark (`✗` blocker, `!` obligation, `?` review, `·` attribution or ok)
- the name: `owner/repo` for GitHub checkouts, `org/model` for Hugging Face
  weights, otherwise the folder name
- the license and the kind (`code` or `weights`)
- a headline and a longer explanation
- `↳` the folder it was found in, and `↳ license from:` where the license came from

Without `--all`, `attribution` and `ok` findings are hidden. If nothing is left
to show you get `Nothing to worry about in this mode.`

## 4. Try the other ship modes

The same folder with `--ship app` turns the GPL-3.0 checkout into a blocker
(`3 blocker  1 attribution  1 review`). With `--ship private` the AGPL-3.0
checkout drops to an obligation, while the non-commercial weights stay a blocker
(`1 blocker  1 obligation  1 attribution  1 review  1 ok`).

## 5. Use it in CI

```bash
python3 -m modelaudit . --ship app --json > modelaudit.json
```

The process exits with code `1` when any finding is a blocker, with or without
`--json`, so a CI step fails on its own. See
[Configuration](configuration.md#exit-codes) for the JSON fields and exit codes.

!!! tip "Offline CI"
    Add `--offline` if the CI runner has no internet or you want a deterministic
    result. Licenses that only exist on GitHub or Hugging Face then show as
    `unknown`, which lands in `review`.
