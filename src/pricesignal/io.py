"""Safe local import and privacy-minimized PriceSignal exports."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import platform
import re
import zipfile

import numpy as np
import pandas as pd

from . import __version__
from .errors import DataProblem


MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_ROWS = 250_000
MAX_COLUMNS = 500
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".json"}


def _validate_shape(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        raise DataProblem("The uploaded table has no data rows.")
    if len(frame) > MAX_ROWS:
        raise DataProblem(f"This release accepts at most {MAX_ROWS:,} rows per analysis.")
    if len(frame.columns) > MAX_COLUMNS:
        raise DataProblem(f"This release accepts at most {MAX_COLUMNS:,} columns.")
    names = [str(column).strip() for column in frame.columns]
    if any(not name for name in names):
        raise DataProblem("Every column needs a non-empty name.")
    if len(names) != len(set(names)):
        raise DataProblem("Column names must be unique.")
    result = frame.copy()
    result.columns = names
    return result


def read_table(raw: bytes, filename: str) -> tuple[pd.DataFrame, dict[str, str]]:
    if not raw:
        raise DataProblem("The uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise DataProblem("The uploaded file exceeds PriceSignal's 50 MB local safety limit.")
    extension = Path(filename).suffix.casefold()
    if extension not in ALLOWED_EXTENSIONS:
        raise DataProblem("Use CSV, XLSX, or JSON for pricing evidence.")
    sheet = ""
    try:
        if extension == ".csv":
            frame = pd.read_csv(BytesIO(raw))
        elif extension == ".xlsx":
            book = pd.ExcelFile(BytesIO(raw), engine="openpyxl")
            if not book.sheet_names:
                raise DataProblem("The workbook has no worksheets.")
            sheet = book.sheet_names[0]
            frame = pd.read_excel(book, sheet_name=sheet)
        else:
            payload = json.loads(raw.decode("utf-8-sig"))
            if isinstance(payload, dict) and isinstance(payload.get("data"), list):
                payload = payload["data"]
            if not isinstance(payload, list):
                raise DataProblem("JSON input must be an array of row objects or an object with a data array.")
            frame = pd.DataFrame(payload)
    except DataProblem:
        raise
    except Exception as exc:
        raise DataProblem(f"The {extension[1:].upper()} file could not be read as a rectangular table.") from exc
    return _validate_shape(frame), {
        "source_filename": Path(filename).name,
        "source_sheet": sheet,
        "source_sha256": sha256(raw).hexdigest(),
    }


_ILLEGAL_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _scrub_control(value: str) -> str:
    return _ILLEGAL_XML.sub("", value)


def _safe_cell(value: object) -> object:
    if isinstance(value, str):
        cleaned = _scrub_control(value)
        if cleaned.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + cleaned
        return cleaned
    return value


def safe_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.select_dtypes(include=["object", "string"]).columns:
        result[column] = result[column].map(_safe_cell)
    result.columns = [_safe_cell(_scrub_control(str(column))) for column in result.columns]
    return result


def _json_value(value: object) -> object:
    if isinstance(value, pd.DataFrame):
        return [{str(key): _json_value(item) for key, item in row.items()} for row in value.to_dict(orient="records")]
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return value


def build_evidence_pack(*, source: dict[str, object], contract: dict[str, object], analysis) -> dict[str, object]:
    return {
        "schema": "pricesignal.evidence.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_by": {
            "product": "PriceSignal",
            "version": __version__,
            "python": platform.python_version(),
        },
        "source": source,
        "evidence_tier": analysis.evidence_tier,
        "decision_contract": contract,
        "audit_summary": analysis.audit.summary,
        "audit_warnings": list(analysis.audit.warnings),
        "diagnostics": analysis.diagnostics,
        "optimal_price_scenario": analysis.optimal,
        "candidate_comparison": analysis.comparison,
        "analysis_warnings": list(analysis.warnings),
        "tables": {
            "evidence_support": analysis.arm_or_quantile_summary,
            "model_or_valuation_summary": analysis.coefficients,
            "price_scenarios": analysis.price_grid,
        },
        "privacy_note": (
            "No customer, respondent, period-level, transaction-level, fitted-value, residual, or free-text rows are included."
        ),
    }


def build_gate_bridge(analysis) -> dict[str, object]:
    """Small aggregate payload for a future GateSignal pricing-evidence import."""
    comparison = analysis.comparison
    return {
        "schema": "signal.price-evidence.v1",
        "producer": {"product": "PriceSignal", "version": __version__},
        "evidence_tier": analysis.evidence_tier,
        "candidate_price": comparison["candidate_price"],
        "reference_price": comparison["reference_price"],
        "declared_unit_cost": analysis.config.unit_cost,
        "candidate_projected_volume": comparison["candidate_volume"],
        "candidate_contribution": comparison["candidate_contribution"],
        "incremental_contribution": comparison["incremental_contribution"],
        "incremental_contribution_interval": [comparison["incremental_low"], comparison["incremental_high"]],
        "within_observed_support": comparison["within_observed_support"],
        "decision_status": comparison["status"],
        "interpretation": comparison["explanation"],
        "warning": "An aggregate price scenario is one input to a launch decision, not a launch approval.",
    }


def evidence_to_json(pack: dict[str, object]) -> bytes:
    return json.dumps(_json_value(pack), indent=2, ensure_ascii=False).encode("utf-8")


def _sheet_name(name: str, used: set[str]) -> str:
    cleaned = re.sub(r"[\\/*?:\[\]]", "_", name)[:31] or "Sheet"
    candidate = cleaned
    suffix = 2
    while candidate.casefold() in used:
        marker = f"_{suffix}"
        candidate = cleaned[: 31 - len(marker)] + marker
        suffix += 1
    used.add(candidate.casefold())
    return candidate


def evidence_to_excel(pack: dict[str, object]) -> bytes:
    buffer = BytesIO()
    used: set[str] = set()
    flat_sections = {
        "Read me": {
            "product": "PriceSignal",
            "schema": pack.get("schema"),
            "evidence_tier": pack.get("evidence_tier"),
            "privacy_note": pack.get("privacy_note"),
        },
        "Source": pack.get("source", {}),
        "Decision contract": pack.get("decision_contract", {}),
        "Audit": pack.get("audit_summary", {}),
        "Diagnostics": pack.get("diagnostics", {}),
        "Candidate comparison": pack.get("candidate_comparison", {}),
        "Optimal scenario": pack.get("optimal_price_scenario", {}),
    }
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, values in flat_sections.items():
            rows = [{"field": key, "value": _json_value(value)} for key, value in dict(values).items()]
            safe_frame(pd.DataFrame(rows)).to_excel(writer, sheet_name=_sheet_name(name, used), index=False)
        tables = pack.get("tables", {})
        if isinstance(tables, dict):
            for name, frame in tables.items():
                if isinstance(frame, pd.DataFrame):
                    safe_frame(frame).to_excel(writer, sheet_name=_sheet_name(str(name), used), index=False)
        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for cells in worksheet.columns:
                width = min(48, max(10, max(len(str(cell.value or "")) for cell in cells) + 2))
                worksheet.column_dimensions[cells[0].column_letter].width = width
    return buffer.getvalue()


def evidence_to_csv_zip(pack: dict[str, object]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest = {key: value for key, value in pack.items() if key != "tables"}
        archive.writestr("manifest.json", evidence_to_json(manifest))
        tables = pack.get("tables", {})
        if isinstance(tables, dict):
            for name, frame in tables.items():
                if isinstance(frame, pd.DataFrame):
                    archive.writestr(f"{name}.csv", safe_frame(frame).to_csv(index=False, lineterminator="\n"))
    return buffer.getvalue()


def dataframe_to_xlsx(frame: pd.DataFrame, sheet_name: str = "Pricing evidence") -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        safe_frame(frame).to_excel(writer, sheet_name=sheet_name, index=False)
        worksheet = writer.book[sheet_name]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        for cells in worksheet.columns:
            worksheet.column_dimensions[cells[0].column_letter].width = min(
                42, max(11, max(len(str(cell.value or "")) for cell in cells) + 2)
            )
    return buffer.getvalue()
