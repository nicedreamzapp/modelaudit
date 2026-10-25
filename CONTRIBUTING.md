# Contributing

Thanks for taking a look. The most useful report is a license `modelaudit` got wrong, in either
direction: a blocker it missed, or a clean project it flagged.

## Reporting a problem

Open an [issue](https://github.com/nicedreamzapp/modelaudit/issues/new/choose). The things that
make it quick to fix:

- the exact command you ran, including `--ship` and `--offline` if you used them
- the finding it printed (or the `--json` output for that entry)
- the repo or Hugging Face model id it was about, and what you think the license really is
- your Python version and OS

## Running it locally

```bash
git clone https://github.com/nicedreamzapp/modelaudit
cd modelaudit
python3 -m modelaudit ~/MyProject --ship service
```

No dependencies, Python 3.8 or newer. Add `--offline` to skip the GitHub and Hugging Face
lookups. Set `GITHUB_TOKEN` or `GH_TOKEN` if you hit GitHub's rate limit.

## Tests

```bash
pip install -r requirements-dev.txt
python3 -m pytest
```

The suite runs offline. Network lookups are mocked, and any test that tries to reach GitHub or
Hugging Face for real fails. CI runs it on Python 3.8 to 3.13. If you fix a misread license,
adding its text as a fixture in `tests/fixtures/licenses/` with a test is the most helpful thing
you can do.

## Pull requests

Small and focused is easiest to review. For big changes, open an issue first so we can talk it
through. Keep the tool free of runtime dependencies. If a change moves a license between
`blocker`, `obligation` and `review`, say why in the PR.

Please follow the [code of conduct](CODE_OF_CONDUCT.md).
