"""Synthetic mock CSV generator mirroring the exact maurices 3-file schema & caveats.

Used ONLY for local testing / demo mode when competition CSVs are not yet placed in `data/`.
Reproduces all schema traps described in the data dictionary:
- 104 fiscal weeks (Oct 6, 2024 – Oct 3, 2026) on an August-start 4-5-4 calendar (12 exact columns)
- Product IDs stored as zero-padded text ('010') vs Customer IDs stored as integers (10)
- Duplicate subclass descriptions ('FASHION CARDI' appearing under two distinct IDs)
- STORE-only inventory with ~14% missing soh_units, ~22% weekly_sell_through > 100%, and occasional negative return weeks
- soh_units_total repeated across STORE and ONLINE rows (trap if summed)
- 48 age columns (TOTAL, NTF, EXISTING x 16 bands from 18 to 95) formatted as '13.44%'
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

AGE_BANDS_16 = [
    (18, 19), (20, 24), (25, 29), (30, 34),
    (35, 39), (40, 44), (45, 49), (50, 54),
    (55, 59), (60, 64), (65, 69), (70, 74),
    (75, 79), (80, 84), (85, 89), (90, 95),
]

CATALOG = [
    # (dept_id, dept_desc, class_id, class_desc, sub_id, sub_desc, base_sales, styles, youth_mean_age, online_sh, yoy_mult)
    (10, "DENIM", 101, "CORE & FASHION JEANS", 1001, "WIDE LEG & BARREL JEAN", 4800, 9, 34.5, 0.29, 1.28),
    (10, "DENIM", 101, "CORE & FASHION JEANS", 1002, "MID-RISE BOOTCUT JEAN", 6200, 14, 46.0, 0.19, 1.04),
    (10, "DENIM", 101, "CORE & FASHION JEANS", 1003, "HIGH-RISE STRAIGHT ANKLE", 5100, 10, 36.5, 0.27, 1.21),
    (10, "DENIM", 101, "CORE & FASHION JEANS", 1004, "CLASSIC PULL-ON JEGGING", 4400, 19, 56.5, 0.13, 0.91),
    (10, "DENIM", 102, "SEASONAL DENIM", 1005, "SCULPT STRETCH FLEX JEAN", 3900, 6, 37.0, 0.31, 1.34),
    (10, "DENIM", 102, "SEASONAL DENIM", 1006, "BASIC SKINNY WASH", 2600, 22, 53.0, 0.14, 0.79),
    (20, "KNIT TOPS", 201, "EVERYDAY TEES", 2001, "SEAMLESS RIBBED BODYSUIT & BABY TEE", 3700, 8, 33.0, 0.28, 1.25),
    (20, "KNIT TOPS", 201, "EVERYDAY TEES", 2002, "CORE V-NECK & CREW TEE", 5800, 16, 49.5, 0.15, 1.01),
    (20, "KNIT TOPS", 202, "GRAPHIC & NOVELTY KNITS", 2003, "PRINT PEPLUM KNIT TOP", 2100, 28, 58.0, 0.11, 0.76),
    (30, "SWEATERS & LAYERS", 301, "CARDIGANS", 3001, "FASHION CARDI", 3600, 8, 36.0, 0.26, 1.19),
    (30, "SWEATERS & LAYERS", 302, "HERITAGE KNITS", 3009, "FASHION CARDI", 1900, 24, 60.5, 0.10, 0.81),
    (30, "SWEATERS & LAYERS", 301, "CARDIGANS", 3002, "COZY TEXTURED PULLOVER", 4100, 12, 43.0, 0.21, 1.07),
    (40, "DRESSES & OCCASION", 401, "EVENT & DAY DRESSES", 4001, "MIDI OCCASION & EVENT DRESS", 4600, 9, 34.0, 0.32, 1.29),
    (40, "DRESSES & OCCASION", 401, "EVENT & DAY DRESSES", 4002, "TIERED SMOCKED MAXI", 3100, 15, 41.0, 0.24, 1.09),
    (50, "WOVENS & WORKWEAR", 501, "BLOUSES & BLAZERS", 5001, "EFFORTLESS STRETCH BLAZER", 3800, 7, 37.5, 0.26, 1.22),
    (50, "WOVENS & WORKWEAR", 501, "BLOUSES & BLAZERS", 5002, "TRADITIONAL FLORAL CHIFFON TOP", 2200, 31, 59.0, 0.11, 0.74),
    (60, "ATHLEISURE & LOUNGE", 601, "ACTIVE COMFORT", 6001, "SOFT-SCULPT TRAVEL SET", 3500, 6, 35.5, 0.30, 1.32),
    (60, "ATHLEISURE & LOUNGE", 601, "ACTIVE COMFORT", 6002, "FLEECE LOUNGE JOGGER", 2900, 17, 51.0, 0.16, 0.94),
]


def _age_distribution(mean_age: float, std_age: float = 12.5) -> np.ndarray:
    mids = np.array([0.5 * (lo + hi) for lo, hi in AGE_BANDS_16])
    weights = np.exp(-0.5 * ((mids - mean_age) / std_age) ** 2)
    return weights / weights.sum()


def generate_synthetic_csvs(out_dir: Path | str, seed: int = 42) -> dict[str, Path]:
    """Generate synthetic `product_file_masked.csv`, `time_file.csv`, `dept_class_subclass_age.csv`."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    # 1. time_file.csv: 104 fiscal weeks (Oct 6, 2024 – Oct 3, 2026), exact 12-column schema
    start = date(2024, 10, 6)
    time_rows = []
    for i in range(104):
        ws = start + timedelta(days=7 * i)
        we = ws + timedelta(days=6)
        m = ws.month
        if m in (8, 9, 10):
            qtr_num, qtr = 1, "Q1"
        elif m in (11, 12, 1):
            qtr_num, qtr = 2, "Q2"
        elif m in (2, 3, 4):
            qtr_num, qtr = 3, "Q3"
        else:
            qtr_num, qtr = 4, "Q4"
        fy = ws.year + 1 if m >= 8 else ws.year
        wk_in_yr = ((i + 9) % 52) + 1
        mo_in_yr = ((m - 8) % 12) + 1
        fw_id = fy * 100 + wk_in_yr
        time_rows.append(
            {
                "fiscal_week_id": fw_id,
                "fiscal_month_id": fy * 100 + mo_in_yr,
                "fiscal_quarter_id": fy * 10 + qtr_num,
                "fiscal_year_id": fy,
                "week_start_date": ws.isoformat(),
                "week_end_date": we.isoformat(),
                "fiscal_month_label": ws.strftime("%b"),
                "fiscal_quarter_label": qtr,
                "fiscal_year_label": f"FY{str(fy)[-2:]}",
                "week_seq": i + 1,
                "month_in_year": mo_in_yr,
                "week_in_year": wk_in_yr,
            }
        )
    time_df = pd.DataFrame(time_rows)

    # 2. dept_class_subclass_age.csv (integer IDs + 48 text % columns)
    cust_rows = []
    for dept_id, _, class_id, _, sub_id, _, _, _, youth_age, _, _ in CATALOG:
        rec: dict[str, object] = {
            "dept": int(dept_id),
            "class": int(class_id),
            "subclass": int(sub_id),
        }
        exist_dist = _age_distribution(youth_age + 5.5, 13.0)
        ntf_dist = _age_distribution(youth_age - 3.5, 11.5)
        tot_dist = 0.72 * exist_dist + 0.28 * ntf_dist
        for seg_name, base_lbl, dist in (("TOTAL", "total", tot_dist), ("NTF", "NTF", ntf_dist), ("EXISTING", "existing", exist_dist)):
            for (lo, hi), val in zip(AGE_BANDS_16, dist):
                rec[f"{seg_name} {lo}-{hi} % of {base_lbl}"] = f"{100.0 * val:.2f}%"
        cust_rows.append(rec)
    cust_df = pd.DataFrame(cust_rows)

    # 3. product_file_masked.csv (zero-padded text IDs, STORE + ONLINE rows)
    prod_rows = []
    for idx_w, trow in enumerate(time_rows):
        fw = int(trow["fiscal_week_id"])
        qtr = str(trow["fiscal_quarter_label"])
        is_yr2 = idx_w >= 52
        q_boost = {"Q1": 1.03, "Q2": 1.24, "Q3": 0.92, "Q4": 0.96}[qtr]

        for dept_id, dept_desc, class_id, class_desc, sub_id, sub_desc, base_sales, styles, _, online_sh, yoy_mult in CATALOG:
            yr_factor = yoy_mult if is_yr2 else 1.0
            noise = float(rng.uniform(0.86, 1.15))
            wk_total_dollars = base_sales * q_boost * yr_factor * noise
            aur_masked = float(rng.uniform(24.0, 44.0))
            wk_styles = max(2, int(round(styles * rng.uniform(0.9, 1.1))))

            store_dollars = wk_total_dollars * (1.0 - online_sh)
            online_dollars = wk_total_dollars * online_sh
            store_units = max(1, int(round(store_dollars / aur_masked)))
            online_units = max(1, int(round(online_dollars / aur_masked)))

            # ~2% net-return weeks on online rows to test negative net_sales_units handling
            if rng.random() < 0.02:
                online_units = -max(1, int(online_units * 0.1))
                online_dollars = online_units * aur_masked

            missing_stock = rng.random() < 0.14
            if missing_stock:
                soh = np.nan
                sc_cnt = np.nan
                st_rate = np.nan
                depth = np.nan
                soh_ref = np.nan
            else:
                fast_restock = rng.random() < 0.22
                st_rate = float(rng.uniform(1.04, 1.45)) if fast_restock else float(rng.uniform(0.05, 0.18))
                soh = max(5.0, round(store_units / st_rate, 1))
                sc_cnt = max(2, int(round(wk_styles * rng.uniform(1.2, 1.8))))
                depth = round(soh / sc_cnt, 2)
                soh_ref = soh

            common = {
                "the_week": fw,
                "dept_idnt": f"{dept_id:03d}",
                "dept_desc": dept_desc,
                "class_idnt": f"{class_id:03d}",
                "class_desc": class_desc,
                "sbclass_idnt": f"{sub_id:04d}",
                "sbclass_desc": sub_desc,
                "soh_units_total": soh_ref,
            }
            prod_rows.append(
                {
                    **common,
                    "channel": "STORE",
                    "net_sales_dollars": round(store_dollars, 2),
                    "net_sales_units": store_units,
                    "style_count": wk_styles,
                    "soh_units": soh,
                    "style_color_count": sc_cnt,
                    "weekly_sell_through": round(st_rate, 4) if pd.notna(st_rate) else np.nan,
                    "depth_per_choice": depth,
                }
            )
            prod_rows.append(
                {
                    **common,
                    "channel": "ONLINE",
                    "net_sales_dollars": round(online_dollars, 2),
                    "net_sales_units": online_units,
                    "style_count": max(2, int(round(wk_styles * 1.05))),
                    "soh_units": np.nan,
                    "style_color_count": np.nan,
                    "weekly_sell_through": np.nan,
                    "depth_per_choice": np.nan,
                }
            )

    prod_df = pd.DataFrame(prod_rows)

    paths = {
        "product": out / "product_file_masked.csv",
        "time": out / "time_file.csv",
        "customer": out / "dept_class_subclass_age.csv",
    }
    prod_df.to_csv(paths["product"], index=False)
    time_df.to_csv(paths["time"], index=False)
    cust_df.to_csv(paths["customer"], index=False)
    return paths
