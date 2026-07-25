"""Offline golden-eval helpers (numeric tolerance + alert / citation checks)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_TOLERANCE = 0.01


@dataclass
class EvalFailure:
    case_id: str
    reason: str


@dataclass
class EvalReport:
    passed: int = 0
    failed: int = 0
    failures: list[EvalFailure] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "ok": self.ok,
            "failures": [{"case_id": f.case_id, "reason": f.reason} for f in self.failures],
        }


def load_golden_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("cases") or [])


def _nearly_equal(actual: float, expected: float, tolerance: float) -> bool:
    return abs(float(actual) - float(expected)) <= tolerance


def evaluate_case(
    case: dict[str, Any],
    result: dict[str, Any],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[str]:
    """Return a list of failure reasons (empty => pass)."""
    expect = case.get("expect") or {}
    etype = expect.get("type")
    errors: list[str] = []
    case_id = case.get("id", "unknown")

    if etype == "numeric":
        spend = (result.get("facts") or {}).get("spend") or {}
        actual = spend.get("total_amount")
        expected = expect.get("expected_amount")
        if actual is None:
            errors.append(f"{case_id}: missing facts.spend.total_amount")
        elif expected is None:
            errors.append(f"{case_id}: golden missing expected_amount")
        elif not _nearly_equal(actual, expected, tolerance):
            errors.append(
                f"{case_id}: amount {actual} != {expected} (tol={tolerance})"
            )
        expected_ids = set(expect.get("invoice_ids") or [])
        if expected_ids:
            got_ids = {i.get("invoice_id") for i in (spend.get("invoices") or [])}
            missing = expected_ids - got_ids
            if missing:
                errors.append(f"{case_id}: missing invoice_ids {sorted(missing)}")
        amount_str = str(expect.get("expected_amount"))
        if amount_str and amount_str not in (result.get("answer") or ""):
            # allow formatted variants like 10675.22 already in answer
            if f"{float(expected):.2f}" not in (result.get("answer") or ""):
                errors.append(f"{case_id}: answer missing expected amount text")

    elif etype == "discrepancy_alert":
        alerts = result.get("alerts") or []
        if not alerts:
            errors.append(f"{case_id}: expected discrepancy alerts, got none")
        else:
            match = None
            for alert in alerts:
                sku_ok = expect.get("sku") is None or alert.get("sku") == expect.get("sku")
                inv_ok = (
                    expect.get("invoice_id") is None
                    or alert.get("invoice_id") == expect.get("invoice_id")
                )
                if sku_ok and inv_ok:
                    match = alert
                    break
            if match is None:
                errors.append(
                    f"{case_id}: no alert for sku={expect.get('sku')} "
                    f"invoice={expect.get('invoice_id')}"
                )
            else:
                if "invoice_qty" in expect and not _nearly_equal(
                    match.get("invoice_qty", 0), expect["invoice_qty"], tolerance
                ):
                    errors.append(
                        f"{case_id}: invoice_qty {match.get('invoice_qty')} != {expect['invoice_qty']}"
                    )
                if "report_received_qty" in expect and not _nearly_equal(
                    match.get("report_received_qty", 0),
                    expect["report_received_qty"],
                    tolerance,
                ):
                    errors.append(
                        f"{case_id}: received_qty {match.get('report_received_qty')} "
                        f"!= {expect['report_received_qty']}"
                    )
                if expect.get("report_period") and match.get("report_period") != expect["report_period"]:
                    errors.append(
                        f"{case_id}: period {match.get('report_period')} != {expect['report_period']}"
                    )
        answer = result.get("answer") or ""
        markdown = result.get("markdown") or ""
        if "Discrepancy" not in answer and "Discrepancy" not in markdown:
            errors.append(f"{case_id}: response missing Discrepancy wording")

    elif etype == "citation":
        if expect.get("invoice_ids"):
            invoices = (result.get("facts") or {}).get("invoices")
            if invoices is None and (result.get("facts") or {}).get("spend"):
                invoices = (result["facts"]["spend"].get("invoices") or [])
            invoices = invoices or []
            got = {i.get("invoice_id") for i in invoices}
            # also allow answer text citations
            answer = result.get("answer") or ""
            for inv_id in expect["invoice_ids"]:
                if inv_id not in got and inv_id not in answer:
                    errors.append(f"{case_id}: missing citation {inv_id}")
        if expect.get("payment_terms"):
            contract = (result.get("facts") or {}).get("contract") or {}
            if contract.get("payment_terms") != expect["payment_terms"]:
                if expect["payment_terms"] not in (result.get("answer") or ""):
                    errors.append(
                        f"{case_id}: payment_terms {contract.get('payment_terms')} "
                        f"!= {expect['payment_terms']}"
                    )
        if expect.get("source_file"):
            contract = (result.get("facts") or {}).get("contract") or {}
            sources = result.get("sources") or []
            source_files = {str((s.get("metadata") or {}).get("source_file") or "") for s in sources}
            if (
                contract.get("source_file") != expect["source_file"]
                and expect["source_file"] not in source_files
                and expect["source_file"] not in (result.get("answer") or "")
            ):
                errors.append(f"{case_id}: missing source_file {expect['source_file']}")

    elif etype == "alert_count":
        alerts = result.get("alerts") or []
        expected_count = int(expect.get("min_count") or expect.get("count") or 0)
        if len(alerts) < expected_count:
            errors.append(
                f"{case_id}: expected >= {expected_count} alerts, got {len(alerts)}"
            )

    elif etype == "price_drift":
        review = (result.get("facts") or {}).get("review") or {}
        alerts = result.get("alerts") or review.get("alerts") or []
        recommendation = review.get("recommendation") or expect.get("recommendation")
        if expect.get("recommendation") and review.get("recommendation") != expect["recommendation"]:
            # also accept recommendation on alert
            alert_recs = {a.get("recommendation") for a in alerts}
            if expect["recommendation"] not in alert_recs and expect["recommendation"] not in (
                result.get("answer") or ""
            ):
                errors.append(
                    f"{case_id}: recommendation {review.get('recommendation')} != {expect['recommendation']}"
                )
        match = None
        for alert in alerts:
            if expect.get("invoice_id") and alert.get("invoice_id") != expect["invoice_id"]:
                continue
            if expect.get("sku") and alert.get("sku") != expect["sku"]:
                continue
            if alert.get("severity") in {None, "price_drift"} or alert.get("drift_pct") is not None:
                match = alert
                break
        if match is None and expect.get("invoice_id"):
            errors.append(f"{case_id}: missing price_drift alert for {expect.get('invoice_id')}")
        elif match is not None:
            if "drift_pct" in expect and abs(float(match.get("drift_pct") or 0) - float(expect["drift_pct"])) > tolerance:
                errors.append(
                    f"{case_id}: drift_pct {match.get('drift_pct')} != {expect['drift_pct']}"
                )
            if expect.get("po_number") and match.get("po_number") != expect["po_number"]:
                if review.get("po_number") != expect["po_number"]:
                    errors.append(f"{case_id}: po_number mismatch")
            if expect.get("po_match") is True and not (
                match.get("po_match") or review.get("po_match")
            ):
                errors.append(f"{case_id}: expected po_match=true")
        answer = result.get("answer") or ""
        if expect.get("recommendation") == "Reject" and "Reject" not in answer and "Reject" not in (
            review.get("summary") or ""
        ):
            errors.append(f"{case_id}: answer missing Reject recommendation")
        _ = recommendation

    else:
        errors.append(f"{case_id}: unknown expect.type {etype}")

    return errors


def run_golden_eval(
    cases: list[dict[str, Any]],
    results_by_id: dict[str, dict[str, Any]],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> EvalReport:
    report = EvalReport()
    for case in cases:
        case_id = case["id"]
        result = results_by_id.get(case_id)
        if result is None:
            report.failed += 1
            report.failures.append(EvalFailure(case_id, "missing query result"))
            continue
        errors = evaluate_case(case, result, tolerance=tolerance)
        if errors:
            report.failed += 1
            for reason in errors:
                report.failures.append(EvalFailure(case_id, reason))
        else:
            report.passed += 1
    return report
