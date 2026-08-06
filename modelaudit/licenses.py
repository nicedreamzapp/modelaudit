"""What each license actually costs you, depending on how you ship.

The whole point of this file: a license is not "good" or "bad" on its own. GPL-3.0
running on your own server is fine. AGPL-3.0 running on your own server obligates you
to hand your source to every user. Same shelf, completely different outcome.

So every rule here is keyed on *how you ship*, not just on the license name.
"""

from dataclasses import dataclass, field

# How the thing you built reaches other people.
SHIP_MODES = {
    "app": "You distribute a binary, app bundle, or installer to users.",
    "service": "Users reach it over a network. A site, an API, a phone app talking to your server.",
    "private": "Only you and your team run it. Nothing leaves the building.",
}

SEVERITY_ORDER = {"blocker": 0, "obligation": 1, "attribution": 2, "review": 3, "ok": 4}


@dataclass
class Finding:
    path: str
    name: str
    license_id: str
    kind: str                  # "code" | "weights" | "package"
    severity: str              # blocker | obligation | attribution | review | ok
    headline: str
    detail: str
    source: str = ""           # where the license came from, so you can check my work
    tags: list = field(default_factory=list)


# ---------------------------------------------------------------- license facts
#
# `triggers` maps a ship mode to (severity, headline). Anything not listed for a
# mode is treated as no obligation beyond attribution.

STRONG_NETWORK_COPYLEFT = {"AGPL-3.0", "AGPL-3.0-only", "AGPL-3.0-or-later"}
STRONG_COPYLEFT = {"GPL-2.0", "GPL-3.0", "GPL-2.0-only", "GPL-3.0-only",
                   "GPL-3.0-or-later", "GPL-2.0-or-later"}
WEAK_COPYLEFT = {"LGPL-2.1", "LGPL-3.0", "MPL-2.0", "EPL-2.0", "LGPL-3.0-only",
                 "LGPL-2.1-only", "CDDL-1.0"}
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense",
              "0BSD", "Zlib", "PSF-2.0", "BSL-1.0", "MIT-0",
              # Creative Commons variants that do permit commercial use. Attribution
              # (and ShareAlike, where present) still applies to what you ship.
              "CC0-1.0", "CC-BY-4.0", "CC-BY-3.0", "CC-BY-SA-4.0", "CC-BY-SA-3.0"}

# Licenses that forbid or restrict making money, regardless of how you ship.
# Anything whose text says "non-commercial" lands here too — see detect.py, which
# falls back to that label when it can't match a known license but the text is clear.
NONCOMMERCIAL = {
    "CC-BY-NC-4.0", "CC-BY-NC-SA-4.0", "CC-BY-NC-ND-4.0", "CC-BY-NC-2.0",
    "creativeml-openrail-m",  # conditional use restrictions
    "flux-1-dev-non-commercial-license",
    "cc-by-nc-4.0", "cc-by-nc-sa-4.0", "cc-by-nc-nd-4.0",
    "non-commercial (custom)",
}

# Vendor licenses that are not standard open source and genuinely need reading.
NEEDS_READING = {
    "apple-amlr", "apple-ascl", "llama2", "llama3", "llama3.1", "llama3.2",
    "gemma", "gemma-terms-of-use", "other", "unknown", "NOASSERTION",
    "openrail", "bigscience-openrail-m", "stabilityai-ai-community",
    "nvidia-open-model-license", "qwen", "deepseek",
}


def classify(license_id: str, ship_mode: str, kind: str):
    """Return (severity, headline, detail) for one dependency."""
    lid = (license_id or "unknown").strip()
    norm = lid.upper().replace("_", "-")

    if norm in {x.upper() for x in STRONG_NETWORK_COPYLEFT}:
        if ship_mode == "service":
            return ("blocker",
                    "AGPL over a network — you owe users your source",
                    "AGPL-3.0 is the one license where letting people use your software "
                    "over a network counts as distribution. If this is in the request "
                    "path of your service, every user is entitled to the complete "
                    "corresponding source of your whole application. Either publish it "
                    "under AGPL, buy a commercial license, or take this out of the path.")
        if ship_mode == "app":
            return ("blocker",
                    "AGPL in something you distribute — source must ship too",
                    "You are handing this to users, which triggers full copyleft. The "
                    "complete source of the derivative work has to be available under "
                    "AGPL-3.0. Note that AGPL is stricter than GPL; releasing under "
                    "GPL-3.0 alone does not satisfy it.")
        return ("obligation",
                "AGPL, currently internal only",
                "No obligation while nothing leaves your machines. The moment this is "
                "exposed over a network or shipped, it becomes a blocker. Worth knowing "
                "before that day arrives.")

    if norm in {x.upper() for x in STRONG_COPYLEFT}:
        if ship_mode == "app":
            return ("blocker",
                    "GPL in something you distribute — source must ship too",
                    "Distributing a binary built on GPL code obligates you to provide "
                    "the complete corresponding source under a compatible GPL license. "
                    "Also worth checking: GPL and app store terms have a long history of "
                    "friction.")
        if ship_mode == "service":
            return ("ok",
                    "GPL, but you only run it server-side",
                    "Plain GPL attaches its obligations to *distribution*. Running it on "
                    "your own hardware to provide a service is not distribution, so "
                    "nothing is triggered. This is exactly the gap AGPL exists to close, "
                    "so confirm it really is GPL and not AGPL.")
        return ("ok", "GPL, internal use", "No obligations for private use.")

    if norm in {x.upper() for x in WEAK_COPYLEFT}:
        if ship_mode == "app":
            return ("obligation",
                    "Weak copyleft — keep it separable",
                    "Fine to ship alongside proprietary code as long as this component "
                    "stays replaceable: dynamic linking, and its own modifications "
                    "published. Static linking is where people get caught.")
        return ("ok", "Weak copyleft, low risk in this mode", "No practical obligation here.")

    if lid.lower() in {x.lower() for x in NONCOMMERCIAL}:
        return ("blocker",
                "Non-commercial license — you cannot sell what this produces",
                "This permits personal and research use but not commercial use. That "
                "restriction usually follows the *output* too, not just the software. If "
                "anything downstream of this is sold, you need different weights or a "
                "commercial agreement.")

    if lid.lower() in {x.lower() for x in NEEDS_READING}:
        return ("review",
                "Custom vendor license — somebody has to read it",
                "This is not a standard open-source license, so no tool can safely tell "
                "you what it permits. These commonly carry acceptable-use clauses, "
                "naming requirements, or field-of-use limits. Read it before you build a "
                "business on it.")

    if norm in {x.upper() for x in PERMISSIVE}:
        return ("attribution",
                "Permissive — just keep the notice",
                "Use it however you like, commercially included. Keep the copyright "
                "notice and license text with anything you ship.")

    return ("review",
            f"Unrecognized license: {lid}",
            "I could not match this to a license I know. Treat it as unknown and check "
            "it by hand rather than assuming it is permissive.")
