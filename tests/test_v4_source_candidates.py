"""SOURCE candidate metadata and refutation-boundary tests."""
from __future__ import annotations

from types import SimpleNamespace

from semabi.compiler.v4 import source_candidates as candidates
from semabi.compiler.v4.identity import IdentityEvidence, Reading
from semabi.compiler.v4.search import SearchResult


def _reading(template: str, key: str | None, *, status: str, discrimination: float | None,
             copresent_pairs: int = 0) -> Reading:
    slots = tuple(key.split("|")) if key is not None else ()
    evidence = IdentityEvidence(
        copresent_pairs=copresent_pairs,
        separated_pairs=round(copresent_pairs * (discrimination or 0.0)),
    )
    return Reading(template, slots, evidence, status=status)


def _install_search(monkeypatch, result, H=None, G=None):
    H = H or SimpleNamespace(units={})
    G = G or SimpleNamespace()
    monkeypatch.setattr(candidates, "build_hypotheses", lambda *args: (H, G))
    monkeypatch.setattr(candidates.v4_search, "search", lambda *args, **kwargs: result)
    monkeypatch.setattr(candidates.v4_search, "_reload_pairs", lambda log: [])
    monkeypatch.setattr(candidates.v4_search, "_view_of", lambda hyps: {})
    monkeypatch.setattr(candidates.promote, "candidates", lambda *args: [])
    return H, G


def test_generated_alternative_carries_its_own_status_and_discrimination(monkeypatch, tmp_path):
    family = "row[_]"
    template = "row[](cell[_])"
    chosen = _reading(template, "cell#0", status="SUPPORTED", discrimination=0.2,
                      copresent_pairs=10)
    alternative = _reading(template, "cell#1", status="SUPPORTED", discrimination=0.7,
                           copresent_pairs=10)
    result = SearchResult(
        chosen={template: chosen},
        readings={template: [chosen, alternative]},
        families={family: [template]},
        final=SimpleNamespace(to_json=lambda: {}),
    )
    _install_search(monkeypatch, result)

    _result, generated, notes, _H, _G = candidates._source_candidates(
        tmp_path, SimpleNamespace(), refuted={}
    )

    assert generated[1].families[family].status == alternative.status
    assert generated[1].families[family].discrimination == alternative.evidence.discrimination
    assert notes == [{
        "candidate": f"{family[:24]}={alternative.key_slot}",
        "family": family,
        "alternative": alternative.key_slot,
        "status": alternative.status,
        "discrimination": alternative.evidence.discrimination,
    }]


def test_candidate_cap_does_not_report_omitted_alternative(monkeypatch, tmp_path):
    family = "row[_]"
    template = "row[](cell[_])"
    chosen = _reading(template, "cell#0", status="SUPPORTED", discrimination=0.9)
    alternative = _reading(template, "cell#1", status="SUPPORTED", discrimination=0.8)
    result = SearchResult(
        chosen={template: chosen},
        readings={template: [chosen, alternative]},
        families={family: [template]},
        final=SimpleNamespace(to_json=lambda: {}),
    )
    _install_search(monkeypatch, result)

    _result, generated, notes, _H, _G = candidates._source_candidates(
        tmp_path, SimpleNamespace(), max_candidates=1, refuted={}
    )

    assert [candidate.name for candidate in generated] == ["source_choice"]
    assert notes == []


def test_refuted_promotion_is_suppressed_before_candidate_and_summary_emission(
    monkeypatch, tmp_path
):
    leaf = "leaf[]"
    leaf_family = "leaf[_]"
    promoted_unit = SimpleNamespace(template=leaf)
    best = _reading(leaf, "text#0", status="SUPPORTED", discrimination=1.0,
                    copresent_pairs=12)
    result = SearchResult(
        chosen={}, readings={}, families={}, final=SimpleNamespace(to_json=lambda: {}),
    )
    base_H = SimpleNamespace(units={})
    promoted_H = SimpleNamespace(units={leaf: promoted_unit})
    G = SimpleNamespace()

    def build(_source, _log, promoted=None):
        return (promoted_H if promoted else base_H), G

    monkeypatch.setattr(candidates, "build_hypotheses", build)
    monkeypatch.setattr(candidates.v4_search, "search", lambda *args, **kwargs: result)
    monkeypatch.setattr(candidates.v4_search, "_reload_pairs", lambda log: [])
    monkeypatch.setattr(candidates.v4_search, "_view_of", lambda hyps: {})
    monkeypatch.setattr(candidates.promote, "candidates", lambda *args: [leaf])
    monkeypatch.setattr(candidates, "family_readings", lambda *args, **kwargs: [best])

    _result, generated, notes, _H, _G = candidates._source_candidates(
        tmp_path, SimpleNamespace(), refuted={leaf_family: {best.key_slot}}
    )

    assert len(generated) == 1
    assert notes == []


def test_refuted_alternative_is_suppressed_before_candidate_and_summary_emission(
    monkeypatch, tmp_path
):
    family = "row[_]"
    template = "row[](cell[_])"
    chosen = _reading(template, "cell#0", status="SUPPORTED", discrimination=0.9)
    alternative = _reading(template, "cell#1", status="SUPPORTED", discrimination=0.8)
    result = SearchResult(
        chosen={template: chosen},
        readings={template: [chosen, alternative]},
        families={family: [template]},
        final=SimpleNamespace(to_json=lambda: {}),
    )
    _install_search(monkeypatch, result)

    _result, generated, notes, _H, _G = candidates._source_candidates(
        tmp_path, SimpleNamespace(), refuted={family: {alternative.key_slot}}
    )

    assert len(generated) == 1
    assert notes == []


def test_generated_promotion_carries_actual_metadata_and_copresent_count(monkeypatch, tmp_path):
    leaf = "leaf[]"
    leaf_family = "leaf[_]"
    promoted_unit = SimpleNamespace(template=leaf)
    best = _reading(leaf, "text#0", status="SUPPORTED", discrimination=0.75,
                    copresent_pairs=12)
    result = SearchResult(
        chosen={}, readings={}, families={}, final=SimpleNamespace(to_json=lambda: {}),
    )
    base_H = SimpleNamespace(units={})
    promoted_H = SimpleNamespace(units={leaf: promoted_unit})
    G = SimpleNamespace()

    def build(_source, _log, promoted=None):
        return (promoted_H if promoted else base_H), G

    monkeypatch.setattr(candidates, "build_hypotheses", build)
    monkeypatch.setattr(candidates.v4_search, "search", lambda *args, **kwargs: result)
    monkeypatch.setattr(candidates.v4_search, "_reload_pairs", lambda log: [])
    monkeypatch.setattr(candidates.v4_search, "_view_of", lambda hyps: {})
    monkeypatch.setattr(candidates.promote, "candidates", lambda *args: [leaf])
    monkeypatch.setattr(candidates, "family_readings", lambda *args, **kwargs: [best])

    _result, generated, notes, _H, _G = candidates._source_candidates(
        tmp_path, SimpleNamespace(), refuted={}
    )

    assert generated[1].families[leaf_family].status == best.status
    assert generated[1].families[leaf_family].discrimination == best.evidence.discrimination
    assert notes == [{
        "candidate": f"promote {leaf_family[:22]}={best.key_slot}",
        "family": leaf_family,
        "promotion": best.key_slot,
        "status": best.status,
        "discrimination": best.evidence.discrimination,
        "copresent_pairs": best.evidence.copresent_pairs,
    }]
