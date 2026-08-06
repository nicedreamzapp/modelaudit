# 🙏 Credits

This tool exists because other people documented the problem first.

| Source | What it gave this project |
|---|---|
| [Ultralytics' licensing page](https://www.ultralytics.com/license) | The clearest plain-English statement of what AGPL-3.0 actually obligates you to do. The AGPL rules in `licenses.py` follow their wording. |
| [Black Forest Labs](https://huggingface.co/black-forest-labs/FLUX.1-dev) | The FLUX split — Apache-2.0 code, non-commercial weights — is the canonical example this whole tool was built around. |
| [Hugging Face Hub API](https://huggingface.co/docs/hub/api) | Model card licenses. This is the data no ordinary dependency scanner reads. |
| ["From Hugging Face to GitHub: Tracing License Drift"](https://arxiv.org/pdf/2509.09873) | Prior research on how license obligations get altered and discarded between dataset, weights and shipped software. |
| [SPDX](https://spdx.org/licenses/) | The license identifiers used throughout. |

There are no runtime dependencies — everything here is Python's standard library — so there
is nothing else to credit. Which is, in a tool about dependency licensing, the point.

---

If your work is listed here and you'd like the wording changed, or if something's missing,
open an issue and I'll fix it.
