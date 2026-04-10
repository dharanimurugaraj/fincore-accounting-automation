"""Chq/Ref picking from narration + amount line."""

from app.pipeline.schema_parser import _pick_ref_number


def test_prefers_bg_code_over_guarantee_word():
    narr = "COMM ON GUARANTEE AMENDMENT BG2026002"
    line = "Rs.0.00 Rs.1,180.00 OD Rs.1,180.00 Cr"
    assert _pick_ref_number(narr, line) == "BG2026002"


def test_prefers_utr_style_over_noise():
    narr = "NEFT CR-HDFCR5202602020628/CNRB/GOA BEVERAGES PVT LTD"
    line = "Rs.2,36,68,500.00 Rs.11,47,60,236.92 OD"
    r = _pick_ref_number(narr, line)
    assert "HDFCR" in r or r.startswith("HDFCR")
