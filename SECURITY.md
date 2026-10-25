# Security policy

## Reporting a vulnerability

Please do not open a public issue for security problems.

Report them privately through GitHub: go to the **Security** tab of this repo and click **Report a vulnerability** ([direct link](https://github.com/nicedreamzapp/modelaudit/security/advisories/new)). Only the maintainer sees the report.

Helpful details: what you found, how to reproduce it, which version or commit, your Python version and OS, and a small folder or file that triggers it if you have one.

I aim to reply within 3 days and to ship a fix or a clear plan within 30 days, depending on severity. You will be credited in the advisory unless you ask not to be.

## Supported versions

Fixes go into the latest version on `main`. Please update before reporting if you are on an older commit.

## What matters most here

The parts where a mistake could hurt someone:

- `GITHUB_TOKEN` and `GH_TOKEN`, read from the environment in `modelaudit/detect.py` and sent only to the GitHub API
- the directory walk and file reading in `modelaudit/detect.py`, which open license files, `model_index.json` and other files inside folders the user did not write
- the GitHub and Hugging Face lookups in `modelaudit/detect.py`, which parse JSON from the network
- the license rules in `modelaudit/licenses.py`, where a wrong rule could report a blocker as clean
