"""RB2-01..18: pure offline rule engine with strict negative safety edges."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.core.paths import REPO_ROOT
from app.schemas.p4_rb2_offline_rules import (
    OfflineObservation,
    OfflineRuleError,
    OfflineRuleInput,
    OfflineRulePolicy,
)
from app.services.p4_rb2_offline_rules import evaluate_p4_rb2_offline_fixture

AS_OF = datetime(2026, 11, 14, 12, tzinfo=UTC)


def record(
    name: str,
    *,
    measure: str = "systolic_bp",
    value: str | int = 121,
    days: int = 1,
    measured_at: datetime | None = None,
    created_at: datetime | None = None,
    trust: str = "self_reported_validated",
    source: str = "seed_fixture",
    **changes,
) -> OfflineObservation:
    units = {
        "systolic_bp": "mmHg",
        "diastolic_bp": "mmHg",
        "heart_rate": "bpm",
        "glucose": "mg/dL",
    }
    return OfflineObservation(
        id=name,
        patient_id="demo-patient",
        measure_type=measure,
        value=value,
        unit=units[measure],
        measured_at=measured_at or (AS_OF - timedelta(days=days)),
        validation="ok",
        trust_level=trust,
        created_at=created_at if created_at is not None else AS_OF,
        source=source,
        **changes,
    )


def run(
    current: tuple[OfflineObservation, ...] = (),
    history: tuple[OfflineObservation, ...] = (),
    *,
    policy: OfflineRulePolicy | None = None,
    facts: tuple[str, ...] = (),
):
    return evaluate_p4_rb2_offline_fixture(
        OfflineRuleInput(
            patient_id="demo-patient",
            selected_current=current,
            history=history,
            as_of_utc=AS_OF,
            policy=policy or OfflineRulePolicy(),
            active_fact_verification_statuses=facts,
        )
    )


def ids(result) -> list[str]:
    return [item.rule_id for item in result.flags]


def test_rb2_result_non_authoritative_and_immutable() -> None:
    result = run((record("a"),))
    assert result.demo_only and result.offline_candidate_rules_evaluated
    assert result.runtime_evaluable is False and result.rules_executed is False
    assert result.review_items_persisted is False and result.policy_status == "unapproved"
    assert all(item.demo_only for item in result.flags)
    with pytest.raises(FrozenInstanceError):
        result.runtime_evaluable = True


def test_zero_selected_never_promotes_history_to_current() -> None:
    result = run(history=(record("old", days=120),))
    assert result.flags == ()


def test_180_day_baseline_cannot_be_reused_from_f2_365_day_history() -> None:
    result = run(
        (record("now", value=150),),
        (record("history180", value=80, days=181),),
    )
    assert ids(result) == ["DR-001"]
    assert all(item.rule_id != "DR-005" for item in result.flags)


def test_latest_prior_tiebreak_is_stable_and_reordered_input_invariant() -> None:
    current = record("now", value=140, days=1)
    a = record("a", value=100, days=4)
    b = record("b", value=135, days=4)
    previous = record("older", value=70, days=12)
    first = run((current,), (previous, b, a))
    replay = run((current,), (a, previous, b))
    assert first == replay
    assert not any(item.rule_id == "DR-005" for item in first.flags)
    assert all(
        item.dedupe_key == run((current,), (b, a, previous)).flags[i].dedupe_key
        for i, item in enumerate(first.flags)
    )


@pytest.mark.parametrize(
    ("change", "expected"),
    [(10, False), (Decimal("10.0001"), True), (-11, True)],
)
def test_strict_absolute_delta_greater_than_not_equal(change, expected: bool) -> None:
    now = record("new", value=120 + change)
    past = record("old", value=120, days=2)
    result = run((now,), (past,))
    assert ("DR-005" in ids(result)) is expected


@pytest.mark.parametrize(("age", "stale"), [(29, False), (30, False), (31, True)])
def test_stale_clock_counts_whole_utc_days(age: int, stale: bool) -> None:
    result = run((record("v", days=age),))
    assert ("DR-003" in ids(result)) is stale
    if stale:
        assert "31 days ago" in result.flags[-1].message or any(
            "31 days ago" in item.message for item in result.flags
        )


def test_dr006_requires_independent_distinct_asserted_document_sources() -> None:
    at = AS_OF - timedelta(days=3)
    left = record(
        "left",
        value=112,
        measured_at=at,
        trust="doctor_verified",
        source="verified_document",
        source_document_id="doc-a",
        source_fact_id="fact-a",
        source_fact_verification_status="verified",
        lineage_status="fixture_asserted",
    )
    right = replace(
        left, id="right", value=125, source_document_id="doc-b", source_fact_id="fact-b"
    )
    result = run((left,), (right,))
    assert "DR-006" in ids(result)
    item = next(item for item in result.flags if item.rule_id == "DR-006")
    assert item.provenance_status == "fixture_asserted"
    assert "document:doc-a" in item.evidence and "fact:fact-b" in item.evidence
    assert item.trust_basis == "doctor_verified"
    replay = run((left,), (replace(right, source_document_id="doc-a"),))
    assert "DR-006" not in ids(replay)
    same_fact = run((left,), (replace(right, source_fact_id="fact-a"),))
    assert "DR-006" not in ids(same_fact)
    assert item.message == "Two verified sources disagree for Systolic BP at 2026-11-11T12:00:00Z."


def test_missing_source_lineage_is_excluded_not_promoted() -> None:
    a = record("a", value=100, days=1, trust="doctor_verified", source="verified_document")
    b = replace(a, id="b", value=110)
    result = run((a,), (b,))
    assert "DR-006" not in ids(result)
    assert {r.reason for r in result.excluded} >= {"verified_lineage_unavailable"}


def test_dr008_exact_duplicate_and_measured_created_order_reversal() -> None:
    dup1 = record("a", value=130, days=2)
    dup2 = replace(dup1, id="b")
    result = run((dup2,), (dup1,))
    assert "DR-008" in ids(result)
    first = record(
        "early_created", measured_at=AS_OF - timedelta(days=2), created_at=AS_OF - timedelta(days=1)
    )
    second = record("late_created", measured_at=AS_OF - timedelta(days=5), created_at=AS_OF)
    result = run((first,), (second,))
    assert "DR-008" in ids(result)
    assert next(f for f in result.flags if f.rule_id == "DR-008").message == (
        "A repeated or out-of-order entry was detected for Systolic BP (self-reported)."
    )


def test_missing_created_at_yields_typed_exclusion_not_fake_order() -> None:
    first = record("new", days=2)
    old = replace(record("old", days=4), created_at=None)
    result = run((first,), (old,))
    assert "DR-008" not in ids(result)
    assert any(e.reason == "missing_created_at" for e in result.excluded)


@pytest.mark.parametrize(
    ("value", "emit"),
    [(300, False), (301, True), (50, False), (49, True)],
)
def test_dr009_closed_engineering_band_only(value: int, emit: bool) -> None:
    result = run((record("current", value=value),))
    assert ("DR-009" in ids(result)) is emit
    if emit:
        assert next(x.message for x in result.flags if x.rule_id == "DR-009") == (
            "A recorded value is outside the demo plausibility range and may be a typo "
            "(self-reported)."
        )


def test_self_report_and_mixed_trust_never_promoted() -> None:
    self_report = run((record("self", value=150),), (record("base", value=120, days=5),))
    item = next(x for x in self_report.flags if x.rule_id == "DR-005")
    assert item.trust_basis == "self_reported"
    assert item.message == (
        "Systolic BP differs from the previous recorded value by 30 mmHg (self-reported)."
    )
    mixed = run(
        (record("doc", value=150, trust="doctor_verified", source="verified_document"),),
        (record("base", value=120, days=5),),
    )
    item2 = next(x for x in mixed.flags if x.rule_id == "DR-005")
    assert item2.trust_basis == "mixed"
    assert item2.message.endswith("(includes self-reported values).")


@pytest.mark.parametrize(
    "change",
    [
        {"policy_version": "demo-policy-1.1.1"},
        {"baseline_lookback_days": 365},
        {"stale_measurement_days": 29},
        {"demo_delta_systolic_mmHg": 11},
        {"ocr_confidence_floor": "0.60"},
        {"conflict_tolerance": 1},
        {"max_items_per_type": 4},
        {"enabled_rules": ("DR-005", "DR-002")},
        {"enabled_rules": ("DR-005",)},
        {"enabled_verification_issues": ("VI-001",)},
        {"demo_only": False},
    ],
)
def test_partial_changed_or_retired_policy_fails_closed(change) -> None:
    with pytest.raises(OfflineRuleError) as error:
        run((record("current"),), policy=replace(OfflineRulePolicy(), **change))
    assert error.value.code == "E_RULE_POLICY_INVALID"


def test_forged_authority_fields_are_not_part_of_typed_fixture() -> None:
    values = {
        "patient_id": "demo-patient",
        "selected_current": (),
        "history": (),
        "as_of_utc": AS_OF,
        "policy": OfflineRulePolicy(),
    }
    for forged in ("blocking_fact_count", "run_gate_completed", "policy_status"):
        with pytest.raises(TypeError):
            OfflineRuleInput(**values, **{forged: True})
    with pytest.raises(OfflineRuleError) as error:
        run((record("a"),), facts=("pending",))
    assert error.value.code == "E_UNVERIFIED_FACT"


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"patient_id": "other"}, "E_SCOPE_VIOLATION"),
        ({"measure_type": "fake"}, "E_VALIDATION"),
        ({"source": "patient_checkin", "trust_level": "doctor_verified"}, "E_VALIDATION"),
        ({"lineage_status": "stored_independently_verified"}, "E_VALIDATION"),
        ({"trust_level": "unapproved"}, "E_VALIDATION"),
    ],
)
def test_foreign_patient_forged_source_and_unknown_types_fail_closed(change, expected: str) -> None:
    with pytest.raises(OfflineRuleError) as error:
        run((replace(record("a"), **change),))
    assert error.value.code == expected


def test_rejected_wrong_unit_future_rows_excluded_without_invented_delta() -> None:
    current = record("valid")
    rejected = replace(record("rej"), validation="rejected")
    bad_unit = replace(record("unit"), unit="bpm")
    future = replace(record("future"), measured_at=AS_OF + timedelta(days=1))
    result = run((current,), (rejected, bad_unit, future))
    assert {x.reason for x in result.excluded} == {
        "validation_rejected",
        "unit_mismatch",
        "future_timestamp",
    }
    assert "DR-005" not in ids(result)


def test_cap_excess_fails_closed_without_partial_flags() -> None:
    current = record("now", days=1)
    duplicates = tuple(replace(current, id=f"dup-{i}") for i in range(4))
    with pytest.raises(OfflineRuleError) as error:
        run((current,), duplicates)
    assert error.value.code == "E_RULE_POLICY_INVALID"


def test_dedupe_replay_order_trust_and_no_retired_ids() -> None:
    first = record("now", value=150)
    old = record("old", value=120, days=2)
    result = run((first,), (old,))
    assert result == run((first,), (old,))
    assert len({x.dedupe_key for x in result.flags}) == len(result.flags)
    assert all(len(x.dedupe_key) == 64 for x in result.flags)
    assert all(
        x.workflow_hint in {"data_quality", "verification_needed", "change_to_review"}
        for x in result.flags
    )
    assert all(x.rule_id in OfflineRulePolicy().enabled_rules for x in result.flags)


def test_no_io_run_api_or_agent_imports_in_pure_service() -> None:
    path: Path = REPO_ROOT / "backend/app/services/p4_rb2_offline_rules.py"
    source = path.read_text(encoding="utf-8")
    for forbidden in (
        "from app.db",
        "import sqlalchemy",
        "from app.api",
        "from app.agents",
        "import langgraph",
        "import ollama",
        "import requests",
        "demo_review_policy.yaml",
        "blocking_fact_count",
        "run_gate_completed",
        "session.add",
        "session.commit",
        "review_item",
    ):
        assert forbidden not in source


# RB2-R01: the R3-A instant is independently pinned, not merely self-consistent.
def test_rb2_r01_coordinated_clock_override_fails_and_equal_offsets_normalize() -> None:
    from datetime import timezone

    changed = AS_OF + timedelta(days=1)
    data = OfflineRuleInput(
        "demo-patient",
        (record("a"),),
        (),
        changed,
        replace(OfflineRulePolicy(), demo_as_of_utc=changed),
    )
    with pytest.raises(OfflineRuleError) as error:
        evaluate_p4_rb2_offline_fixture(data)
    assert error.value.code == "E_RULE_POLICY_INVALID"
    offset = AS_OF.astimezone(timezone(timedelta(hours=3)))
    approved = replace(
        data,
        as_of_utc=offset.isoformat(),
        policy=replace(OfflineRulePolicy(), demo_as_of_utc=offset),
    )
    assert evaluate_p4_rb2_offline_fixture(approved) == run((record("a"),))


# RB2-R02: the absence of independently asserted lineage is per observation.
def test_rb2_r02_single_document_lineage_excluded() -> None:
    doc = record("doc", source="verified_document", trust="doctor_verified")
    result = run((doc,))
    assert ("doc", "verified_lineage_unavailable") in {
        (e.observation_id, e.reason) for e in result.excluded
    }
    assert "DR-006" not in ids(result)


# RB2-R03: created-time absence never fabricates ordering, including duplicates.
@pytest.mark.parametrize("missing", [None, "not-a-date", "2026-11-01T12:00:00", 42])
def test_rb2_r03_bad_created_at_per_row_and_duplicate_independent(missing) -> None:
    a = replace(record("a", days=1), created_at=missing)
    b = replace(record("b", days=2), created_at=missing)
    result = run((a,), (b,))
    assert {e.observation_id for e in result.excluded if e.reason == "missing_created_at"} == {
        "a",
        "b",
    }
    assert "DR-008" not in ids(result)
    duplicate = replace(a, id="duplicate")
    result = run((a,), (duplicate,))
    assert "DR-008" in ids(result)
    assert {e.observation_id for e in result.excluded if e.reason == "missing_created_at"} == {
        "a",
        "duplicate",
    }


def test_rb2_r03_one_missing_created_at() -> None:
    result = run((record("a", days=1),), (replace(record("b", days=2), created_at=None),))
    assert [(e.observation_id, e.reason) for e in result.excluded] == [("b", "missing_created_at")]
    assert "DR-008" not in ids(result)


# RB2-R04: the selected type scopes DR-003; historical records never select a type.
def test_rb2_r04_newer_history_dr003_only_does_not_change_current_comparison() -> None:
    selected = record("selected", days=45, value=140)
    newest = record("history", days=5, value=130)
    result = run((selected,), (newest,))
    assert "DR-003" not in ids(result)
    assert "DR-001" in ids(result)
    assert next(f for f in result.flags if f.rule_id == "DR-001").message == (
        "No previous recorded Systolic BP to compare against (self-reported)."
    )
    assert "DR-005" not in ids(result)
    assert result == run((selected,), (newest,))


def test_rb2_r04_stale_newest_history_evidence_trust_template_and_replay() -> None:
    selected = record("selected", days=65, value=130)
    newest = record("newest", days=40, value=130, trust="doctor_verified")
    other = record("other", days=50, value=130)
    result = run((selected,), (newest, other))
    assert result == run((selected,), (other, newest))
    stale = next(flag for flag in result.flags if flag.rule_id == "DR-003")
    assert stale.evidence == ("observation:newest",)
    assert stale.trust_basis == "doctor_verified"
    assert stale.message == "The most recent Systolic BP was recorded 40 days ago."


@pytest.mark.parametrize(
    "change",
    [
        {"validation": "rejected"},
        {"measured_at": AS_OF + timedelta(days=1)},
        {"unit": "bpm"},
        {"measured_at": "invalid"},
    ],
)
def test_rb2_r04_inadmissible_newer_history_cannot_determine_age(change) -> None:
    selected = record("selected", days=45)
    newer = replace(record("newer", days=5), **change)
    stale = next(flag for flag in run((selected,), (newer,)).flags if flag.rule_id == "DR-003")
    assert stale.evidence == ("observation:selected",)
    assert stale.message == "The most recent Systolic BP was recorded 45 days ago (self-reported)."


def test_rb2_r04_unselected_type_and_zero_selected_never_evaluated() -> None:
    selected = record("selected", days=1)
    other_type = record("old-heart", measure="heart_rate", days=60, value=70)
    assert "DR-003" not in ids(run((selected,), (other_type,)))
    assert run((), (other_type,)).flags == ()


def test_rb2_r04_equal_newest_timestamp_stable_tiebreak() -> None:
    selected = record("old", days=60)
    a = record("a", days=40, trust="self_reported_validated")
    b = record("b", days=40, trust="doctor_verified")
    x, y = run((selected,), (a, b)), run((selected,), (b, a))
    assert x == y
    stale = next(f for f in x.flags if f.rule_id == "DR-003")
    assert stale.evidence == ("observation:b",)
    assert stale.trust_basis == "doctor_verified"


@pytest.mark.parametrize(("days", "expected"), [(29, False), (30, False), (31, True)])
def test_rb2_r04_newest_history_whole_day_boundary(days, expected) -> None:
    result = run((record("old", days=60),), (record("new", days=days),))
    assert ("DR-003" in ids(result)) is expected


# RB2-R05: do not silently consume contradictory source-fact assertions.
@pytest.mark.parametrize("status", ["pending", "rejected"])
@pytest.mark.parametrize("as_history", [False, True])
def test_rb2_r05_unverified_fact_assertion_fails_closed(status, as_history) -> None:
    doc = record(
        "doc",
        source="verified_document",
        trust="doctor_verified",
        source_fact_verification_status=status,
    )
    with pytest.raises(OfflineRuleError) as error:
        run((record("current"),) if as_history else (doc,), (doc,) if as_history else (), facts=())
    assert error.value.code == "E_UNVERIFIED_FACT"


# RB2-R06: malformed dataclass fields cannot escape as raw Python exceptions.
@pytest.mark.parametrize(
    "change",
    [
        {"measure_type": []},
        {"id": []},
        {"patient_id": []},
        {"validation": []},
        {"trust_level": []},
        {"source": []},
        {"lineage_status": []},
        {"unit": []},
        {"value": []},
        {"source_fact_verification_status": []},
        {"source_document_id": []},
        {"source_fact_id": []},
        {"id": "a|observation:b"},
        {"id": "a\n"},
        {"id": "\ud800"},
    ],
)
def test_rb2_r06_malformed_fields_are_typed_failures(change) -> None:
    with pytest.raises(OfflineRuleError) as error:
        run((replace(record("a"), **change),))
    assert error.value.code == "E_VALIDATION"


@pytest.mark.parametrize(
    "change",
    [
        {"demo_delta_systolic_mmHg": []},
        {"conflict_tolerance": {}},
        {"enabled_rules": []},
        {"demo_as_of_utc": []},
        {"max_items_per_type": True},
    ],
)
def test_rb2_r06_malformed_policy_is_typed_failure(change) -> None:
    with pytest.raises(OfflineRuleError) as error:
        run((record("a"),), policy=replace(OfflineRulePolicy(), **change))
    assert error.value.code == "E_RULE_POLICY_INVALID"


def test_rb2_r06_bad_active_status_and_patient_id_are_typed() -> None:
    with pytest.raises(OfflineRuleError) as error:
        run((record("a"),), facts=([],))
    assert error.value.code == "E_VALIDATION"
    data = OfflineRuleInput("p|DR-005", (), (), AS_OF, OfflineRulePolicy())
    with pytest.raises(OfflineRuleError) as error:
        evaluate_p4_rb2_offline_fixture(data)
    assert error.value.code == "E_VALIDATION"


def test_rb2_r06_decimal_overflow_fails_closed() -> None:
    huge = record("huge", value="1e999999999")
    with pytest.raises(OfflineRuleError) as error:
        run((huge,), (record("baseline", value=100, days=2),))
    assert error.value.code == "E_VALIDATION"


def test_rb2_evidence_delimiter_collision_is_rejected() -> None:
    # Before the fix, the two distinct evidence pairs serialized identically.
    for first, second in (("a", "b|observation:c"), ("a|observation:b", "c")):
        with pytest.raises(OfflineRuleError) as error:
            run((record(first, value=150),), (record(second, value=100, days=2),))
        assert error.value.code == "E_VALIDATION"
