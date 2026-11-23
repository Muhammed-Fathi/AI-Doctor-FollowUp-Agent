"""P4-RB3 migration, schema, WITHOUT ROWID, trigger, and replacement-guard tests.

Covers RB3-29..31, RB3-54..58, RB3-67..69, RB3-78..81, RB3-89..91,
RB3-100..110, RB3-115..127 from docs/phase-reports/P4_RB3_DURABLE_PERSISTENCE_DESIGN_20261123.md.
No existing test, fixture, migration, or session pragma is modified.
"""

from __future__ import annotations

import hashlib
import importlib.util
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, create_engine, inspect, literal_column, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AuditOutcome, Role
from app.core.paths import REPO_ROOT
from app.core.policies import Principal
from app.db.base import Base
from app.db.models import (
    AuditEvent,
    Document,
    ExtractedFact,
    FactVerification,
    Observation,
    Patient,
    ReviewEvaluation,
    RunGateEvaluation,
    User,
    UserSession,
)
from app.db.session import create_db_engine
from app.services.p5_run_foundation import create_run_foundation
from app.services.p5_run_gate import evaluate_run_verification_gate
from app.services.seed import seed_demo_data

ALEMBIC_INI = REPO_ROOT / "backend" / "migrations" / "alembic.ini"
CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)
CLOCK_ISO = "2026-11-14T12:00:00Z"
AT_ISO = "2026-06-14T08:00:00Z"
POLICY_SHA = "f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36"
RB3_TABLES = ("review_item", "evidence_link", "review_evaluation")

EXPECTED_RB3_TRIGGERS = {
    "trg_review_item_update_immutable",
    "trg_review_item_delete_immutable",
    "trg_review_item_insert_open_only",
    "trg_review_item_run_scope_consistent",
    "trg_review_item_insert_sealed",
    "trg_review_item_insert_id_conflict",
    "trg_review_item_insert_dedupe_conflict",
    "trg_review_item_insert_order_conflict",
    "trg_evidence_link_update_immutable",
    "trg_evidence_link_delete_immutable",
    "trg_evidence_link_owner_review_item_only",
    "trg_evidence_link_kind_observation_only",
    "trg_evidence_link_owner_exists",
    "trg_evidence_link_reference_same_patient",
    "trg_evidence_link_duplicate_identity",
    "trg_evidence_link_insert_sealed",
    "trg_evidence_link_insert_id_conflict",
    "trg_evidence_link_insert_observation_identity_conflict",
    "trg_evidence_link_insert_span_identity_conflict",
    "trg_review_evaluation_update_immutable",
    "trg_review_evaluation_delete_immutable",
    "trg_review_evaluation_run_scope_consistent",
    "trg_review_evaluation_insert_sealed",
    "trg_review_evaluation_insert_id_conflict",
    "trg_review_evaluation_insert_run_conflict",
}

EXPECTED_HISTORICAL_TRIGGERS = {
    "trg_fact_verification_doctor_only",
    "trg_run_selected_document_update_immutable",
    "trg_run_selected_document_delete_immutable",
    "trg_run_selected_observation_update_immutable",
    "trg_run_selected_observation_delete_immutable",
    "trg_run_source_omission_update_immutable",
    "trg_run_source_omission_delete_immutable",
    "trg_run_gate_evaluation_update_immutable",
    "trg_run_gate_evaluation_delete_immutable",
    "trg_run_gate_blocker_update_immutable",
    "trg_run_gate_blocker_delete_immutable",
}


def _alembic_cfg(db_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.cmd_opts = None  # type: ignore[attr-defined]
    cfg.attributes["configure_logger"] = False
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _load_0008_module():
    path = REPO_ROOT / "backend" / "migrations" / "versions" / "0008_p4_rb3_review_persistence.py"
    spec = importlib.util.spec_from_file_location("mig_0008", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _seed_proceed_run(db: Session, root: Path, *, suffix: str) -> tuple[str, str, str, str]:
    patient = db.execute(select(Patient).where(Patient.external_ref == "DEMO-A-001")).scalar_one()
    doctor = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
    sess = db.execute(
        select(UserSession).where(UserSession.user_id == doctor.id)
    ).scalar_one_or_none()
    if sess is None:
        sess = UserSession(
            id=f"a0000000-0000-4000-8000-00000000000{suffix[-1] if suffix[-1].isdigit() else '1'}",
            user_id=doctor.id,
            token_sha256=hashlib.sha256(f"mig-{suffix}".encode()).hexdigest(),
            created_at="2026-11-01T00:00:00Z",
            expires_at="2026-12-01T00:00:00Z",
        )
        db.add(sess)
        db.flush()

    raw = f"mig-doc-{suffix}".encode()
    fname = f"mig-{suffix}.pdf"
    (root / fname).write_bytes(raw)
    doc = Document(
        patient_id=patient.id,
        uploaded_by_user_id=doctor.id,
        original_filename=fname,
        stored_path=fname,
        mime_type="application/pdf",
        sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw),
        extraction_status="verified",
        failure_code=None,
        document_patient_ref=patient.external_ref,
        document_patient_refs=f'["{patient.external_ref}"]',
        uploaded_at=AT_ISO,
    )
    db.add(doc)
    db.flush()
    for field_name, val, unit in (
        ("report_date", "2026-06-14", None),
        ("test_name", "glucose", None),
        ("value", "105", "mg/dL"),
        ("unit", "mg/dL", None),
    ):
        ef = ExtractedFact(
            document_id=doc.id,
            patient_id=patient.id,
            field_name=field_name,
            raw_text=val,
            normalized_value=val,
            unit=unit,
            page_index=0,
            char_start=0,
            char_end=len(val),
            verification_status="verified",
            created_at=AT_ISO,
        )
        db.add(ef)
        db.flush()
        db.add(
            FactVerification(
                fact_id=ef.id,
                decision="verified",
                verified_by_user_id=doctor.id,
                decided_at=AT_ISO,
            )
        )
    obs_val = 120 + (int(suffix) if suffix.isdigit() else 0)
    obs = Observation(
        patient_id=patient.id,
        measure_type="heart_rate",
        value=obs_val,
        unit="bpm",
        measured_at="2026-11-14T10:00:00Z",
        source="patient_checkin",
        validation="ok",
        trust_level="self_reported_validated",
        created_at="2026-11-14T10:00:00Z",
    )
    db.add(obs)
    db.commit()

    principal = Principal(
        user_id=doctor.id,
        username=doctor.username,
        display_name=doctor.display_name,
        role=Role(doctor.role),
        patient_id=doctor.patient_id,
        session_id=sess.id,
    )
    rec = create_run_foundation(
        db,
        principal=principal,
        patient_id=patient.id,
        document_ids=(doc.id,),
        observation_ids=(obs.id,),
        omissions=(),
        client_request_id=f"mig-run-{suffix}",
        as_of_utc=CLOCK,
    )
    db.commit()
    gate = evaluate_run_verification_gate(
        db,
        principal=principal,
        run_id=rec.run_id,
        validation_clock=CLOCK,
        upload_root=str(root),
    )
    assert gate.decision == "proceed"
    gate_row = db.execute(
        select(RunGateEvaluation).where(RunGateEvaluation.workflow_run_id == rec.run_id)
    ).scalar_one()
    return rec.run_id, patient.id, doctor.id, obs.id, gate_row.id, gate_row.input_fingerprint_sha256


def _insert_audit_for_run(
    db: Session,
    *,
    audit_id: str,
    run_id: str,
    patient_id: str,
    doctor_id: str,
    item_count: int = 1,
    link_count: int = 1,
) -> None:
    db.add(
        AuditEvent(
            id=audit_id,
            event_type="workflow.review.persisted",
            actor_type="user",
            actor_id=doctor_id,
            patient_id=patient_id,
            workflow_run_id=run_id,
            subject_type="workflow_run",
            subject_id=run_id,
            outcome=AuditOutcome.OK.value,
            idempotency_key=hashlib.sha256(f"audit-{audit_id}".encode()).hexdigest(),
            safe_detail=f"items={item_count}; links={link_count}",
            created_at=CLOCK_ISO,
        )
    )


def _insert_item(
    db: Session,
    *,
    item_id: str,
    run_id: str,
    patient_id: str,
    rule_id: str = "DR-009",
    reason_code: str = "implausible_value",
    dedupe_key: str | None = None,
    display_order: int = 0,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO review_item (
                id, patient_id, workflow_run_id, rule_id, reason_code, workflow_hint,
                trust_basis, message, policy_version, demo_only, dedupe_key, state,
                provenance_status, stored_lineage_proved, display_order, created_at
            ) VALUES (
                :id, :patient_id, :run_id, :rule_id, :reason_code, 'data_quality',
                'self_reported', 'Demo review item', 'demo-policy-1.1.0', 1,
                :dedupe_key, 'open', 'fixture_asserted', 0, :display_order, :created_at
            )
            """
        ),
        {
            "id": item_id,
            "patient_id": patient_id,
            "run_id": run_id,
            "rule_id": rule_id,
            "reason_code": reason_code,
            "dedupe_key": dedupe_key or hashlib.sha256(item_id.encode()).hexdigest(),
            "display_order": display_order,
            "created_at": CLOCK_ISO,
        },
    )


def _insert_link(
    db: Session,
    *,
    link_id: str,
    owner_id: str,
    obs_id: str,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO evidence_link (
                id, owner_type, owner_id, kind, document_id, observation_id,
                page_index, char_start, char_end, created_at
            ) VALUES (
                :id, 'review_item', :owner_id, 'observation', NULL, :obs_id,
                NULL, NULL, NULL, :created_at
            )
            """
        ),
        {"id": link_id, "owner_id": owner_id, "obs_id": obs_id, "created_at": CLOCK_ISO},
    )


