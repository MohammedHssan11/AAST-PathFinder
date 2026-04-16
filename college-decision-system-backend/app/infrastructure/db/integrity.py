from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.infrastructure.db import models as _db_models  # noqa: F401
from app.infrastructure.db.session import Base

ACTIVE_DECISION_TABLES = (
    "decision_colleges",
    "decision_college_sources",
    "decision_college_leadership",
    "decision_programs",
    "decision_program_decision_profiles",
    "decision_program_career_paths",
    "decision_program_traits",
    "decision_employment_outlooks",
    "decision_college_level_profiles",
    "decision_training_and_practice",
    "decision_admission_requirements",
    "decision_accepted_certificates",
    "decision_college_accreditations",
    "decision_college_facilities",
    "decision_college_research_focus",
    "decision_college_mobility",
    "decision_college_mobility_items",
    "decision_fee_global_policies",
    "decision_fee_definitions",
    "decision_fee_items",
    "decision_fee_amounts",
    "decision_fee_additional_fees",
    "decision_fee_category_rules",
    "decision_fee_rule_colleges",
    "decision_fee_rule_thresholds",
    "decision_scholarships",
    "decision_scholarship_eligibility",
)

INTEGRITY_COUNT_QUERIES = {
    "programs_missing_college": """
        select count(*) from decision_programs p
        left join decision_colleges c on c.id = p.college_id
        where c.id is null
    """,
    "profiles_missing_program": """
        select count(*) from decision_program_decision_profiles dp
        left join decision_programs p on p.id = dp.program_id
        where p.id is null
    """,
    "career_paths_missing_program": """
        select count(*) from decision_program_career_paths cp
        left join decision_programs p on p.id = cp.program_id
        where p.id is null
    """,
    "traits_missing_program": """
        select count(*) from decision_program_traits t
        left join decision_programs p on p.id = t.program_id
        where p.id is null
    """,
    "employment_missing_program": """
        select count(*) from decision_employment_outlooks eo
        left join decision_programs p on p.id = eo.program_id
        where p.id is null
    """,
    "college_sources_missing_college": """
        select count(*) from decision_college_sources s
        left join decision_colleges c on c.id = s.college_id
        where c.id is null
    """,
    "leadership_missing_college": """
        select count(*) from decision_college_leadership l
        left join decision_colleges c on c.id = l.college_id
        where c.id is null
    """,
    "level_profiles_missing_college": """
        select count(*) from decision_college_level_profiles lp
        left join decision_colleges c on c.id = lp.college_id
        where c.id is null
    """,
    "training_missing_college": """
        select count(*) from decision_training_and_practice tp
        left join decision_colleges c on c.id = tp.college_id
        where c.id is null
    """,
    "admission_missing_college": """
        select count(*) from decision_admission_requirements ar
        left join decision_colleges c on c.id = ar.college_id
        where c.id is null
    """,
    "accepted_certs_missing_admission": """
        select count(*) from decision_accepted_certificates ac
        left join decision_admission_requirements ar on ar.id = ac.admission_requirement_id
        where ar.id is null
    """,
    "accreditations_missing_college": """
        select count(*) from decision_college_accreditations a
        left join decision_colleges c on c.id = a.college_id
        where c.id is null
    """,
    "facilities_missing_college": """
        select count(*) from decision_college_facilities f
        left join decision_colleges c on c.id = f.college_id
        where c.id is null
    """,
    "research_focus_missing_college": """
        select count(*) from decision_college_research_focus rf
        left join decision_colleges c on c.id = rf.college_id
        where c.id is null
    """,
    "mobility_missing_college": """
        select count(*) from decision_college_mobility m
        left join decision_colleges c on c.id = m.college_id
        where c.id is null
    """,
    "mobility_items_missing_mobility": """
        select count(*) from decision_college_mobility_items mi
        left join decision_college_mobility m on m.id = mi.mobility_id
        where m.id is null
    """,
    "fee_items_missing_college": """
        select count(*) from decision_fee_items fi
        left join decision_colleges c on c.id = fi.source_college_match_id
        where fi.source_college_match_id is not null and c.id is null
    """,
    "fee_items_missing_program": """
        select count(*) from decision_fee_items fi
        left join decision_programs p on p.id = fi.source_program_match_id
        where fi.source_program_match_id is not null and p.id is null
    """,
    "fee_amounts_missing_fee_item": """
        select count(*) from decision_fee_amounts fa
        left join decision_fee_items fi on fi.id = fa.fee_item_id
        where fi.id is null
    """,
    "additional_fees_missing_fee_item": """
        select count(*) from decision_fee_additional_fees af
        left join decision_fee_items fi on fi.id = af.fee_item_id
        where fi.id is null
    """,
    "fee_rule_colleges_missing_rule": """
        select count(*) from decision_fee_rule_colleges rc
        left join decision_fee_category_rules r on r.id = rc.fee_rule_id
        where r.id is null
    """,
    "fee_rule_colleges_missing_college": """
        select count(*) from decision_fee_rule_colleges rc
        left join decision_colleges c on c.id = rc.source_college_match_id
        where rc.source_college_match_id is not null and c.id is null
    """,
    "fee_thresholds_missing_rule": """
        select count(*) from decision_fee_rule_thresholds t
        left join decision_fee_category_rules r on r.id = t.fee_rule_id
        where r.id is null
    """,
    "scholarship_eligibility_missing_parent": """
        select count(*) from decision_scholarship_eligibility se
        left join decision_scholarships s on s.id = se.scholarship_id
        where s.id is null
    """,
}

