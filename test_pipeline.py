"""Automated assertion suite verifying every maurices data dictionary caveat + 12-slide PPTX."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from pptx import Presentation

from charts import export_full_pack
from deck_builder import build_presentation_deck
from engine import load_and_analyze
from mock_data import generate_synthetic_csvs


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "data"
        out = Path(td) / "slides"
        paths = generate_synthetic_csvs(tmp, seed=7)
        res = load_and_analyze(paths["product"], paths["time"], paths["customer"])
        sub = res["subclasses"]
        diag = res["diagnostics"]

        # 1. Text ('010') vs Integer (10) composite join matched 100% of subclasses
        assert diag["joined_subclasses"] == len(sub) == 18, f"Expected 18 joined subclasses, got {diag['joined_subclasses']}"
        assert diag["weeks_count"] == 104, f"Expected 104 fiscal weeks, got {diag['weeks_count']}"

        # 2. Shared description ('FASHION CARDI') kept separate via composite key
        cardi = sub[sub["subclass_desc_raw"] == "FASHION CARDI"]
        assert len(cardi) == 2, "Duplicate 'FASHION CARDI' subclasses were erroneously merged!"
        assert cardi["subclass_label"].nunique() == 2, "Disambiguated labels must be unique!"

        # 3. Age '%' strings parsed into valid proportions (~1.0 total across bands)
        assert sub["ntf_under_51"].between(0.05, 0.99).all(), "Age % parsing failed!"

        # 4. Volume-weighted rollup check (must weight by positive net_sales_units, not unweighted mean)
        sweaters = sub[sub["dept_label"] == "SWEATERS & LAYERS"]
        unweighted = float(sweaters["ntf_under_51"].mean())
        weighted_expected = float(np.average(sweaters["ntf_under_51"], weights=sweaters["total_sales_units"].clip(lower=0)))
        dept_row = res["departments"].loc[res["departments"]["dept_label"] == "SWEATERS & LAYERS"].iloc[0]
        assert abs(float(dept_row["ntf_under_51"]) - weighted_expected) < 1e-9
        assert abs(weighted_expected - unweighted) > 0.005, "Weighted vs unweighted age share check should differ!"

        # 5. SOH is weekly snapshot averaged on STORE only (never summed across 104 weeks!)
        assert (sub["avg_store_soh_units"] < 5000).all(), "SOH looks summed instead of averaged!"
        assert 8.0 <= diag["store_missing_soh_pct"] <= 22.0, f"Unexpected missing SOH %: {diag['store_missing_soh_pct']}"
        assert 14.0 <= diag["store_st_over_100_pct"] <= 32.0, f"Unexpected >100% ST %: {diag['store_st_over_100_pct']}"
        assert diag["negative_unit_rows"] > 0, "Expected synthetic negative return weeks to be tested!"

        # 5b. Small-sample quantized NTF shrinkage check (e.g. 2 buyers -> 50%/50% in two <51 bands must shrink toward TOTAL)
        sparse_cust = pd.read_csv(paths["customer"])
        ntf_cols = [c for c in sparse_cust.columns if c.startswith("NTF ")]
        sparse_cust.loc[0, ntf_cols] = "0.00%"
        sparse_cust.loc[0, ntf_cols[1]] = "50.00%"
        sparse_cust.loc[0, ntf_cols[4]] = "50.00%"
        sparse_path = tmp / "sparse_cust.csv"
        sparse_cust.to_csv(sparse_path, index=False)
        res_sparse = load_and_analyze(paths["product"], paths["time"], sparse_path)
        row0_key = f"{int(sparse_cust.loc[0, 'dept'])}|{int(sparse_cust.loc[0, 'class'])}|{int(sparse_cust.loc[0, 'subclass'])}"
        shrunk_val = float(res_sparse["subclasses"].set_index("comp_key").loc[row0_key, "ntf_under_51"])
        assert shrunk_val < 0.96, f"Expected sparse 2-band 100% NTF fluke to shrink toward TOTAL, got {shrunk_val}"

        # 6. Export all 7 high-DPI slide charts + 2 CSVs + brief + 12-slide PPTX
        pack = export_full_pack(res, out, demo_mode=True)
        assert len(pack) == 10
        pptx_file = build_presentation_deck(res, pack, out / "maurices_Assortment_Strategy_Deck.pptx", demo_mode=True)
        assert pptx_file.exists() and pptx_file.stat().st_size > 250_000

        # 7. Programmatically audit PPTX geometry & speaker notes
        prs = Presentation(str(pptx_file))
        assert len(prs.slides) == 12, f"Expected 12 slides, got {len(prs.slides)}"
        w_max = prs.slide_width
        h_max = prs.slide_height
        for idx, sl in enumerate(prs.slides, start=1):
            notes_txt = sl.notes_slide.notes_text_frame.text.strip()
            assert len(notes_txt) > 40, f"Slide {idx} missing speaker notes!"
            for shp in sl.shapes:
                assert shp.left >= -5000 and shp.top >= -5000, f"Slide {idx} shape negative coords!"
                assert (shp.left + shp.width) <= w_max + 25000, f"Slide {idx} shape overflows width!"
                assert (shp.top + shp.height) <= h_max + 25000, f"Slide {idx} shape overflows height!"

    print("ALL_CAVEAT_AND_PPTX_ASSERTIONS_PASSED_OK")


if __name__ == "__main__":
    main()
