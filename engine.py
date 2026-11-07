"""Caveat-safe local analytics engine for the maurices Assortment Case Competition.

Runs 100% offline on local CSVs (zero network/AI calls). Enforces every data
dictionary rule:
1. Joins customer & product files on composite (dept, class, subclass) after
   normalizing text ("004") vs integer (4) IDs.
2. Keys all subclass metrics on composite IDs so shared descriptions (e.g., two
   "FASHION CARDI" subclasses) never collide.
3. Strips "%" from all 48 age-band columns and weights age rollups by unit volume
   (never unweighted averages of distributions).
4. Treats soh_units as a weekly STORE-only snapshot (mean across active store
   weeks, never summed; ignores ~14% null store stock rows cleanly).
5. Computes sell-through & depth-per-choice on STORE rows only, handling >100%
   mid-week restock weeks via median + fast-turn share.
6. Expresses "profitability" via Assortment Productivity (Sales/Style Index,
   Sell-Through, Depth per Choice) and masks raw dollars into Index / % Share.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def normalize_id_series(s: pd.Series) -> pd.Series:
    """Convert text ('004', ' 4 ', '4.0') or integer IDs into canonical string keys."""
    txt = s.astype(str).str.strip()
    num = pd.to_numeric(txt, errors="coerce")
    is_num = num.notna()
    out = txt.copy()
    out.loc[is_num] = num.loc[is_num].astype(np.int64).astype(str)
    return out


def parse_pct_series(s: pd.Series) -> pd.Series:
    """Convert percentage text like '13.44%' (or numeric 0.1344 / 13.44) into 0.0-1.0 float."""
    if pd.api.types.is_numeric_dtype(s):
        vals = pd.to_numeric(s, errors="coerce").fillna(0.0)
        # If stored as 0..100 numbers rather than 0..1 proportions
        return vals / 100.0 if vals.max() > 1.5 else vals
    has_pct = s.astype(str).str.contains("%", na=False).any()
    cleaned = s.astype(str).str.strip().str.replace("%", "", regex=False).replace({"": "0", "nan": "0", "None": "0"})
    vals = pd.to_numeric(cleaned, errors="coerce").fillna(0.0)
    if has_pct or vals.max() > 1.5:
        return vals / 100.0
    return vals


def _pick_col(cols: list[str], candidates: list[str], fallback_regex: str | None = None) -> str | None:
    lower_map = {c.lower().strip(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    if fallback_regex:
        for c in cols:
            if re.search(fallback_regex, c, re.I):
                return c
    return None


def detect_product_columns(df: pd.DataFrame) -> dict[str, str | None]:
    cols = list(df.columns)
    return {
        "dept_id": _pick_col(cols, ["dept_id", "department_id", "dept", "dept_num", "dept_nbr"], r"^dept.*(id|num|nbr|code)$|^dept$"),
        "dept_desc": _pick_col(cols, ["dept_desc", "department_desc", "department_description", "dept_name", "department"], r"dept.*(desc|name)"),
        "class_id": _pick_col(cols, ["class_id", "class", "class_num", "class_nbr", "cls_id"], r"^class.*(id|num|nbr|code)$|^class$"),
        "class_desc": _pick_col(cols, ["class_desc", "class_description", "class_name"], r"class.*(desc|name)"),
        "subclass_id": _pick_col(cols, ["subclass_id", "subclass", "sub_class_id", "subclass_num", "sbc_id"], r"sub.?class.*(id|num|nbr|code)$|^subclass$"),
        "subclass_desc": _pick_col(cols, ["subclass_desc", "subclass_description", "subclass_name", "sub_class_desc"], r"sub.?class.*(desc|name)"),
        "week": _pick_col(cols, ["the_week", "fiscal_week_id", "week_id", "fiscal_week"], r"the_week|week"),
        "channel": _pick_col(cols, ["channel", "channel_code", "selling_channel"], r"channel"),
        "sales_dollars": _pick_col(cols, ["net_sales_dollars", "sales_dollars", "net_sales_amt", "net_sales"], r"net_sales.*dollar|sales.*dollar"),
        "sales_units": _pick_col(cols, ["net_sales_units", "sales_units", "net_units", "units_sold"], r"net_sales.*unit|sales.*unit"),
        "style_count": _pick_col(cols, ["style_count", "styles", "active_styles"], r"^style_count$|^styles$"),
        "soh_units": _pick_col(cols, ["soh_units", "eoh_units", "stock_on_hand"], r"^soh_units$"),
        "style_color_count": _pick_col(cols, ["style_color_count", "choice_count", "style_colors"], r"style_color"),
        "weekly_sell_through": _pick_col(cols, ["weekly_sell_through", "sell_through", "sell_thru"], r"sell_thr"),
        "depth_per_choice": _pick_col(cols, ["depth_per_choice", "choice_depth"], r"depth_per_choice|depth"),
        "soh_units_total": _pick_col(cols, ["soh_units_total", "total_soh_units"], r"soh_units_total"),
    }


def detect_time_columns(df: pd.DataFrame) -> dict[str, str | None]:
    cols = list(df.columns)
    return {
        "week": _pick_col(cols, ["fiscal_week_id", "the_week", "week_id", "fiscal_week"], r"fiscal_week_id|week"),
        "fiscal_year": _pick_col(cols, ["fiscal_year", "fy", "year", "fiscal_yr"], r"fiscal_y|year"),
        "fiscal_quarter": _pick_col(cols, ["fiscal_quarter", "quarter", "fiscal_qtr", "qtr"], r"quarter|qtr"),
        "fiscal_month": _pick_col(cols, ["fiscal_month", "month", "fiscal_mo", "month_name"], r"month"),
        "week_start": _pick_col(cols, ["week_start_date", "start_date", "week_start", "week_ending_date", "date"], r"date|start|end"),
    }


def classify_age_columns(df: pd.DataFrame) -> dict[str, dict[str, list[str]]]:
    """Classify the 48 customer age columns into TOTAL / NTF / EXISTING and strategic age cohorts."""
    groups: dict[str, dict[str, list[str]]] = {
        seg: {"all": [], "under_51": [], "under_40": [], "liv_35_44": [], "young_18_34": [], "protect_45_plus": []}
        for seg in ("TOTAL", "NTF", "EXISTING")
    }
    id_like = {"dept", "dept_id", "department", "department_id", "class", "class_id", "subclass", "subclass_id"}

    for col in df.columns:
        cl = col.lower().strip()
        if cl in id_like or cl.endswith(("_desc", "_name", "_description")):
            continue
        nums = [int(x) for x in re.findall(r"\d{2}", cl) if 16 <= int(x) <= 99]
        if not nums:
            continue

        if re.search(r"(^|[_\s-])(ntf|new[_\s-]?to[_\s-]?file|new)($|[_\s\d-])", cl):
            seg = "NTF"
        elif re.search(r"(^|[_\s-])(exist|existing|ret|retained|current)($|[_\s\d-])", cl):
            seg = "EXISTING"
        else:
            seg = "TOTAL"
        lo = nums[0]
        hi = nums[1] if len(nums) > 1 else (95 if "+" in cl else lo + 4)
        mid = 0.5 * (lo + hi)

        g = groups[seg]
        g["all"].append(col)
        if mid < 51.0:
            g["under_51"].append(col)
        if mid < 40.0:
            g["under_40"].append(col)
        if 35 <= lo and hi <= 45:
            g["liv_35_44"].append(col)
        elif lo < 35 and mid < 35:
            g["young_18_34"].append(col)
        if lo >= 45 or mid >= 45:
            g["protect_45_plus"].append(col)

    return groups


def load_and_analyze(
    product_csv: Path | str,
    time_csv: Path | str,
    customer_csv: Path | str,
    denim_regex: str = r"\b(?:denim|jean|jeans|jegging)\b",
) -> dict[str, Any]:
    """Load the 3 maurices CSVs locally and build caveat-safe analytical tables."""
    prod = pd.read_csv(product_csv, low_memory=False)
    time_df = pd.read_csv(time_csv, low_memory=False)
    cust = pd.read_csv(customer_csv, low_memory=False)

    pcols = detect_product_columns(prod)
    tcols = detect_time_columns(time_df)
    c_dept = _pick_col(list(cust.columns), ["dept_id", "department_id", "dept", "department"], r"dept")
    c_cls = _pick_col(list(cust.columns), ["class_id", "class", "cls_id"], r"^class")
    c_sub = _pick_col(list(cust.columns), ["subclass_id", "subclass", "sub_class_id", "sub_class"], r"sub.?class")

    required_p = ["dept_id", "class_id", "subclass_id", "week", "channel", "sales_dollars", "sales_units", "style_count"]
    missing = [k for k in required_p if not pcols.get(k)]
    if missing or not (c_dept and c_cls and c_sub) or not tcols.get("week"):
        raise ValueError(f"Column auto-detection incomplete. Missing product={missing}, cust={(c_dept, c_cls, c_sub)}, time={tcols}")

    # 1. Canonical composite keys (fixes text '004' vs integer 4 mismatch + duplicate subclass descriptions)
    prod["dept_key"] = normalize_id_series(prod[pcols["dept_id"]])
    prod["class_key"] = normalize_id_series(prod[pcols["class_id"]])
    prod["subclass_key"] = normalize_id_series(prod[pcols["subclass_id"]])
    prod["comp_key"] = prod["dept_key"] + "|" + prod["class_key"] + "|" + prod["subclass_key"]

    prod["dept_label"] = prod[pcols["dept_desc"]].astype(str).str.strip() if pcols["dept_desc"] else ("Dept " + prod["dept_key"])
    prod["class_label"] = prod[pcols["class_desc"]].astype(str).str.strip() if pcols["class_desc"] else ("Class " + prod["class_key"])
    raw_sub_desc = prod[pcols["subclass_desc"]].astype(str).str.strip() if pcols["subclass_desc"] else ("Subclass " + prod["subclass_key"])
    prod["subclass_desc_raw"] = raw_sub_desc

    # Disambiguate shared descriptions like two "FASHION CARDI" subclasses!
    desc_key_counts = prod.groupby("subclass_desc_raw")["comp_key"].nunique()
    dup_descs = set(desc_key_counts[desc_key_counts > 1].index)
    prod["subclass_label"] = np.where(
        prod["subclass_desc_raw"].isin(dup_descs),
        prod["subclass_desc_raw"] + " [#" + prod["subclass_key"] + "]",
        prod["subclass_desc_raw"],
    )

    # Numeric coercion on product metrics
    for k in ("sales_dollars", "sales_units", "style_count", "soh_units", "style_color_count", "weekly_sell_through", "depth_per_choice", "soh_units_total"):
        col = pcols.get(k)
        if col and col in prod.columns:
            if k == "weekly_sell_through" and not pd.api.types.is_numeric_dtype(prod[col]):
                prod[k] = parse_pct_series(prod[col])
            else:
                prod[k] = pd.to_numeric(prod[col], errors="coerce")
        else:
            prod[k] = np.nan

    # Normalize weekly_sell_through scale to 0..1+ ratio (e.g. 1.0 = 100%)
    valid_st = prod["weekly_sell_through"].dropna()
    if len(valid_st) and valid_st.median() > 2.5:
        prod["weekly_sell_through"] = prod["weekly_sell_through"] / 100.0

    prod["channel_norm"] = prod[pcols["channel"]].astype(str).str.upper().str.strip()
    prod["week_key"] = normalize_id_series(prod[pcols["week"]])

    # 2. Join Time File on fiscal_week_id = the_week
    time_clean = time_df.copy()
    time_clean["week_key"] = normalize_id_series(time_clean[tcols["week"]])
    time_clean = time_clean.drop_duplicates(subset=["week_key"]).sort_values("week_key")
    # Order weeks chronologically (numeric sort on fiscal_week_id)
    time_clean["week_num_sort"] = pd.to_numeric(time_clean["week_key"], errors="coerce")
    if time_clean["week_num_sort"].notna().all():
        time_clean = time_clean.sort_values("week_num_sort").reset_index(drop=True)
    time_clean["seq_week"] = np.arange(1, len(time_clean) + 1)
    half_point = max(1, len(time_clean) // 2)
    time_clean["period_half"] = np.where(time_clean["seq_week"] <= half_point, "Year_1", "Year_2")

    if tcols["fiscal_quarter"]:
        q_raw = time_clean[tcols["fiscal_quarter"]].astype(str).str.upper().str.strip()
        time_clean["qtr_label"] = np.where(q_raw.str.startswith("Q"), q_raw, "Q" + q_raw)
    else:
        time_clean["qtr_label"] = "Q" + (((time_clean["seq_week"] - 1) % 52) // 13 + 1).astype(str)

    prod = prod.merge(
        time_clean[["week_key", "seq_week", "period_half", "qtr_label"]],
        on="week_key",
        how="left",
    )

    # 3. Parse Customer Age File (48 % columns, composite key dept+class+subclass)
    cust_clean = cust.copy()
    cust_clean["dept_key"] = normalize_id_series(cust_clean[c_dept])
    cust_clean["class_key"] = normalize_id_series(cust_clean[c_cls])
    cust_clean["subclass_key"] = normalize_id_series(cust_clean[c_sub])
    cust_clean["comp_key"] = cust_clean["dept_key"] + "|" + cust_clean["class_key"] + "|" + cust_clean["subclass_key"]
    cust_clean = cust_clean.drop_duplicates(subset=["comp_key"])

    age_map = classify_age_columns(cust_clean)
    all_age_cols = sorted({c for seg in age_map.values() for c in seg["all"]})
    for c in all_age_cols:
        cust_clean[c] = parse_pct_series(cust_clean[c])

    for seg in ("TOTAL", "NTF", "EXISTING"):
        for bucket in ("under_51", "under_40", "liv_35_44", "young_18_34", "protect_45_plus"):
            bcols = age_map[seg][bucket]
            cust_clean[f"{seg.lower()}_{bucket}"] = cust_clean[bcols].sum(axis=1) if bcols else np.nan

    # 4. Caveat-Safe Subclass Aggregation (STORE vs ONLINE separated properly)
    is_store = prod["channel_norm"].str.contains("STORE", na=False)
    is_online = prod["channel_norm"].str.contains("ONLINE|WEB|ECOM", na=False)

    meta = (
        prod.groupby("comp_key", as_index=False)
        .agg(
            dept_key=("dept_key", "first"),
            dept_label=("dept_label", "first"),
            class_key=("class_key", "first"),
            class_label=("class_label", "first"),
            subclass_key=("subclass_key", "first"),
            subclass_label=("subclass_label", "first"),
            subclass_desc_raw=("subclass_desc_raw", "first"),
            total_sales_dollars=("sales_dollars", "sum"),
            total_sales_units=("sales_units", "sum"),
            weeks_present=("week_key", "nunique"),
        )
    )

    # Style breadth: weekly max across channels (styles offered that week), then averaged across active weeks
    wk_styles = (
        prod.groupby(["comp_key", "week_key"], as_index=False)
        .agg(weekly_styles=("style_count", "max"), soh_ref=("soh_units_total", "first"))
    )
    style_agg = wk_styles.groupby("comp_key", as_index=False).agg(
        avg_style_count=("weekly_styles", "mean"),
        avg_soh_ref=("soh_ref", "mean"),
    )

    # STORE-only inventory & sell-through (NEVER sum soh_units; ONLINE has no sell-through)
    store_df = prod.loc[is_store].copy()
    store_agg = store_df.groupby("comp_key", as_index=False).agg(
        store_sales_dollars=("sales_dollars", "sum"),
        store_sales_units=("sales_units", "sum"),
        store_rows=("week_key", "count"),
        store_stock_rows=("soh_units", lambda s: int(s.notna().sum())),
        avg_store_soh_units=("soh_units", "mean"),
        avg_style_color_count=("style_color_count", "mean"),
        median_store_sell_through=("weekly_sell_through", "median"),
        mean_store_sell_through=("weekly_sell_through", "mean"),
        pct_weeks_st_over_100=("weekly_sell_through", lambda s: float((s.dropna() > 1.0).mean()) if s.notna().any() else np.nan),
        avg_depth_per_choice=("depth_per_choice", "mean"),
    )
    store_agg["missing_stock_share"] = 1.0 - (store_agg["store_stock_rows"] / store_agg["store_rows"].clip(lower=1))

    online_agg = prod.loc[is_online].groupby("comp_key", as_index=False).agg(
        online_sales_dollars=("sales_dollars", "sum"),
        online_sales_units=("sales_units", "sum"),
    )

    # YoY Momentum (Year 2 vs Year 1)
    yoy = (
        prod.groupby(["comp_key", "period_half"])["sales_dollars"]
        .sum()
        .unstack(fill_value=0.0)
        .reset_index()
    )
    for col_y in ("Year_1", "Year_2"):
        if col_y not in yoy.columns:
            yoy[col_y] = 0.0
    yoy["yoy_sales_growth"] = np.where(
        yoy["Year_1"] > 0, (yoy["Year_2"] - yoy["Year_1"]) / yoy["Year_1"], np.nan
    )

    cust_keep = [
        "comp_key",
        "total_under_51", "total_under_40", "total_liv_35_44", "total_young_18_34", "total_protect_45_plus",
        "ntf_under_51", "ntf_under_40", "ntf_liv_35_44", "ntf_young_18_34", "ntf_protect_45_plus",
        "existing_under_51", "existing_under_40", "existing_liv_35_44", "existing_young_18_34", "existing_protect_45_plus",
    ]
    sub = (
        meta.merge(style_agg, on="comp_key", how="left")
        .merge(store_agg, on="comp_key", how="left")
        .merge(online_agg, on="comp_key", how="left")
        .merge(yoy[["comp_key", "Year_1", "Year_2", "yoy_sales_growth"]], on="comp_key", how="left")
        .merge(cust_clean[cust_keep], on="comp_key", how="left")
    )
    sub["online_sales_dollars"] = sub["online_sales_dollars"].fillna(0.0)
    sub["store_sales_dollars"] = sub["store_sales_dollars"].fillna(0.0)

    # Relative shares & masked-safe Productivity Indices (Chain = 100)
    chain_dollars = max(float(sub["total_sales_dollars"].sum()), 1e-9)
    chain_units = max(float(sub["total_sales_units"].sum()), 1e-9)
    chain_styles = max(float(sub["avg_style_count"].fillna(0).sum()), 1e-9)

    sub["sales_dollar_share"] = sub["total_sales_dollars"] / chain_dollars
    sub["sales_unit_share"] = sub["total_sales_units"] / chain_units
    sub["style_share"] = sub["avg_style_count"].fillna(0.0) / chain_styles
    sub["online_share"] = np.where(sub["total_sales_dollars"] > 0, sub["online_sales_dollars"] / sub["total_sales_dollars"], 0.0)

    sub["sales_per_style"] = np.where(sub["avg_style_count"] > 0, sub["total_sales_dollars"] / sub["avg_style_count"], np.nan)
    chain_sps = float(sub["total_sales_dollars"].sum() / max(sub["avg_style_count"].fillna(0).sum(), 1.0))
    sub["sales_per_style_idx"] = 100.0 * (sub["sales_per_style"] / max(chain_sps, 1e-9))

    # NTF Youth Lift: how much younger new-to-file buyers are vs existing buyers in this subclass
    sub["ntf_youth_lift"] = sub["ntf_under_51"] - sub["existing_under_51"]

    # Denim Bet flag
    combined_text = sub["dept_label"] + " " + sub["class_label"] + " " + sub["subclass_label"]
    sub["is_denim"] = combined_text.str.contains(denim_regex, case=False, regex=True, na=False)

    # Success Criteria Composite Scores (0-100 percentiles)
    sub["sc1_volume_profit_pct"] = 100.0 * (
        0.40 * sub["total_sales_dollars"].rank(pct=True)
        + 0.30 * sub["total_sales_units"].rank(pct=True)
        + 0.30 * sub["sales_per_style"].rank(pct=True)
    )
    sub["sc2_younger_ntf_pct"] = 100.0 * (
        0.45 * sub["ntf_under_51"].rank(pct=True)
        + 0.35 * sub["ntf_liv_35_44"].rank(pct=True)
        + 0.20 * sub["online_share"].rank(pct=True)
    )
    sub["ideal_assortment_score"] = 0.55 * sub["sc1_volume_profit_pct"] + 0.45 * sub["sc2_younger_ntf_pct"]

    # 4-Quadrant Merchandising Action Tier
    med_sps = float(sub["sales_per_style_idx"].median())
    med_youth = float(sub["ntf_under_51"].median())
    med_styles = float(sub["avg_style_count"].median())

    def _classify_row(r: pd.Series) -> str:
        hi_prod = bool(r["sales_per_style_idx"] >= med_sps)
        hi_youth = bool(r["ntf_under_51"] >= med_youth)
        if hi_prod and hi_youth:
            if pd.notna(r["avg_style_count"]) and r["avg_style_count"] < med_styles:
                return "Expand Depth & Styles (Under-Assorted Gem)"
            return "Invest & Scale (Hero + Liv Growth)"
        if hi_prod and not hi_youth:
            return "Protect Core (45+ Cash Cow)"
        if (not hi_prod) and hi_youth:
            return "Curate & Refresh (Trim Styles, Keep Trend)"
        return "Rationalize Bloat (Cut Over-Assorted Tail)"

    sub["action_tier"] = sub.apply(_classify_row, axis=1)

    # 5. Volume-Weighted Rollups (Department & Class — NEVER unweighted age % mean!)
    dept_rollup = weighted_group_rollup(sub, ["dept_key", "dept_label"])
    class_rollup = weighted_group_rollup(sub, ["dept_key", "dept_label", "class_key", "class_label"])

    # 6. Weekly / Quarterly Time Series by Channel & Denim
    ts_weekly = (
        prod.groupby(["seq_week", "week_key", "qtr_label", "period_half", "channel_norm"], as_index=False)
        .agg(sales_dollars=("sales_dollars", "sum"), sales_units=("sales_units", "sum"))
    )
    total_wk_dollars = max(float(ts_weekly["sales_dollars"].sum()), 1e-9)
    ts_weekly["sales_share_pct"] = 100.0 * ts_weekly["sales_dollars"] / total_wk_dollars

    return {
        "subclasses": sub.sort_values("ideal_assortment_score", ascending=False).reset_index(drop=True),
        "departments": dept_rollup.sort_values("sales_dollar_share", ascending=False).reset_index(drop=True),
        "classes": class_rollup.sort_values("sales_dollar_share", ascending=False).reset_index(drop=True),
        "weekly": ts_weekly,
        "diagnostics": {
            "product_rows": len(prod),
            "weeks_count": int(prod["week_key"].nunique()),
            "customer_subclasses": len(cust_clean),
            "joined_subclasses": int(sub["ntf_under_51"].notna().sum()),
            "duplicate_descriptions_disambiguated": sorted(list(dup_descs)),
            "store_missing_soh_pct": round(100.0 * float(store_df["soh_units"].isna().mean()), 1) if len(store_df) else 0.0,
            "store_st_over_100_pct": round(100.0 * float((store_df["weekly_sell_through"].dropna() > 1.0).mean()), 1) if len(store_df) else 0.0,
            "denim_subclass_count": int(sub["is_denim"].sum()),
            "chain_weighted_under_51": float(np.average(sub["total_under_51"].fillna(0), weights=sub["total_sales_units"].clip(lower=1))),
            "chain_weighted_ntf_under_51": float(np.average(sub["ntf_under_51"].fillna(0), weights=sub["total_sales_units"].clip(lower=1))),
            "chain_weighted_liv_35_44": float(np.average(sub["ntf_liv_35_44"].fillna(0), weights=sub["total_sales_units"].clip(lower=1))),
            "chain_online_share": float(sub["online_sales_dollars"].sum() / chain_dollars),
        },
    }


def weighted_group_rollup(sub: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Roll up subclass metrics to Class or Department weighting age distributions by unit volume."""
    age_fields = [
        "total_under_51", "total_under_40", "total_liv_35_44", "total_protect_45_plus",
        "ntf_under_51", "ntf_under_40", "ntf_liv_35_44", "ntf_young_18_34", "ntf_protect_45_plus",
        "existing_under_51", "existing_protect_45_plus",
    ]
    rows: list[dict[str, Any]] = []
    chain_dollars = max(float(sub["total_sales_dollars"].sum()), 1e-9)
    chain_units = max(float(sub["total_sales_units"].sum()), 1e-9)
    chain_styles = max(float(sub["avg_style_count"].fillna(0).sum()), 1e-9)
    chain_sps = chain_dollars / chain_styles

    for keys, grp in sub.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        rec = {col: val for col, val in zip(group_cols, keys)}
        dollars = float(grp["total_sales_dollars"].sum())
        units = float(grp["total_sales_units"].sum())
        styles = float(grp["avg_style_count"].fillna(0).sum())
        online_d = float(grp["online_sales_dollars"].sum())
        y1 = float(grp["Year_1"].sum())
        y2 = float(grp["Year_2"].sum())

        rec.update(
            {
                "subclass_count": len(grp),
                "total_sales_dollars": dollars,
                "total_sales_units": units,
                "avg_style_count": styles,
                "sales_dollar_share": dollars / chain_dollars,
                "sales_unit_share": units / chain_units,
                "style_share": styles / chain_styles,
                "assortment_gap_bps": (dollars / chain_dollars - styles / chain_styles) * 100.0,
                "sales_per_style_idx": 100.0 * ((dollars / max(styles, 1e-9)) / max(chain_sps, 1e-9)),
                "online_share": online_d / max(dollars, 1e-9),
                "median_store_sell_through": float(grp["median_store_sell_through"].median()),
                "avg_depth_per_choice": float(grp["avg_depth_per_choice"].mean()),
                "yoy_sales_growth": (y2 - y1) / y1 if y1 > 0 else np.nan,
            }
        )
        w = grp["total_sales_units"].fillna(0.0).clip(lower=0.0)
        w_sum = float(w.sum())
        for af in age_fields:
            valid = grp[af].notna()
            if valid.any() and float(w[valid].sum()) > 0:
                rec[af] = float(np.average(grp.loc[valid, af], weights=w.loc[valid]))
            elif valid.any() and w_sum == 0:
                rec[af] = float(grp.loc[valid, af].mean())
            else:
                rec[af] = np.nan
        rec["ntf_youth_lift"] = rec["ntf_under_51"] - rec["existing_under_51"]
        rows.append(rec)

    return pd.DataFrame(rows)
