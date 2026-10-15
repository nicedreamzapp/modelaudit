---
title: Install modelaudit
description: >-
  How to install modelaudit, the AI model license scanner. Clone the repository
  and run it with Python 3. No pip package and no third-party dependencies.
---

# Install

There is no pip package yet. You run `modelaudit` from a clone of the repository.

## Requirements

- Python 3. The README states Python 3.8+.
  <!-- TODO-VERIFY: the code has only been run on Python 3.13 while writing these docs; 3.8 is not tested by any CI in the repo. -->
- `git`, to clone the repository.
- No third-party packages. Everything is in Python's standard library
  (`argparse`, `json`, `os`, `re`, `urllib`, `dataclasses`).
- Network access is optional. See [`--offline`](configuration.md#offline).

## Clone and run

```bash
git clone https://github.com/nicedreamzapp/modelaudit
cd modelaudit
python3 -m modelaudit --help
```

`python3 -m modelaudit` works from the repository folder because the package
lives in the `modelaudit/` directory there.

## Run it from anywhere

Put the repository on `PYTHONPATH`:

```bash
export PYTHONPATH="$HOME/src/modelaudit:$PYTHONPATH"   # wherever you cloned it
python3 -m modelaudit ~/MyProject
```

Or add a shell alias:

```bash
alias modelaudit='PYTHONPATH="$HOME/src/modelaudit" python3 -m modelaudit'
```

## Update

```bash
cd modelaudit
git pull
```

## Uninstall

Delete the cloned folder. The tool writes no files, caches or config anywhere on
disk.

## Next

Go to the [Quickstart](quickstart.md).