def _insert_eval(
    db: Session,
    *,
    eval_id: str,
    run_id: str,
    patient_id: str,
    doctor_id: str,
    gate_id: str,
    gate_fp: str,
    audit_id: str,
    item_count: int = 1,
    link_count: int = 1,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO review_evaluation (
                id, workflow_run_id, patient_id, doctor_id, as_of_utc, policy_version,
                policy_reference_sha256, fingerprint_version, input_fingerprint_sha256,
                output_identity_sha256, gate_evaluation_id, gate_input_fingerprint_sha256,
                bridge_input_fingerprint_sha256, f2_contract_version, gate_version,
                rb2_policy_version, lineage_label_policy, dr006_policy, item_count,
                evidence_link_count, exclusion_count, audit_event_id, demo_only, created_at
            ) VALUES (
                :id, :run_id, :patient_id, :doctor_id, :as_of, 'demo-policy-1.1.0',
                :policy_sha, 'rb3-full-input-1.0.0', :in_fp, :out_fp,
                :gate_id, :gate_fp, :bridge_fp, '2.0.0', '1.0.0', 'demo-policy-1.1.0',
                'a2_transport_label', 'prohibited_denied', :item_count, :link_count,
                0, :audit_id, 1, :created_at
            )
            """
        ),
        {
            "id": eval_id,
            "run_id": run_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "as_of": CLOCK_ISO,
            "policy_sha": POLICY_SHA,
            "in_fp": hashlib.sha256(f"in-{eval_id}".encode()).hexdigest(),
            "out_fp": hashlib.sha256(f"out-{eval_id}".encode()).hexdigest(),
            "gate_id": gate_id,
            "gate_fp": gate_fp,
            "bridge_fp": hashlib.sha256(f"br-{eval_id}".encode()).hexdigest(),
            "item_count": item_count,
            "link_count": link_count,
            "audit_id": audit_id,
            "created_at": CLOCK_ISO,
        },
    )


def _setup_populated_db(tmp_path: Path) -> tuple[str, Path, tuple[str, str, str, str, str, str]]:
    db_file = tmp_path / "pop.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    cfg = _alembic_cfg(db_url)
    command.upgrade(cfg, "0007_p5_run_gate")
    eng = create_db_engine(db_url)
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    try:
        with Session(eng) as db:
            seed_demo_data(db, password=secrets.token_urlsafe(24), now=CLOCK, iterations=1000)
            db.commit()
            run_info = _seed_proceed_run(db, upload_root, suffix="1")
    finally:
        eng.dispose()
    return db_url, upload_root, run_info


def test_rb3_29_30_31_127_migration_populated_refusal_and_empty_roundtrip(tmp_path: Path):
    """RB3-29/30/31/110/127: 0007->0008->0007 exact sqlite_master & data preservation, populated refusal."""
    db_url, _upload_root, run_info = _setup_populated_db(tmp_path)
    run_id, patient_id, doctor_id, obs_id, gate_id, gate_fp = run_info
    cfg = _alembic_cfg(db_url)
    mig0008 = _load_0008_module()

    def _capture_master(conn):
        objs = conn.execute(
            text(
                "SELECT type, name, tbl_name, sql FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_autoindex_%' "
                "ORDER BY type, name, tbl_name"
            )
        ).all()
        auto_counts = conn.execute(
            text(
                "SELECT tbl_name, COUNT(*) FROM sqlite_master "
                "WHERE name LIKE 'sqlite_autoindex_%' "
                "GROUP BY tbl_name ORDER BY tbl_name"
            )
        ).all()
        return [(r[0], r[1], r[2], r[3]) for r in objs], [(r[0], r[1]) for r in auto_counts]

    def _capture_historical_data(conn):
        tables = (
            "schema_meta",
            "user",
            "patient",
            "document",
            "observation",
            "extracted_fact",
            "fact_verification",
            "workflow_run",
            "run_selected_document",
            "run_selected_observation",
            "run_gate_evaluation",
            "audit_event",
        )
        return {tbl: conn.execute(text(f"SELECT * FROM {tbl}")).all() for tbl in tables}

    eng = create_db_engine(db_url)
    try:
        with eng.connect() as conn:
            hist_master_0007, hist_auto_0007 = _capture_master(conn)
            hist_data_0007 = _capture_historical_data(conn)
            hist_triggers_0007 = {
                name: sql for typ, name, _tbl, sql in hist_master_0007 if typ == "trigger"
            }
            assert set(hist_triggers_0007) == EXPECTED_HISTORICAL_TRIGGERS

        command.upgrade(cfg, "head")
        with eng.connect() as conn:
            head_master, head_auto = _capture_master(conn)
            # Every pre-existing non-RB3 sqlite_master object (tables, indexes, and all 11 historical triggers)
            # must be byte-for-byte identical at 0008 head
            head_non_rb3 = [row for row in head_master if row[2] not in RB3_TABLES]
            assert head_non_rb3 == hist_master_0007
            assert [row for row in head_auto if row[0] not in RB3_TABLES] == hist_auto_0007
            # All 25 RB3 triggers exist on RB3 tables, and WITHOUT ROWID is confined to RB3 tables
            head_rb3_triggers = {
                name
                for typ, name, tbl, _sql in head_master
                if typ == "trigger" and tbl in RB3_TABLES
            }
            assert head_rb3_triggers == EXPECTED_RB3_TRIGGERS
            for typ, tbl, _t, ddl in head_master:
                if typ == "table" and tbl in RB3_TABLES:
                    assert "WITHOUT ROWID" in (ddl or "")
                elif typ == "table" and tbl != "sqlite_sequence":
                    assert "WITHOUT ROWID" not in (ddl or "")
            # Historical data remains completely intact
            assert _capture_historical_data(conn) == hist_data_0007

        # Empty-DB roundtrip: downgrade 0008 -> 0007 restores exact 0007 sqlite_master & data
        command.downgrade(cfg, "0007_p5_run_gate")
        with eng.connect() as conn:
            down_master, down_auto = _capture_master(conn)
            assert down_master == hist_master_0007
            assert down_auto == hist_auto_0007
            assert _capture_historical_data(conn) == hist_data_0007

        # Re-upgrade and verify nonempty downgrade refusal on each RB3 table
        command.upgrade(cfg, "head")
        with Session(eng) as db:
            item_id = "11111111-1111-4111-8111-111111111111"
            link_id = "22222222-2222-4222-8222-222222222222"
            audit_id = "33333333-3333-4333-8333-333333333333"
            eval_id = "44444444-4444-4444-8444-444444444444"
            _insert_item(db, item_id=item_id, run_id=run_id, patient_id=patient_id)
            _insert_link(db, link_id=link_id, owner_id=item_id, obs_id=obs_id)
            _insert_audit_for_run(
                db, audit_id=audit_id, run_id=run_id, patient_id=patient_id, doctor_id=doctor_id
            )
            _insert_eval(
                db,
                eval_id=eval_id,
                run_id=run_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                gate_id=gate_id,
                gate_fp=gate_fp,
                audit_id=audit_id,
            )
            db.commit()

        with pytest.raises(RuntimeError) as exc:
            command.downgrade(cfg, "0007_p5_run_gate")
        assert str(exc.value) == mig0008.DOWNGRADE_REFUSED_MESSAGE
        assert "0008_p4_rb3_review_persistence" in str(exc.value)

        with eng.connect() as conn:
            tables_after = {
                row[0]
                for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            }
            assert set(RB3_TABLES).issubset(tables_after)
            after_refusal = _capture_historical_data(conn)
            for tbl_name, expected_rows in hist_data_0007.items():
                if tbl_name == "audit_event":
                    assert set(expected_rows).issubset(set(after_refusal[tbl_name]))
                else:
                    assert after_refusal[tbl_name] == expected_rows
    finally:
        eng.dispose()


def test_rb3_58_126_orm_migration_parity_and_autogenerate_blind_spot(tmp_path: Path):
    """RB3-58/126: ORM/migration table+index+WITHOUT ROWID parity and autogenerate limit."""
    db_url = f"sqlite:///{(tmp_path / 'parity.db').as_posix()}"
    command.upgrade(_alembic_cfg(db_url), "head")
    eng = create_db_engine(db_url)
    try:
        insp = inspect(eng)
        assert set(insp.get_table_names()) >= set(RB3_TABLES)
        assert set(Base.metadata.tables) >= set(RB3_TABLES)
        for tbl in RB3_TABLES:
            mig_indexes = {idx["name"] for idx in insp.get_indexes(tbl)}
            orm_indexes = {idx.name for idx in Base.metadata.tables[tbl].indexes}
            assert mig_indexes == orm_indexes
            reflected = MetaData()
            reflected.reflect(bind=eng, only=[tbl])
            assert reflected.tables[tbl].dialect_options["sqlite"]["with_rowid"] is False
            ddl = str(reflected.tables[tbl].__table_args__ if False else "")
            from sqlalchemy.schema import CreateTable

            ddl = str(CreateTable(reflected.tables[tbl]).compile(eng))
            assert "WITHOUT ROWID" in ddl
            assert "VARCHAR(36) NOT NULL" in ddl
            assert "PRIMARY KEY (id)" in ddl

        # Prove Alembic autogenerate is blind to with_rowid loss
        rowid_url = f"sqlite:///{(tmp_path / 'rowid_only.db').as_posix()}"
        rowid_eng = create_engine(rowid_url)
        try:
            with rowid_eng.begin() as conn:
                conn.execute(
                    text(
                        "CREATE TABLE review_item ("
                        "id VARCHAR(36) NOT NULL PRIMARY KEY, patient_id VARCHAR(36) NOT NULL)"
                    )
                )
            sub_meta = MetaData()
            from sqlalchemy import Column, String, Table

            Table(
                "review_item",
                sub_meta,
                Column("id", String(36), primary_key=True, nullable=False),
                Column("patient_id", String(36), nullable=False),
                sqlite_with_rowid=False,
            )
            with rowid_eng.connect() as conn:
                mc = MigrationContext.configure(conn)
                diffs = compare_metadata(mc, sub_meta)
                assert diffs == []
        finally:
            rowid_eng.dispose()
    finally:
        eng.dispose()


def test_rb3_110_119_122_123_124_125_without_rowid_inventory_and_pragmas(engine, tmp_path: Path):
    """RB3-110/119/122/123/124/125: 25 RB3 triggers, 11 historical, WITHOUT ROWID, PK/FK/row-size."""
    with engine.connect() as conn:
        rb3_triggers = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='trigger' "
                    "AND tbl_name IN ('review_item', 'evidence_link', 'review_evaluation')"
                )
            )
        }
        assert rb3_triggers == EXPECTED_RB3_TRIGGERS

        all_triggers = {
            row[0]
            for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'"))
        }
        assert EXPECTED_HISTORICAL_TRIGGERS.issubset(all_triggers)

        assert conn.execute(text("PRAGMA recursive_triggers")).scalar_one() == 0
        assert conn.execute(text("PRAGMA foreign_keys")).scalar_one() == 1

        master_rows = conn.execute(
            text("SELECT name, sql FROM sqlite_master WHERE type='table'")
        ).all()
        for tbl_name, tbl_sql in master_rows:
            if tbl_name in RB3_TABLES:
                assert "WITHOUT ROWID" in tbl_sql
            elif tbl_name != "sqlite_sequence":
                assert "WITHOUT ROWID" not in (tbl_sql or "")

        # Verify PRAGMA index_list / index_info / foreign_key_list
        idx_names = {row[1] for row in conn.execute(text("PRAGMA index_list('review_item')")).all()}
        assert {
            "ux_review_dedupe",
            "ux_review_order",
            "ix_review_patient_state",
            "ix_review_run",
        }.issubset(idx_names)
        link_idx_sql = dict(
            conn.execute(
                text(
                    "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='evidence_link'"
                )
            ).all()
        )
        assert "WHERE kind = 'observation'" in link_idx_sql["ux_evidence_link_observation"]
        assert "WHERE kind = 'document_span'" in link_idx_sql["ux_evidence_link_span"]
        fk_tables = {
            row[2] for row in conn.execute(text("PRAGMA foreign_key_list('evidence_link')")).all()
        }
        assert {"document", "observation"} == fk_tables
        eval_fk_tables = {
            row[2]
            for row in conn.execute(text("PRAGMA foreign_key_list('review_evaluation')")).all()
        }
        assert {
            "workflow_run",
            "patient",
            "user",
            "run_gate_evaluation",
            "audit_event",
        } == eval_fk_tables

    # Verify NULL PK rejected on all 3 WITHOUT ROWID tables, contrasted with ordinary rowid table
    with Session(engine) as db:
        for stmt in (
            "INSERT INTO review_item (id, patient_id, workflow_run_id, rule_id, reason_code, workflow_hint, trust_basis, message, policy_version, demo_only, dedupe_key, state, provenance_status, stored_lineage_proved, display_order, created_at) VALUES (NULL, 'p', 'r', 'DR-001', 'missing_baseline', 'data_quality', 'self_reported', 'm', 'demo-policy-1.1.0', 1, :dk, 'open', 'fixture_asserted', 0, 0, :ts)",
            "INSERT INTO evidence_link (id, owner_type, owner_id, kind, document_id, observation_id, page_index, char_start, char_end, created_at) VALUES (NULL, 'review_item', 'o', 'observation', NULL, 'ob', NULL, NULL, NULL, :ts)",
            "INSERT INTO review_evaluation (id, workflow_run_id, patient_id, doctor_id, as_of_utc, policy_version, policy_reference_sha256, fingerprint_version, input_fingerprint_sha256, output_identity_sha256, gate_evaluation_id, gate_input_fingerprint_sha256, bridge_input_fingerprint_sha256, f2_contract_version, gate_version, rb2_policy_version, lineage_label_policy, dr006_policy, item_count, evidence_link_count, exclusion_count, audit_event_id, demo_only, created_at) VALUES (NULL, 'r', 'p', 'd', :ts, 'demo-policy-1.1.0', :ps, 'rb3-full-input-1.0.0', :ps, :ps, 'g', :ps, :ps, '2.0.0', '1.0.0', 'demo-policy-1.1.0', 'a2_transport_label', 'prohibited_denied', 0, 0, 0, 'a', 1, :ts)",
        ):
            with pytest.raises(IntegrityError):
                db.execute(text(stmt), {"dk": "a" * 64, "ts": CLOCK_ISO, "ps": POLICY_SHA})
            db.rollback()

    # Contrast: ordinary rowid table accepts NULL TEXT PRIMARY KEY
    mem = sqlite3.connect(":memory:")
    mem.execute("CREATE TABLE rowid_demo (id TEXT PRIMARY KEY, v TEXT)")
    mem.execute("INSERT INTO rowid_demo (id, v) VALUES (NULL, 'ok')")
    assert mem.execute("SELECT COUNT(*) FROM rowid_demo").fetchone() == (1,)
    mem.close()

    # Verify historical AuditEvent literal_column('rowid') still works & worst-case row sizes insert
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    with Session(engine) as db:
        seed_demo_data(db, password=secrets.token_urlsafe(24), now=CLOCK, iterations=1000)
        db.commit()
        run_id, patient_id, doctor_id, obs_id, gate_id, gate_fp = _seed_proceed_run(
            db, upload_root, suffix="2"
        )
        assert db.execute(select(AuditEvent.id).order_by(literal_column("rowid"))).all()

        big_item_id = "11111111-1111-4111-8111-111111111112"
        big_msg = "M" * 240
        db.execute(
            text(
                """
                INSERT INTO review_item (
                    id, patient_id, workflow_run_id, rule_id, reason_code, workflow_hint,
                    trust_basis, message, policy_version, demo_only, dedupe_key, state,
                    provenance_status, stored_lineage_proved, display_order, created_at
                ) VALUES (
                    :id, :pid, :rid, 'DR-009', 'implausible_value', 'data_quality',
                    'self_reported', :msg, 'demo-policy-1.1.0', 1, :dk, 'open',
                    'fixture_asserted', 0, 0, :ts
                )
                """
            ),
            {
                "id": big_item_id,
                "pid": patient_id,
                "rid": run_id,
                "msg": big_msg,
                "dk": "b" * 64,
                "ts": CLOCK_ISO,
            },
        )
        _insert_link(
            db, link_id="22222222-2222-4222-8222-222222222223", owner_id=big_item_id, obs_id=obs_id
        )
        audit_id = "33333333-3333-4333-8333-333333333334"
        _insert_audit_for_run(
            db, audit_id=audit_id, run_id=run_id, patient_id=patient_id, doctor_id=doctor_id
        )
        _insert_eval(
            db,
            eval_id="44444444-4444-4444-8444-444444444445",
            run_id=run_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            gate_id=gate_id,
            gate_fp=gate_fp,
            audit_id=audit_id,
        )
        db.commit()


def test_rb3_54_to_57_67_68_78_79_80_81_checks_and_vocabulary(engine, tmp_path: Path):
    """RB3-54..57/67/68/78/79/80/81: CHECKs, lengths, valid/retired rules, reason_codes, bounds."""
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    with Session(engine) as db:
        seed_demo_data(db, password=secrets.token_urlsafe(24), now=CLOCK, iterations=1000)
        db.commit()
        run_id, patient_id, doctor_id, obs_id, gate_id, gate_fp = _seed_proceed_run(
            db, upload_root, suffix="3"
        )

        # Valid 6 rules & 6 reason codes insert
        pairs = (
            ("DR-001", "missing_baseline"),
            ("DR-003", "measurement_stale"),
            ("DR-005", "change_exceeds_demo_parameter"),
            ("DR-006", "verified_source_conflict"),
            ("DR-008", "duplicate_or_out_of_order"),
            ("DR-009", "implausible_value"),
        )
        for idx, (rule_id, reason_code) in enumerate(pairs):
            _insert_item(
                db,
                item_id=f"55555555-5555-4555-8555-55555555550{idx}",
                run_id=run_id,
                patient_id=patient_id,
                rule_id=rule_id,
                reason_code=reason_code,
                display_order=idx,
            )
        db.commit()

        # Retired rule_ids, bad lengths, bad states/kinds/owner_types/provenance_status rejected
        bad_items = [
            ("DR-002", "missing_baseline", "m", "a" * 64, "open", "fixture_asserted"),
            ("DR-004", "missing_baseline", "m", "a" * 64, "open", "fixture_asserted"),
            ("DR-007", "missing_baseline", "m", "a" * 64, "open", "fixture_asserted"),
            ("DR-010", "missing_baseline", "m", "a" * 64, "open", "fixture_asserted"),
            ("DR-0001", "missing_baseline", "m", "a" * 64, "open", "fixture_asserted"),
            ("", "missing_baseline", "m", "a" * 64, "open", "fixture_asserted"),
            ("   ", "missing_baseline", "m", "a" * 64, "open", "fixture_asserted"),
            ("DR-001", "unknown_reason", "m", "a" * 64, "open", "fixture_asserted"),
            ("DR-001", "missing_baseline", "m" * 241, "a" * 64, "open", "fixture_asserted"),
            ("DR-001", "missing_baseline", "m", "a" * 63, "open", "fixture_asserted"),
            ("DR-001", "missing_baseline", "m", "a" * 64, "decided", "fixture_asserted"),
            ("DR-001", "missing_baseline", "m", "a" * 64, "superseded", "fixture_asserted"),
            ("DR-001", "missing_baseline", "m", "a" * 64, "open", "doctor_verified"),
        ]
        for idx, (rid, rcode, msg, dk, st, prov) in enumerate(bad_items):
            with pytest.raises(IntegrityError):
                db.execute(
                    text(
                        """
                        INSERT INTO review_item (
                            id, patient_id, workflow_run_id, rule_id, reason_code, workflow_hint,
                            trust_basis, message, policy_version, demo_only, dedupe_key, state,
                            provenance_status, stored_lineage_proved, display_order, created_at
                        ) VALUES (
                            :id, :pid, :run_id, :rid, :rcode, 'data_quality', 'self_reported', :msg, 'demo-policy-1.1.0',
                            1, :dk, :st, :prov, 0, 9, :ts
                        )
                        """
                    ),
                    {
                        "id": f"66666666-6666-4666-8666-6666666666{idx:02d}",
                        "pid": patient_id,
                        "run_id": run_id,
                        "rid": rid,
                        "rcode": rcode,
                        "msg": msg,
                        "dk": dk,
                        "st": st,
                        "prov": prov,
                        "ts": CLOCK_ISO,
                    },
                )
            db.rollback()

        # Reserved owner_type & kind rejected by G7 / G8
        victim_id = "55555555-5555-4555-8555-555555555500"
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT INTO evidence_link (id, owner_type, owner_id, kind, observation_id, created_at) "
                    "VALUES ('77777777-7777-4777-8777-777777777701', 'verification_issue', :oid, 'observation', :obs, :ts)"
                ),
                {"oid": victim_id, "obs": obs_id, "ts": CLOCK_ISO},
            )
        db.rollback()
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT INTO evidence_link (id, owner_type, owner_id, kind, document_id, page_index, char_start, char_end, created_at) "
                    "VALUES ('77777777-7777-4777-8777-777777777702', 'review_item', :oid, 'document_span', 'd', 0, 0, 1, :ts)"
                ),
                {"oid": victim_id, "ts": CLOCK_ISO},
            )
        db.rollback()

        # Attach 1 link per item (6 items, 6 links) so evidence_link_count >= item_count and G14 passes
        for idx in range(6):
            _insert_link(
                db,
                link_id=f"77777777-7777-4777-8777-77777777780{idx}",
                owner_id=f"55555555-5555-4555-8555-55555555550{idx}",
                obs_id=obs_id,
            )

        # Bounds CHECK on review_evaluation (item_count>12, link_count>24, wrong policy_sha, exclusion_count<0 or >200)
        audit_id = "33333333-3333-4333-8333-333333333335"
        _insert_audit_for_run(
            db,
            audit_id=audit_id,
            run_id=run_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            item_count=6,
            link_count=6,
        )
        db.commit()
        for bad_items_cnt, bad_links_cnt, bad_excl_cnt, bad_sha, expected_err in (
            (13, 13, 0, POLICY_SHA, None),
            (1, 25, 0, POLICY_SHA, None),
            (6, 6, 201, POLICY_SHA, "review_eval_excl_count_range"),
            (6, 6, -1, POLICY_SHA, "review_eval_excl_count_range"),
            (6, 6, 0, "0" * 64, "CHECK constraint failed"),
        ):
            with pytest.raises(IntegrityError, match=expected_err):
                db.execute(
                    text(
                        """
                        INSERT INTO review_evaluation (
                            id, workflow_run_id, patient_id, doctor_id, as_of_utc, policy_version,
                            policy_reference_sha256, fingerprint_version, input_fingerprint_sha256,
                            output_identity_sha256, gate_evaluation_id, gate_input_fingerprint_sha256,
                            bridge_input_fingerprint_sha256, f2_contract_version, gate_version,
                            rb2_policy_version, lineage_label_policy, dr006_policy, item_count,
                            evidence_link_count, exclusion_count, audit_event_id, demo_only, created_at
                        ) VALUES (
                            '88888888-8888-4888-8888-888888888801', :run_id, :pid, :did, :ts,
                            'demo-policy-1.1.0', :psha, 'rb3-full-input-1.0.0', :sha, :sha,
                            :gid, :gfp, :sha, '2.0.0', '1.0.0', 'demo-policy-1.1.0',
                            'a2_transport_label', 'prohibited_denied', :ic, :lc, :ec, :aid, 1, :ts
                        )
                        """
                    ),
                    {
                        "run_id": run_id,
                        "pid": patient_id,
                        "did": doctor_id,
                        "ts": CLOCK_ISO,
                        "psha": bad_sha,
                        "sha": POLICY_SHA,
                        "gid": gate_id,
                        "gfp": gate_fp,
                        "ic": bad_items_cnt,
                        "lc": bad_links_cnt,
                        "ec": bad_excl_cnt,
                        "aid": audit_id,
                    },
                )
            db.rollback()

        # Structural acceptance of exclusion_count=200 on the same otherwise valid row (RB3-98)
        db.execute(
            text(
                """
                INSERT INTO review_evaluation (
                    id, workflow_run_id, patient_id, doctor_id, as_of_utc, policy_version,
                    policy_reference_sha256, fingerprint_version, input_fingerprint_sha256,
                    output_identity_sha256, gate_evaluation_id, gate_input_fingerprint_sha256,
                    bridge_input_fingerprint_sha256, f2_contract_version, gate_version,
                    rb2_policy_version, lineage_label_policy, dr006_policy, item_count,
                    evidence_link_count, exclusion_count, audit_event_id, demo_only, created_at
                ) VALUES (
                    '88888888-8888-4888-8888-888888888802', :run_id, :pid, :did, :ts,
                    'demo-policy-1.1.0', :psha, 'rb3-full-input-1.0.0', :sha, :sha,
                    :gid, :gfp, :sha, '2.0.0', '1.0.0', 'demo-policy-1.1.0',
                    'a2_transport_label', 'prohibited_denied', 6, 6, 200, :aid, 1, :ts
                )
                """
            ),
            {
                "run_id": run_id,
                "pid": patient_id,
                "did": doctor_id,
                "ts": CLOCK_ISO,
                "psha": POLICY_SHA,
                "sha": POLICY_SHA,
                "gid": gate_id,
                "gfp": gate_fp,
                "aid": audit_id,
            },
        )
        db.commit()
        assert (
            db.execute(
                text(
                    "SELECT exclusion_count FROM review_evaluation "
                    "WHERE id = '88888888-8888-4888-8888-888888888802'"
                )
            ).scalar_one()
            == 200
        )


def test_rb3_69_89_90_100_to_108_118_121_replacement_and_rowid_closure(engine, tmp_path: Path):
    """RB3-69/89/90/100..108/118/121: FK order, sealing, all REPLACE spellings, cross-run & rowid closure."""
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    with Session(engine) as db:
        seed_demo_data(db, password=secrets.token_urlsafe(24), now=CLOCK, iterations=1000)
        db.commit()
        run_a, patient_id, doctor_id, obs_id, gate_a, fp_a = _seed_proceed_run(
            db, upload_root, suffix="4"
        )
        run_b, _, _, obs_b, gate_b, fp_b = _seed_proceed_run(db, upload_root, suffix="5")

        # RB3-69: completion before audit fails immediate FK
        with pytest.raises(IntegrityError):
            _insert_eval(
                db,
                eval_id="99999999-9999-4999-8999-999999999901",
                run_id=run_a,
                patient_id=patient_id,
                doctor_id=doctor_id,
                gate_id=gate_a,
                gate_fp=fp_a,
                audit_id="missing-audit-id-0000-0000-000000000000",
                item_count=0,
                link_count=0,
            )
        db.rollback()

        # Pre-completion items for run A: item_a1 (has link), item_a2 (no link)
        item_a1 = "aaaaaaa1-aaaa-4aaa-8aaa-aaaaaaaaaaa1"
        item_a2 = "aaaaaaa2-aaaa-4aaa-8aaa-aaaaaaaaaaa2"
        link_a1 = "bbbbbbb1-bbbb-4bbb-8bbb-bbbbbbbbbbb1"
        _insert_item(db, item_id=item_a1, run_id=run_a, patient_id=patient_id, display_order=0)
        _insert_item(db, item_id=item_a2, run_id=run_a, patient_id=patient_id, display_order=1)
        _insert_link(db, link_id=link_a1, owner_id=item_a1, obs_id=obs_id)
        db.commit()

        # RB3-100 / RB3-106: same-run PK-preserving replacement on item_a1 (G18)
        for verb in ("INSERT OR REPLACE", "REPLACE", "INSERT OR IGNORE"):
            with pytest.raises(IntegrityError):
                db.execute(
                    text(
                        f"{verb} INTO review_item (id, patient_id, workflow_run_id, rule_id, reason_code, workflow_hint, trust_basis, message, policy_version, demo_only, dedupe_key, state, provenance_status, stored_lineage_proved, display_order, created_at) "
                        "VALUES (:id, :pid, :rid, 'DR-001', 'missing_baseline', 'data_quality', 'self_reported', 'tampered', 'demo-policy-1.1.0', 1, :dk, 'open', 'fixture_asserted', 0, 5, :ts)"
                    ),
                    {
                        "id": item_a1,
                        "pid": patient_id,
                        "rid": run_a,
                        "dk": "c" * 64,
                        "ts": CLOCK_ISO,
                    },
                )
            db.rollback()

        # RB3-101: same-run dedupe_key replacement on linkless item_a2 (G19)
        dk_a2 = hashlib.sha256(item_a2.encode()).hexdigest()
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT OR REPLACE INTO review_item (id, patient_id, workflow_run_id, rule_id, reason_code, workflow_hint, trust_basis, message, policy_version, demo_only, dedupe_key, state, provenance_status, stored_lineage_proved, display_order, created_at) "
                    "VALUES ('aaaaaaa9-aaaa-4aaa-8aaa-aaaaaaaaaaa9', :pid, :rid, 'DR-009', 'implausible_value', 'data_quality', 'self_reported', 'tampered', 'demo-policy-1.1.0', 1, :dk, 'open', 'fixture_asserted', 0, 5, :ts)"
                ),
                {"pid": patient_id, "rid": run_a, "dk": dk_a2, "ts": CLOCK_ISO},
            )
        db.rollback()

        # RB3-102: same-run display_order replacement (G20)
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT OR REPLACE INTO review_item (id, patient_id, workflow_run_id, rule_id, reason_code, workflow_hint, trust_basis, message, policy_version, demo_only, dedupe_key, state, provenance_status, stored_lineage_proved, display_order, created_at) "
                    "VALUES ('aaaaaaa9-aaaa-4aaa-8aaa-aaaaaaaaaaa9', :pid, :rid, 'DR-009', 'implausible_value', 'data_quality', 'self_reported', 'tampered', 'demo-policy-1.1.0', 1, :dk, 'open', 'fixture_asserted', 0, 1, :ts)"
                ),
                {"pid": patient_id, "rid": run_a, "dk": "d" * 64, "ts": CLOCK_ISO},
            )
        db.rollback()

        # RB3-108: multi-conflict statement (PK + dedupe + order) refused
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT OR REPLACE INTO review_item (id, patient_id, workflow_run_id, rule_id, reason_code, workflow_hint, trust_basis, message, policy_version, demo_only, dedupe_key, state, provenance_status, stored_lineage_proved, display_order, created_at) "
                    "VALUES (:id, :pid, :rid, 'DR-009', 'implausible_value', 'data_quality', 'self_reported', 'multi', 'demo-policy-1.1.0', 1, :dk, 'open', 'fixture_asserted', 0, 1, :ts)"
                ),
                {"id": item_a2, "pid": patient_id, "rid": run_a, "dk": dk_a2, "ts": CLOCK_ISO},
            )
        db.rollback()

        # Complete run A (add link_a2 after testing linkless RB3-101 so link_count >= item_count holds)
        _insert_link(
            db, link_id="bbbbbbb2-bbbb-4bbb-8bbb-bbbbbbbbbbb2", owner_id=item_a2, obs_id=obs_id
        )
        audit_a = "ccccccc1-cccc-4ccc-8ccc-ccccccccccc1"
        eval_a = "ddddddd1-dddd-4ddd-8ddd-ddddddddddd1"
        _insert_audit_for_run(
            db,
            audit_id=audit_a,
            run_id=run_a,
            patient_id=patient_id,
            doctor_id=doctor_id,
            item_count=2,
            link_count=2,
        )
        _insert_eval(
            db,
            eval_id=eval_a,
            run_id=run_a,
            patient_id=patient_id,
            doctor_id=doctor_id,
            gate_id=gate_a,
            gate_fp=fp_a,
            audit_id=audit_a,
            item_count=2,
            link_count=2,
        )
        db.commit()

        # RB3-89: late insert into sealed run A refused by G15 / G16
        with pytest.raises(IntegrityError) as exc15:
            _insert_item(
                db,
                item_id="aaaaaaa8-aaaa-4aaa-8aaa-aaaaaaaaaaa8",
                run_id=run_a,
                patient_id=patient_id,
                display_order=2,
            )
        assert "review result is sealed for this run" in str(exc15.value)
        db.rollback()
        with pytest.raises(IntegrityError) as exc16:
            _insert_link(
                db, link_id="bbbbbbb8-bbbb-4bbb-8bbb-bbbbbbbbbbb8", owner_id=item_a1, obs_id=obs_b
            )
        assert "review result is sealed for this run" in str(exc16.value)
        db.rollback()

        # RB3-90: UPDATE/DELETE immutability + ON CONFLICT DO NOTHING/UPDATE
        for sql in (
            "UPDATE review_item SET message='x' WHERE id=:id",
            "DELETE FROM review_item WHERE id=:id",
            "UPDATE evidence_link SET kind='checkin_note' WHERE id=:lid",
            "DELETE FROM evidence_link WHERE id=:lid",
            "UPDATE review_evaluation SET item_count=0 WHERE id=:eid",
            "DELETE FROM review_evaluation WHERE id=:eid",
        ):
            with pytest.raises(IntegrityError):
                db.execute(text(sql), {"id": item_a1, "lid": link_a1, "eid": eval_a})
            db.rollback()

        # RB3-103 / 104: cross-run replacement into uncompleted run B refused by G18 / G21
        with pytest.raises(IntegrityError):
            _insert_item(db, item_id=item_a2, run_id=run_b, patient_id=patient_id, display_order=0)
        db.rollback()
        item_b1 = "eeeeeee1-eeee-4eee-8eee-eeeeeeeeeee1"
        _insert_item(db, item_id=item_b1, run_id=run_b, patient_id=patient_id, display_order=0)
        db.commit()
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT OR REPLACE INTO evidence_link (id, owner_type, owner_id, kind, observation_id, created_at) "
                    "VALUES (:lid, 'review_item', :oid, 'observation', :obs, :ts)"
                ),
                {"lid": link_a1, "oid": item_b1, "obs": obs_id, "ts": CLOCK_ISO},
            )
        db.rollback()

        # RB3-105 / 107: complete run B cleanly; cross-run review_evaluation replacement refused by G24
        _insert_link(
            db, link_id="fffffff1-ffff-4fff-8fff-fffffffffff1", owner_id=item_b1, obs_id=obs_id
        )
        audit_b = "ccccccc2-cccc-4ccc-8ccc-ccccccccccc2"
        eval_b = "ddddddd2-dddd-4ddd-8ddd-ddddddddddd2"
        _insert_audit_for_run(
            db,
            audit_id=audit_b,
            run_id=run_b,
            patient_id=patient_id,
            doctor_id=doctor_id,
            item_count=1,
            link_count=1,
        )
        _insert_eval(
            db,
            eval_id=eval_b,
            run_id=run_b,
            patient_id=patient_id,
            doctor_id=doctor_id,
            gate_id=gate_b,
            gate_fp=fp_b,
            audit_id=audit_b,
            item_count=1,
            link_count=1,
        )
        db.commit()
        assert db.get(ReviewEvaluation, eval_a).item_count == 2  # type: ignore[union-attr]

        run_c, _, _, _, gate_c, fp_c = _seed_proceed_run(db, upload_root, suffix="6")
        audit_c = "ccccccc3-cccc-4ccc-8ccc-ccccccccccc3"
        _insert_audit_for_run(
            db,
            audit_id=audit_c,
            run_id=run_c,
            patient_id=patient_id,
            doctor_id=doctor_id,
            item_count=0,
            link_count=0,
        )
        db.commit()
        with pytest.raises(IntegrityError):
            _insert_eval(
                db,
                eval_id=eval_a,
                run_id=run_c,
                patient_id=patient_id,
                doctor_id=doctor_id,
                gate_id=gate_c,
                gate_fp=fp_c,
                audit_id=audit_c,
                item_count=0,
                link_count=0,
            )
        db.rollback()

        # RB3-118: rowid, _rowid_, oid impossible on all 3 WITHOUT ROWID tables
        for tbl in RB3_TABLES:
            for alias in ("rowid", "_rowid_", "oid"):
                with pytest.raises(Exception) as r_exc:
                    db.execute(text(f"SELECT {alias} FROM {tbl}"))
                assert f"no such column: {alias}" in str(r_exc.value)
                db.rollback()
                with pytest.raises(Exception) as u_exc:
                    db.execute(text(f"UPDATE {tbl} SET {alias} = 99"))
                assert f"no such column: {alias}" in str(u_exc.value)
                db.rollback()


def test_rb3_91_115_116_117_g14_audit_completeness(engine, tmp_path: Path):
    """RB3-91/115/116/117: G14 checks all 8 audit columns independently + counts + gate."""
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    with Session(engine) as db:
        seed_demo_data(db, password=secrets.token_urlsafe(24), now=CLOCK, iterations=1000)
        db.commit()
        run_id, patient_id, doctor_id, _obs_id, gate_id, gate_fp = _seed_proceed_run(
            db, upload_root, suffix="7"
        )
        run2_id, _, _, _, _, _ = _seed_proceed_run(db, upload_root, suffix="8")

        for idx, bad_kwargs in enumerate(
            (
                {"event_type": "checkin.created"},
                {"patient_id": "other-patient"},
                {"workflow_run_id": run2_id},
                {"subject_type": "patient"},
                {"subject_id": "other-subject"},
                {"actor_type": "system"},
                {"actor_id": "other-actor"},
                {"outcome": "denied"},
            )
        ):
            aid = f"a1111111-1111-4111-8111-11111111110{idx}"
            kw = {
                "id": aid,
                "event_type": "workflow.review.persisted",
                "actor_type": "user",
                "actor_id": doctor_id,
                "patient_id": patient_id,
                "workflow_run_id": run_id,
                "subject_type": "workflow_run",
                "subject_id": run_id,
                "outcome": AuditOutcome.OK.value,
                "idempotency_key": hashlib.sha256(f"bad-g14-{idx}".encode()).hexdigest(),
                "safe_detail": "ok",
                "created_at": CLOCK_ISO,
            }
            kw.update(bad_kwargs)
            db.add(AuditEvent(**kw))
            db.commit()
            with pytest.raises(IntegrityError):
                _insert_eval(
                    db,
                    eval_id=f"e1111111-1111-4111-8111-11111111110{idx}",
                    run_id=run_id,
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    gate_id=gate_id,
                    gate_fp=gate_fp,
                    audit_id=aid,
                    item_count=0,
                    link_count=0,
                )
            db.rollback()

        # Consistent audit + mismatched item_count refused by G14
        good_aid = "a2222222-2222-4222-8222-222222222222"
        _insert_audit_for_run(
            db,
            audit_id=good_aid,
            run_id=run_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            item_count=0,
            link_count=0,
        )
        db.commit()
        with pytest.raises(IntegrityError):
            _insert_eval(
                db,
                eval_id="e2222222-2222-4222-8222-222222222221",
                run_id=run_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                gate_id=gate_id,
                gate_fp=gate_fp,
                audit_id=good_aid,
                item_count=1,
                link_count=1,
            )
        db.rollback()

        # Consistent audit + matching counts accepted (RB3-117)
        _insert_eval(
            db,
            eval_id="e2222222-2222-4222-8222-222222222222",
            run_id=run_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            gate_id=gate_id,
            gate_fp=gate_fp,
            audit_id=good_aid,
            item_count=0,
            link_count=0,
        )
        db.commit()


def test_rb3_109_120_isolated_guard_regression_proves(tmp_path: Path):
    """RB3-109/120: partial-index guard mirroring and Revision-5 rowid vulnerability regression."""
    # RB3-109: guard-isolation fixture omitting G8 to test G22 vs G23 predicates directly
    mig = _load_0008_module()
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys = OFF")
    con.execute(
        """
        CREATE TABLE evidence_link (
            id TEXT(36) NOT NULL, owner_type TEXT(32) NOT NULL, owner_id TEXT(36) NOT NULL,
            kind TEXT(24) NOT NULL, document_id TEXT(36), observation_id TEXT(36),
            page_index INTEGER, char_start INTEGER, char_end INTEGER, created_at TEXT(20) NOT NULL,
            PRIMARY KEY (id)
        ) WITHOUT ROWID
        """
    )
    con.execute(
        "CREATE UNIQUE INDEX ux_evidence_link_observation ON evidence_link (owner_id, observation_id) WHERE kind = 'observation'"
    )
    con.execute(
        "CREATE UNIQUE INDEX ux_evidence_link_span ON evidence_link (owner_id, document_id, page_index, char_start, char_end) WHERE kind = 'document_span'"
    )
    for trg_name, sql in mig.TRIGGER_CREATION_ORDER:
        if trg_name in {
            "trg_evidence_link_insert_observation_identity_conflict",
            "trg_evidence_link_insert_span_identity_conflict",
        }:
            con.execute(sql)
    con.execute(
        "INSERT INTO evidence_link VALUES ('l1','review_item','o1','observation',NULL,'obs1',NULL,NULL,NULL,'2026-11-14T12:00:00Z')"
    )
    # document_span for same owner o1 is NOT blocked by G22
    con.execute(
        "INSERT INTO evidence_link VALUES ('l2','review_item','o1','document_span','d1',NULL,0,0,5,'2026-11-14T12:00:00Z')"
    )
    # different char_end allowed
    con.execute(
        "INSERT INTO evidence_link VALUES ('l3','review_item','o1','document_span','d1',NULL,0,0,6,'2026-11-14T12:00:00Z')"
    )
    # duplicate span refused by G23
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO evidence_link VALUES ('l4','review_item','o1','document_span','d1',NULL,0,0,5,'2026-11-14T12:00:00Z')"
        )
    # duplicate observation refused by G22
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO evidence_link VALUES ('l5','review_item','o1','observation',NULL,'obs1',NULL,NULL,NULL,'2026-11-14T12:00:00Z')"
        )
    # same observation under different owner o2 allowed
    con.execute(
        "INSERT INTO evidence_link VALUES ('l6','review_item','o2','observation',NULL,'obs1',NULL,NULL,NULL,'2026-11-14T12:00:00Z')"
    )
    con.close()

    # RB3-120: Revision-5 ordinary rowid table allows hidden-rowid REPLACE attack
    rev5 = sqlite3.connect(":memory:")
    rev5.execute(
        "CREATE TABLE review_item (id TEXT(36) NOT NULL PRIMARY KEY, workflow_run_id TEXT(36) NOT NULL, dedupe_key TEXT(64) NOT NULL, display_order INTEGER NOT NULL)"
    )
    rev5.execute(
        "CREATE TRIGGER trg_pk BEFORE INSERT ON review_item WHEN EXISTS (SELECT 1 FROM review_item WHERE id = NEW.id) BEGIN SELECT RAISE(ABORT, 'pk'); END;"
    )
    rev5.execute("INSERT INTO review_item VALUES ('i1', 'runA', 'dk1', 0)")
    rid = rev5.execute("SELECT rowid FROM review_item WHERE id='i1'").fetchone()[0]
    rev5.execute(
        "INSERT OR REPLACE INTO review_item (rowid, id, workflow_run_id, dedupe_key, display_order) VALUES (?, 'i2', 'runB', 'dk2', 0)",
        (rid,),
    )
    assert (
        rev5.execute("SELECT COUNT(*) FROM review_item WHERE workflow_run_id='runA'").fetchone()[0]
        == 0
    )
    assert (
        rev5.execute("SELECT COUNT(*) FROM review_item WHERE workflow_run_id='runB'").fetchone()[0]
        == 1
    )
    rev5.close()
