"""licenses.py: every license family judged against every ship mode."""

import pytest

from modelaudit.licenses import (
    NEEDS_READING, NONCOMMERCIAL, PERMISSIVE, SEVERITY_ORDER, SHIP_MODES,
    STRONG_COPYLEFT, STRONG_NETWORK_COPYLEFT, WEAK_COPYLEFT, Finding, classify,
)

MODES = ("app", "service", "private")


def sev(lid, mode, kind="code", published=False):
    return classify(lid, mode, kind, published=published)[0]


# The table in the README, row by row.
@pytest.mark.parametrize("lid, app, service, private", [
    ("GPL-3.0", "blocker", "ok", "ok"),
    ("AGPL-3.0", "blocker", "blocker", "obligation"),
    ("flux-1-dev-non-commercial-license", "blocker", "blocker", "blocker"),
])
def test_readme_table(lid, app, service, private):
    assert (sev(lid, "app"), sev(lid, "service"), sev(lid, "private")) == \
        (app, service, private)


@pytest.mark.parametrize("lid", sorted(STRONG_NETWORK_COPYLEFT))
def test_agpl_family(lid):
    assert sev(lid, "service") == "blocker"
    assert sev(lid, "app") == "blocker"
    assert sev(lid, "private") == "obligation"


@pytest.mark.parametrize("lid", sorted(STRONG_COPYLEFT))
def test_gpl_family(lid):
    assert sev(lid, "app") == "blocker"
    assert sev(lid, "service") == "ok"
    assert sev(lid, "private") == "ok"


@pytest.mark.parametrize("lid", sorted(WEAK_COPYLEFT))
def test_weak_copyleft(lid):
    assert sev(lid, "app") == "obligation"
    assert sev(lid, "service") == "ok"
    assert sev(lid, "private") == "ok"


@pytest.mark.parametrize("lid", sorted(NONCOMMERCIAL))
@pytest.mark.parametrize("mode", MODES)
def test_non_commercial_is_always_a_blocker(lid, mode):
    assert sev(lid, mode, kind="weights") == "blocker"


@pytest.mark.parametrize("lid", sorted(NEEDS_READING))
@pytest.mark.parametrize("mode", MODES)
def test_vendor_licenses_need_review(lid, mode):
    assert sev(lid, mode, kind="weights") == "review"


@pytest.mark.parametrize("lid", sorted(PERMISSIVE))
@pytest.mark.parametrize("mode", MODES)
def test_permissive(lid, mode):
    assert sev(lid, mode) == "attribution"


def test_license_sets_do_not_overlap():
    groups = [STRONG_NETWORK_COPYLEFT, STRONG_COPYLEFT, WEAK_COPYLEFT,
              PERMISSIVE, NONCOMMERCIAL, NEEDS_READING]
    lowered = [{x.lower() for x in g} for g in groups]
    for i, a in enumerate(lowered):
        for b in lowered[i + 1:]:
            assert not a & b


# Hugging Face model cards use lowercase ids; detect.py and GitHub use SPDX case.
@pytest.mark.parametrize("hf_id, spdx", [
    ("apache-2.0", "Apache-2.0"), ("mit", "MIT"), ("agpl-3.0", "AGPL-3.0"),
    ("gpl-3.0", "GPL-3.0"), ("lgpl-3.0", "LGPL-3.0"), ("bsd-3-clause", "BSD-3-Clause"),
    ("cc-by-4.0", "CC-BY-4.0"), ("CC-BY-NC-4.0", "cc-by-nc-4.0"), ("LLAMA3", "llama3"),
])
@pytest.mark.parametrize("mode", MODES)
def test_case_insensitive(hf_id, spdx, mode):
    assert classify(hf_id, mode, "weights") == classify(spdx, mode, "weights")


def test_underscores_normalized():
    assert sev("GPL_3.0", "app") == "blocker"


def test_surrounding_whitespace_ignored():
    assert sev("  MIT\n", "app") == "attribution"


@pytest.mark.parametrize("lid", [None, "", "unknown", "other", "NOASSERTION"])
def test_missing_license_is_review_not_pass(lid):
    assert sev(lid, "service") == "review"


def test_unrecognized_license_names_itself():
    s, headline, detail = classify("wtfpl-ish", "service", "code")
    assert s == "review"
    assert "wtfpl-ish" in headline
    assert "permissive" in detail


@pytest.mark.parametrize("lid", sorted(STRONG_NETWORK_COPYLEFT | STRONG_COPYLEFT))
@pytest.mark.parametrize("mode", MODES)
def test_published_copyleft_softens_to_obligation(lid, mode):
    s, headline, _ = classify(lid, mode, "code", published=True)
    assert s == "obligation"
    assert "already public" in headline


@pytest.mark.parametrize("lid", ["LGPL-3.0", "MIT", "cc-by-nc-4.0", "llama3", "mystery"])
def test_published_only_affects_strong_copyleft(lid):
    for mode in MODES:
        assert classify(lid, mode, "code", published=True) == \
            classify(lid, mode, "code", published=False)


@pytest.mark.parametrize("lid", ["AGPL-3.0", "GPL-3.0", "LGPL-2.1", "MIT", "llama3",
                                 "cc-by-nc-4.0", "unknown", "made-up"])
@pytest.mark.parametrize("mode", MODES)
def test_every_result_is_well_formed(lid, mode):
    s, headline, detail = classify(lid, mode, "code")
    assert s in SEVERITY_ORDER
    assert headline.strip() and detail.strip()


def test_ship_modes_and_severity_order():
    assert set(SHIP_MODES) == set(MODES)
    assert sorted(SEVERITY_ORDER, key=SEVERITY_ORDER.get) == \
        ["blocker", "obligation", "attribution", "review", "ok"]


def test_finding_defaults_are_independent():
    a = Finding("p", "n", "MIT", "code", "ok", "h", "d")
    b = Finding("p", "n", "MIT", "code", "ok", "h", "d")
    a.tags.append("x")
    assert b.tags == [] and a.source == ""