DUPLICATE_COUNT_QUERIES = {
    "duplicate_decision_college_ids": """
        select count(*) from (
            select id from decision_colleges group by id having count(*) > 1
        )
    """,
    "duplicate_decision_program_ids": """
        select count(*) from (
            select id from decision_programs group by id having count(*) > 1
        )
    """,
    "duplicate_program_name_per_college": """
        select count(*) from (
            select college_id, lower(program_name)
            from decision_programs
            group by college_id, lower(program_name)
            having count(*) > 1
        )
    """,
    "duplicate_fee_ids": """
        select count(*) from (
            select fee_id from decision_fee_items group by fee_id having count(*) > 1
        )
    """,
    "duplicate_fee_amount_keys": """
        select count(*) from (
            select fee_item_id, student_group, fee_category
            from decision_fee_amounts
            group by fee_item_id, student_group, fee_category
            having count(*) > 1
        )
    """,
    "duplicate_rule_ids": """
        select count(*) from (
            select rule_id from decision_fee_category_rules group by rule_id having count(*) > 1
        )
    """,
    "duplicate_rule_threshold_category": """
        select count(*) from (
            select fee_rule_id, fee_category
            from decision_fee_rule_thresholds
            group by fee_rule_id, fee_category
            having count(*) > 1
        )
    """,
    "duplicate_rule_college_rows": """
        select count(*) from (
            select fee_rule_id, college_id_raw, ifnull(source_college_match_id, '')
            from decision_fee_rule_colleges
            group by fee_rule_id, college_id_raw, ifnull(source_college_match_id, '')
            having count(*) > 1
        )
    """,
    "duplicate_additional_fees": """
        select count(*) from (
            select fee_item_id, fee_type, amount_usd, ifnull(frequency, ''), ifnull(note, '')
            from decision_fee_additional_fees
            group by fee_item_id, fee_type, amount_usd, ifnull(frequency, ''), ifnull(note, '')
            having count(*) > 1
        )
    """,
    "duplicate_academic_year_fee_rows_same_mapping": """
        select count(*) from (
            select ifnull(source_program_match_id, ''), ifnull(source_college_match_id, ''),
                   ifnull(program_name, ''), academic_year, track_type
            from decision_fee_items
            group by ifnull(source_program_match_id, ''), ifnull(source_college_match_id, ''),
                     ifnull(program_name, ''), academic_year, track_type
            having count(*) > 1
        )
    """,
}

MAPPING_GAP_QUERIES = {
    "fee_rule_colleges_unmatched_raw_ids": """
        select count(*) from decision_fee_rule_colleges
        where source_college_match_id is null
    """,
    "fee_items_unmatched_raw_college_ids": """
        select count(*) from decision_fee_items
        where source_college_match_id is null
    """,
    "fee_items_unmatched_program_ids": """
        select count(*) from decision_fee_items
        where program_name is not null and trim(program_name) != '' and source_program_match_id is null
    """,
    "rules_missing_threshold_categories": """
        select count(*) from (
            select r.id
            from decision_fee_category_rules r
            left join decision_fee_rule_thresholds t on t.fee_rule_id = r.id
            group by r.id
            having count(t.id) < 3
        )
    """,
    "fee_items_program_college_mismatch": """
        select count(*) from decision_fee_items fi
        join decision_programs p on p.id = fi.source_program_match_id
        where fi.source_college_match_id is not null and p.college_id != fi.source_college_match_id
    """,
}

RUNTIME_CRITICAL_INDEX_COLUMNS = {
    "decision_programs": {("college_id",), ("program_name",)},
    "decision_program_career_paths": {("program_id",)},
    "decision_program_traits": {("program_id",), ("trait_type",)},
    "decision_employment_outlooks": {("program_id",)},
    "decision_training_and_practice": {("college_id",)},
    "decision_admission_requirements": {("college_id",)},
    "decision_accepted_certificates": {("admission_requirement_id",)},
    "decision_fee_items": {
        ("fee_id",),
        ("college_id_raw",),
        ("source_college_match_id",),
        ("source_program_match_id",),
        ("track_type",),
    },
    "decision_fee_amounts": {("fee_item_id",), ("student_group",), ("fee_category",)},
    "decision_fee_additional_fees": {("fee_item_id",)},
    "decision_fee_category_rules": {("rule_id",)},
    "decision_fee_rule_colleges": {("fee_rule_id",), ("college_id_raw",)},
    "decision_fee_rule_thresholds": {("fee_rule_id",)},
}


