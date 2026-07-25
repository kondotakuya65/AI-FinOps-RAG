"""Validate synthetic fixtures against ground_truth.json."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures"
GROUND_TRUTH = FIXTURES / "ground_truth.json"


def _load_truth() -> dict:
    assert GROUND_TRUTH.exists(), f"Missing {GROUND_TRUTH}; run scripts/generate_fixtures.py"
    return json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))


def test_ground_truth_line_math() -> None:
    truth = _load_truth()
    for inv in truth["invoices"]:
        computed = round(sum(line["line_total"] for line in inv["lines"]), 2)
        assert computed == inv["total_amount"], inv["invoice_id"]
        for line in inv["lines"]:
            expected = round(line["qty"] * line["unit_price"], 2)
            assert line["line_total"] == expected, (inv["invoice_id"], line["sku"])


def test_alpha_q3_aggregate() -> None:
    truth = _load_truth()
    expected = round(
        sum(
            inv["total_amount"]
            for inv in truth["invoices"]
            if inv["vendor"] == "Alpha Supplies" and inv["quarter"] == "2024-Q3"
        ),
        2,
    )
    assert truth["aggregates"]["alpha_supplies_2024_q3_spend"] == expected
    assert expected == 10675.22


def test_fixture_files_exist() -> None:
    truth = _load_truth()
    for inv in truth["invoices"]:
        path = FIXTURES / "invoices" / inv["file_name"]
        assert path.exists() and path.stat().st_size > 0, path
    for report in truth["reports"]:
        path = FIXTURES / "reports" / report["file_name"]
        assert path.exists() and path.stat().st_size > 0, path
    contract = FIXTURES / "contracts" / truth["contract"]["file_name"]
    assert contract.exists() and contract.stat().st_size > 0


def test_discrepancies_match_reports() -> None:
    truth = _load_truth()
    reports_by_period = {r["period"]: r for r in truth["reports"]}
    invoices = {i["invoice_id"]: i for i in truth["invoices"]}

    assert len(truth["discrepancies"]) == 3
    for disc in truth["discrepancies"]:
        inv = invoices[disc["invoice_id"]]
        line = next(L for L in inv["lines"] if L["sku"] == disc["sku"])
        assert line["qty"] == disc["invoice_qty"]

        report = reports_by_period[disc["report_period"]]
        row = next(R for R in report["rows"] if R["sku"] == disc["sku"])
        assert row["received_qty"] == disc["report_received_qty"]
        assert disc["invoice_qty"] != disc["report_received_qty"]


def test_golden_qa_aligned() -> None:
    truth = _load_truth()
    golden = json.loads((FIXTURES / "evals" / "golden_qa.json").read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in golden["cases"]}
    assert cases["spend_vendor_q3"]["expect"]["expected_amount"] == truth["aggregates"][
        "alpha_supplies_2024_q3_spend"
    ]
    assert cases["qty_discrepancy"]["expect"]["invoice_qty"] == 500
    assert cases["qty_discrepancy"]["expect"]["report_received_qty"] == 450
