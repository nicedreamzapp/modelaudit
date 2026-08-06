# modelaudit

**Find the license landmines in a local AI stack — including the ones in the model weights.**

I audited my own machine by hand and found three problems I had no idea were there: an
AGPL-3.0 voice-conversion engine sitting one wire-up away from my music service, and two
sets of non-commercial image weights inside a video pipeline. None of it was carelessness.
There was simply nothing that would tell me.

So: one file, no dependencies, runs offline, tells you what you actually owe.

```
python3 -m modelaudit ~/MyProject --ship service
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
| **non-commercial weights** | can't sell it | can't sell it | fine |

GPL and AGPL sit next to each other on the shelf and behave completely differently the
moment there's a network involved. That single distinction is what most of this tool is for.

## What it does

Walks a directory and finds three kinds of thing, because they resolve differently:

- **code** — git checkouts of other people's projects. License from the bundled
  `LICENSE`, falling back to the GitHub API.
- **weights** — downloaded models, including diffusers-style ones like FLUX that keep
  their weights in subfolders and only a `model_index.json` at the root. License from a
  bundled license file, falling back to the Hugging Face model card.
- Then it asks how you ship, and only reports what actually applies.

Every finding says where the license came from, so you can check its work.

## Output

```
✗ BLOCKER    black-forest-labs/FLUX.1-dev  (flux-1-dev-non-commercial-license, weights)
  Non-commercial license — you cannot sell what this produces
  This permits personal and research use but not commercial use. That restriction
  usually follows the output too, not just the software.
  ↳ ~/.cache/huggingface/hub/models--black-forest-labs--FLUX.1-dev/snapshots/3de623f...
  ↳ license from: https://huggingface.co/black-forest-labs/FLUX.1-dev
```

Severity is honest about its own limits:

- **blocker** — a real obligation in the mode you chose
- **obligation** — you owe something, usually attribution or keeping a component separable
- **review** — a vendor license I can't safely interpret. **Not a pass.** Read it.
- **attribution** — permissive, keep the notice

`review` exists because guessing about someone's custom license is worse than admitting
I can't read it. Llama, Gemma and Apple's model licenses all land here on purpose.

## Usage

```
python3 -m modelaudit PATH [--ship app|service|private] [--offline] [--json] [--all]
```

- `--ship` — how it reaches people. Defaults to `service`, the strictest common case.
- `--offline` — never touch the network; use only what's on disk.
- `--json` — for CI. Exits non-zero when there's a blocker.
- `--all` — show the clean results too.

No dependencies. Python 3.8+. Nothing is uploaded anywhere — the only outbound requests
are public license lookups on GitHub and Hugging Face, and `--offline` turns those off.

## What it isn't

Not legal advice. It's a smoke detector — it tells you where to look. The hard cases
(is a converted model a derivative work? does GPL-3.0 satisfy an AGPL-3.0 upstream?) are
genuinely contested, and a tool that answered them confidently would be lying to you.

## License

MIT. See [CREDITS.md](CREDITS.md) for the work this is built on.
