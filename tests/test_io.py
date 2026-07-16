from __future__ import annotations

import io
import json
import zipfile

import pandas as pd

from pricesignal.analysis import PriceConfig, analyze_price
from pricesignal.examples import demo_contract, randomized_demo
from pricesignal.io import (
    build_evidence_pack,
    build_gate_bridge,
    dataframe_to_xlsx,
    evidence_to_csv_zip,
    evidence_to_excel,
    evidence_to_json,
    read_table,
    safe_frame,
)


def result():
    values = demo_contract("randomized")
    values["controls"] = tuple(values.get("controls", ()))
    values["bootstrap_iterations"] = 120
    return analyze_price(randomized_demo(), PriceConfig(**values))


def test_csv_json_and_xlsx_imports() -> None:
    frame = pd.DataFrame({"price": [10, 12], "quantity": [5, 4]})
    csv_frame, csv_source = read_table(frame.to_csv(index=False).encode(), "input.csv")
    assert csv_frame.equals(frame)
    assert csv_source["source_sha256"]
    json_frame, _ = read_table(json.dumps({"data": frame.to_dict(orient="records")}).encode(), "input.json")
    assert json_frame.equals(frame)
    xlsx_frame, _ = read_table(dataframe_to_xlsx(frame), "input.xlsx")
    assert xlsx_frame.equals(frame)


def test_exports_are_aggregate_and_portable() -> None:
    analysis = result()
    pack = build_evidence_pack(
        source={"source_filename": "fictional.csv", "source_sha256": "abc"},
        contract=demo_contract("randomized"),
        analysis=analysis,
    )
    raw_json = evidence_to_json(pack)
    decoded = json.loads(raw_json)
    assert decoded["schema"] == "pricesignal.evidence.v1"
    assert "customer_id" not in raw_json.decode()
    workbook = pd.ExcelFile(io.BytesIO(evidence_to_excel(pack)), engine="openpyxl")
    assert "Candidate comparison" in workbook.sheet_names
    with zipfile.ZipFile(io.BytesIO(evidence_to_csv_zip(pack))) as archive:
        assert "manifest.json" in archive.namelist()
        assert "price_scenarios.csv" in archive.namelist()


def test_gate_bridge_contains_no_row_level_data() -> None:
    bridge = build_gate_bridge(result())
    assert bridge["schema"] == "signal.price-evidence.v1"
    assert bridge["candidate_price"] == 34.0
    assert "customer_id" not in json.dumps(bridge)


def test_spreadsheet_formula_strings_are_neutralized() -> None:
    frame = safe_frame(pd.DataFrame({"label": ["=2+2", "+cmd", "ordinary"]}))
    assert frame.loc[0, "label"].startswith("'")
    assert frame.loc[1, "label"].startswith("'")
    assert frame.loc[2, "label"] == "ordinary"

