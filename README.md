# modelaudit

**Find the license landmines in a local AI stack — including the ones in the model weights.**

`modelaudit` is a command-line tool that walks a folder, finds the code checkouts and
downloaded model weights in it, and tells you which licenses cause real obligations for
the way you plan to ship.

I audited my own machine by hand and found three problems I had no idea were there: an
AGPL-3.0 voice-conversion engine sitting one wire-up away from my music service, and two
sets of non-commercial image weights inside a video pipeline. None of it was carelessness.
There was simply nothing that would tell me.

So: one small Python package, no dependencies, runs offline, tells you what you actually owe.

## Quick start

There is no pip package yet. Clone it and run it from the repo folder (or put the repo
on `PYTHONPATH`):

```
git clone https://github.com/nicedreamzapp/modelaudit
cd modelaudit
python3 -m modelaudit ~/MyProject --ship service
python3 -m modelaudit ~/.cache/huggingface/hub --ship service
```

The second line scans the Hugging Face cache, which a normal walk skips. On FLUX.1-dev:

```
✗ BLOCKER    black-forest-labs/FLUX.1-dev  (flux-1-dev-non-commercial-license, weights)
  Non-commercial license — you cannot sell what this produces
  This permits personal and research use but not commercial use. That restriction
  usually follows the output too, not just the software.
  ↳ ~/.cache/huggingface/hub/models--black-forest-labs--FLUX.1-dev/snapshots/3de623f...
  ↳ license from: https://huggingface.co/black-forest-labs/FLUX.1-dev
```

## Why existing scanners miss this

**Model weights carry their own license, separate from the code that runs them.**
FLUX is the trap everyone falls into — the code is Apache-2.0, and the weights are under a
non-commercial agreement. A dependency scanner reads your manifests, sees Apache-2.0, and
tells you you're clear. You are not.

Worse, Hugging Face records a bespoke license as the literal string `"other"` and puts the
real name in a different field. Take `"other"` at face value and FLUX.1-dev looks like an
unknown rather than a model you can't sell anything made with. `modelaudit` reads the
second field.

**And whether a license bites depends on how you ship.** This is the part no tool models:

| | you distribute an app | you run a service | internal only |
|---|---|---|---|
| **GPL-3.0** | source must ship | **fine** | fine |
| **AGPL-3.0** | source must ship | **users can demand your source** | fine, until it isn't |
| **non-commercial weights** | can't sell it | can't sell it | still flagged as a blocker |

GPL and AGPL sit next to each other on the shelf and behave completely differently the
moment there's a network involved. That single distinction is what most of this tool is for.

## What it does

Walks a directory and finds two kinds of thing, because they resolve differently:

- **code** — git checkouts of other people's projects. License from the bundled
  `LICENSE`, falling back to the GitHub API.
- **weights** — downloaded models, including diffusers-style ones like FLUX that keep
  their weights in subfolders and only a `model_index.json` at the root. License from a
  bundled license file, falling back to the Hugging Face model card.

Then it asks how you ship, and only reports what actually applies. When it finds a
license, the finding says where it came from, so you can check its work.

## Severity

Severity is honest about its own limits:

- **blocker** — a real obligation in the mode you chose
- **obligation** — you owe something, usually attribution or keeping a component separable
- **review** — a vendor license I can't safely interpret. **Not a pass.** Read it.
- **attribution** — permissive, keep the notice

`review` exists because guessing about someone's custom license is worse than admitting
I can't read it. Llama, Gemma and Apple's model licenses all land here on purpose.

## Usage

```
python3 -m modelaudit PATH [--ship app|service|private] [--offline] [--json] [--all] [--depth N]
```

- `--ship` — how it reaches people. Defaults to `service`, the strictest common case.
- `--offline` — never touch the network; use only what's on disk.
- `--json` — for CI.
- `--all` — show the clean results too.
- `--depth N`: how many folders deep to walk. Defaults to 6.

The exit code is 1 whenever there is a blocker, with or without `--json`.

No dependencies. Python 3.8+. Nothing is uploaded anywhere — the only outbound requests
are public license lookups on GitHub and Hugging Face, and `--offline` turns those off.
Set `GITHUB_TOKEN` or `GH_TOKEN` if you hit GitHub's rate limit.

## What I built

Written by Matt Macosko:

- [`modelaudit/detect.py`](modelaudit/detect.py): the scanner. Finds git checkouts and
  model folders (including diffusers-style ones), matches license text, and reads the
  Hugging Face `license_name` field when the license says `"other"`.
- [`modelaudit/licenses.py`](modelaudit/licenses.py): the rules. Each license family is
  judged against the ship mode (`app`, `service`, `private`), not on its own.
- [`modelaudit/__main__.py`](modelaudit/__main__.py): the command line, terminal report
  and JSON output.

Upstream, not mine: the [GitHub REST API](https://docs.github.com/en/rest) and the
[Hugging Face Hub API](https://huggingface.co/docs/hub/api) for license lookups,
[SPDX](https://spdx.org/licenses/) license identifiers, and Python's standard library.
See [CREDITS.md](CREDITS.md).

## Known limits

- **No pip or npm scanning yet.** Only git checkouts and model weights, not manifests.
- **Hidden folders are skipped**, including `~/.cache`. Point at the HF cache directly.
- **Failed lookups and `--offline`** leave a model with no local license as `unknown`,
  which lands in `review`, never a pass.
- **Online, copyleft in a public GitHub checkout drops** from `blocker` to `obligation`.
  It checks the checkout's own repo, so most AGPL upstreams will show as `obligation`.
- **Only the first checkout without a GitHub remote is reported**, and the folder you
  scan counts as a checkout if it is a git repo.

## What it isn't

Not legal advice. It's a smoke detector — it tells you where to look. The hard cases
(is a converted model a derivative work? does GPL-3.0 satisfy an AGPL-3.0 upstream?) are
genuinely contested, and a tool that answered them confidently would be lying to you.

## License

MIT. See [CREDITS.md](CREDITS.md) for the work this is built on.