def get_sqlite_foreign_keys_enabled(session: Session) -> bool:
    if session.bind is None or session.bind.dialect.name != "sqlite":
        return True
    value = session.execute(text("PRAGMA foreign_keys")).scalar_one()
    return bool(value)


def collect_decision_table_inventory(engine: Engine) -> list[dict[str, object]]:
    inspector = inspect(engine)
    available_tables = set(inspector.get_table_names())
    inventory: list[dict[str, object]] = []
    for table_name in ACTIVE_DECISION_TABLES:
        if table_name not in available_tables:
            continue
        pk = inspector.get_pk_constraint(table_name)
        inventory.append(
            {
                "table_name": table_name,
                "row_count": _count_rows(engine, table_name),
                "primary_key": pk.get("constrained_columns", []),
                "foreign_keys": inspector.get_foreign_keys(table_name),
                "unique_constraints": inspector.get_unique_constraints(table_name),
                "columns": inspector.get_columns(table_name),
                "indexes": _get_table_indexes(engine, table_name),
            }
        )
    return inventory


def collect_integrity_counts(session: Session) -> dict[str, int]:
    return {
        name: int(session.execute(text(sql)).scalar_one())
        for name, sql in INTEGRITY_COUNT_QUERIES.items()
    }


def collect_duplicate_counts(session: Session) -> dict[str, int]:
    return {
        name: int(session.execute(text(sql)).scalar_one())
        for name, sql in DUPLICATE_COUNT_QUERIES.items()
    }


def collect_mapping_gap_counts(session: Session) -> dict[str, int]:
    return {
        name: int(session.execute(text(sql)).scalar_one())
        for name, sql in MAPPING_GAP_QUERIES.items()
    }


def collect_runtime_index_status(engine: Engine) -> dict[str, dict[tuple[str, ...], bool]]:
    available_indexes = {
        table_name: {tuple(index["columns"]) for index in _get_table_indexes(engine, table_name)}
        for table_name in RUNTIME_CRITICAL_INDEX_COLUMNS
    }
    return {
        table_name: {
            index_columns: index_columns in available_indexes.get(table_name, set())
            for index_columns in expected_indexes
        }
        for table_name, expected_indexes in RUNTIME_CRITICAL_INDEX_COLUMNS.items()
    }


def collect_decision_schema_drift(engine: Engine) -> dict[str, object]:
    inspector = inspect(engine)
    available_tables = set(inspector.get_table_names())
    active_table_set = set(ACTIVE_DECISION_TABLES)
    metadata_tables = {
        table_name
        for table_name in Base.metadata.tables
        if table_name.startswith("decision_")
    }

    missing_tables_in_db = sorted(metadata_tables - available_tables)
    unmanaged_active_tables = sorted(active_table_set - metadata_tables)
    unexpected_decision_tables = sorted(
        table_name
        for table_name in available_tables
        if table_name.startswith("decision_") and table_name not in metadata_tables
    )

    column_drift: dict[str, dict[str, list[str]]] = {}
    for table_name in sorted(metadata_tables & available_tables):
        model_columns = set(Base.metadata.tables[table_name].columns.keys())
        db_columns = {column["name"] for column in inspector.get_columns(table_name)}
        missing_in_db = sorted(model_columns - db_columns)
        missing_in_model = sorted(db_columns - model_columns)
        if missing_in_db or missing_in_model:
            column_drift[table_name] = {
                "missing_in_db": missing_in_db,
                "missing_in_model": missing_in_model,
            }

    missing_runtime_indexes = {
        table_name: [list(columns) for columns, present in status.items() if not present]
        for table_name, status in collect_runtime_index_status(engine).items()
        if not all(status.values())
    }

    return {
        "missing_tables_in_db": missing_tables_in_db,
        "unmanaged_active_tables": unmanaged_active_tables,
        "unexpected_decision_tables": unexpected_decision_tables,
        "column_drift": column_drift,
        "missing_runtime_indexes": missing_runtime_indexes,
    }


def _count_rows(engine: Engine, table_name: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f"select count(*) from {table_name}")).scalar_one())


def _get_table_indexes(engine: Engine, table_name: str) -> list[dict[str, object]]:
    inspector = inspect(engine)
    indexes = [
        {
            "name": index.get("name"),
            "columns": index.get("column_names", []),
            "unique": bool(index.get("unique", False)),
        }
        for index in inspector.get_indexes(table_name)
    ]
    indexes.extend(_unique_constraints_as_indexes(inspector.get_unique_constraints(table_name)))
    return sorted(
        indexes,
        key=lambda item: (tuple(item.get("columns", ())), item.get("name") or ""),
    )


def _unique_constraints_as_indexes(
    constraints: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        {
            "name": constraint.get("name"),
            "columns": constraint.get("column_names", []),
            "unique": True,
        }
        for constraint in constraints
    ]
