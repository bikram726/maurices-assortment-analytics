"""Automated assertion suite verifying every maurices data dictionary caveat."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from charts import export_full_pack
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

        # 2. Shared description ('FASHION CARDI') kept separate via composite key
        cardi = sub[sub["subclass_desc_raw"] == "FASHION CARDI"]
        assert len(cardi) == 2, "Duplicate 'FASHION CARDI' subclasses were erroneously merged!"
        assert cardi["subclass_label"].nunique() == 2, "Disambiguated labels must be unique!"

        # 3. Age '%' strings parsed into valid proportions (~1.0 total across bands)
        assert sub["ntf_under_51"].between(0.05, 0.99).all(), "Age % parsing failed!"

        # 4. Volume-weighted rollup check (must weight by net_sales_units, not unweighted mean)
        sweaters = sub[sub["dept_label"] == "SWEATERS & LAYERS"]
        unweighted = float(sweaters["ntf_under_51"].mean())
        weighted_expected = float(np.average(sweaters["ntf_under_51"], weights=sweaters["total_sales_units"]))
        dept_row = res["departments"].loc[res["departments"]["dept_label"] == "SWEATERS & LAYERS"].iloc[0]
        assert abs(float(dept_row["ntf_under_51"]) - weighted_expected) < 1e-9
        assert abs(weighted_expected - unweighted) > 0.005, "Weighted vs unweighted age share check should differ!"

        # 5. SOH is weekly snapshot averaged on STORE only (never summed across 104 weeks!)
        assert (sub["avg_store_soh_units"] < 2500).all(), "SOH looks summed instead of averaged!"
        assert 8.0 <= diag["store_missing_soh_pct"] <= 22.0, f"Unexpected missing SOH %: {diag['store_missing_soh_pct']}"
        assert 14.0 <= diag["store_st_over_100_pct"] <= 32.0, f"Unexpected >100% ST %: {diag['store_st_over_100_pct']}"

        # 6. Export all 6 300-DPI slide charts + CSV + brief
        pack = export_full_pack(res, out, demo_mode=True)
        assert len(pack) == 8
        for name, fpath in pack.items():
            assert fpath.exists() and fpath.stat().st_size > 1500, f"Artifact {name} failed: {fpath}"

    print("ALL_CAVEAT_ASSERTIONS_PASSED_OK")


if __name__ == "__main__":
    main()
