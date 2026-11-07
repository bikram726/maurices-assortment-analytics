"""Caveat-safe local analytics engine for the maurices Assortment Case Competition.

Runs 100% offline on local CSVs (zero network/AI calls). Enforces every data
dictionary rule:
1. Joins customer & product files on composite (dept, class, subclass) after
   normalizing text ("004") vs integer (4) IDs.
2. Keys all subclass metrics on composite IDs so shared descriptions (e.g., two
   "FASHION CARDI" subclasses) never collide.
3. Strips "%" from all 48 age-band columns, guards blank/zero-buyer rows, and
   weights age rollups by positive unit volume (never unweighted averages).
4. Treats soh_units as a weekly STORE-only snapshot (mean across active store
   weeks, never summed; ignores ~14% null store stock rows cleanly).
5. Computes sell-through & depth-per-choice on STORE rows only, handling >100%
   mid-week restock weeks via median + fast-turn share.
6. Expresses "profitability" via Assortment Productivity (Sales per Style-Week
   Index = 100, Store Sell-Through, Depth per Choice) and masks raw dollars
   into % Share & Index.
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
        return vals / 100.0 if vals.max() > 1.5 else vals
    has_pct = s.astype(str).str.contains("%", na=False).any()
    cleaned = (
        s.astype(str)
        .str.strip()
        .str.replace("%", "", regex=False)
        .replace({"": "0", "nan": "0", "None": "0", "NULL": "0", "null": "0"})
    )
    vals = pd.to_numeric(cleaned, errors="coerce").fillna(0.0)
    if has_pct or vals.max() > 1.5:
        return vals / 100.0
    return vals


def _wavg(values: pd.Series, weights: pd.Series) -> float:
    """Volume-weighted average ignoring NaNs and zero/negative return-week weights."""
    w = pd.to_numeric(weights, errors="coerce").fillna(0.0).clip(lower=0.0)
    valid = values.notna() & (w > 0)
    if valid.any():
        return float(np.average(values.loc[valid], weights=w.loc[valid]))
    if values.notna().any():
        return float(values.dropna().mean())
    return float("nan")


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
        "dept_id": _pick_col(cols, ["dept_idnt", "dept_id", "department_id", "dept", "dept_num", "dept_nbr"], r"^dept.*(idnt|id|num|nbr|code)$|^dept$"),
        "dept_desc": _pick_col(cols, ["dept_desc", "department_desc", "department_description", "dept_name", "department"], r"dept.*(desc|name)"),
        "class_id": _pick_col(cols, ["class_idnt", "class_id", "class", "class_num", "class_nbr", "cls_id"], r"^class.*(idnt|id|num|nbr|code)$|^class$"),
        "class_desc": _pick_col(cols, ["class_desc", "class_description", "class_name"], r"class.*(desc|name)"),
        "subclass_id": _pick_col(cols, ["sbclass_idnt", "subclass_idnt", "subclass_id", "subclass", "sub_class_id", "sbc_id"], r"s(?:u)?b.?class.*(idnt|id|num|nbr|code)$|^s(?:u)?bclass$"),
        "subclass_desc": _pick_col(cols, ["sbclass_desc", "subclass_desc", "subclass_description", "subclass_name", "sub_class_desc"], r"s(?:u)?b.?class.*(desc|name)"),
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
        "week_seq": _pick_col(cols, ["week_seq", "seq_week"], r"week_seq"),
        "fiscal_year": _pick_col(cols, ["fiscal_year_label", "fiscal_year_id", "fiscal_year", "fy", "year"], r"fiscal_year|year"),
        "fiscal_quarter": _pick_col(cols, ["fiscal_quarter_label", "fiscal_quarter", "quarter", "fiscal_qtr", "qtr", "fiscal_quarter_id"], r"fiscal_quarter_label|quarter|qtr"),
        "fiscal_month": _pick_col(cols, ["fiscal_month_label", "fiscal_month", "month", "fiscal_mo"], r"fiscal_month_label|month"),
        "week_start": _pick_col(cols, ["week_start_date", "start_date", "week_start", "week_end_date"], r"week_start_date|date"),
    }


def classify_age_columns(df: pd.DataFrame) -> dict[str, dict[str, list[str]]]:
    """Classify the 48 customer age columns into TOTAL / NTF / EXISTING and strategic age cohorts."""
    groups: dict[str, dict[str, list[str]]] = {
        seg: {"all": [], "under_51": [], "under_40": [], "liv_35_44": [], "young_18_34": [], "protect_45_plus": []}
        for seg in ("TOTAL", "NTF", "EXISTING")
    }
    id_like = {"dept", "dept_id", "dept_idnt", "department", "department_id", "class", "class_id", "class_idnt", "subclass", "subclass_id", "sbclass_idnt"}

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


def _normalize_quarter_label(s: pd.Series, seq_week: pd.Series) -> pd.Series:
    """Extract canonical Q1..Q4 labels regardless of 'Q1', 'FY26 Q1', or '20261' formatting."""
    extracted = s.astype(str).str.upper().str.extract(r"Q\s*([1-4])", expand=False)
    missing = extracted.isna()
    if missing.any():
        tail_digit = s.astype(str).str.strip().str.extract(r"([1-4])$", expand=False)
        extracted = extracted.fillna(tail_digit)
    fallback = (((seq_week - 1) % 52) // 13 + 1).astype(str)
    return "Q" + extracted.fillna(fallback)


def load_and_analyze(
    product_csv: Path | str,
    time_csv: Path | str,
    customer_csv: Path | str,
    denim_regex: str = r"\b(?:denim|dnm|jean|jeans|jns|jegging|jeggings|jeg)\b",
) -> dict[str, Any]:
    """Load the 3 maurices CSVs locally and build caveat-safe analytical tables."""
    prod = pd.read_csv(product_csv, low_memory=False)
    time_df = pd.read_csv(time_csv, low_memory=False)
    cust = pd.read_csv(customer_csv, low_memory=False)

    pcols = detect_product_columns(prod)
    tcols = detect_time_columns(time_df)
    c_dept = _pick_col(list(cust.columns), ["dept", "dept_id", "dept_idnt", "department_id", "department"], r"dept")
    c_cls = _pick_col(list(cust.columns), ["class", "class_id", "class_idnt", "cls_id"], r"^class")
    c_sub = _pick_col(list(cust.columns), ["subclass", "subclass_id", "sbclass_idnt", "sub_class_id", "sub_class"], r"s(?:u)?b.?class")

    required_p = ["dept_id", "class_id", "subclass_id", "week", "channel", "sales_dollars", "sales_units", "style_count"]
    missing = [k for k in required_p if not pcols.get(k)]
    if missing or not (c_dept and c_cls and c_sub) or not tcols.get("week"):
        raise ValueError(f"Column auto-detection incomplete. Missing product={missing}, cust={(c_dept, c_cls, c_sub)}, time={tcols}")

    # 1. Canonical composite keys (fixes text '004' vs integer 4 mismatch + duplicate subclass descriptions)
    prod["dept_key"] = normalize_id_series(prod[pcols["dept_id"]])
    prod["class_key"] = normalize_id_series(prod[pcols["class_id"]])
    prod["subclass_key"] = normalize_id_series(prod[pcols["subclass_id"]])
    prod["class_comp_key"] = prod["dept_key"] + "|" + prod["class_key"]
    prod["comp_key"] = prod["dept_key"] + "|" + prod["class_key"] + "|" + prod["subclass_key"]

    prod["dept_label"] = prod[pcols["dept_desc"]].astype(str).str.strip() if pcols["dept_desc"] else ("Dept " + prod["dept_key"])
    raw_cls_desc = prod[pcols["class_desc"]].astype(str).str.strip() if pcols["class_desc"] else ("Class " + prod["class_key"])
    prod["class_desc_raw"] = raw_cls_desc
    cls_key_counts = prod.groupby("class_desc_raw")["class_comp_key"].nunique()
    dup_cls_descs = set(cls_key_counts[cls_key_counts > 1].index)
    prod["class_label"] = np.where(
        prod["class_desc_raw"].isin(dup_cls_descs),
        prod["class_desc_raw"] + " [" + prod["dept_label"].str.slice(0, 12) + "]",
        prod["class_desc_raw"],
    )

    raw_sub_desc = prod[pcols["subclass_desc"]].astype(str).str.strip() if pcols["subclass_desc"] else ("Subclass " + prod["subclass_key"])
    prod["subclass_desc_raw"] = raw_sub_desc
    desc_key_counts = prod.groupby("subclass_desc_raw")["comp_key"].nunique()
    dup_descs = set(desc_key_counts[desc_key_counts > 1].index)
    prod["subclass_label"] = np.where(
        prod["subclass_desc_raw"].isin(dup_descs),
        prod["subclass_desc_raw"] + " [" + prod["dept_key"] + "-" + prod["subclass_key"] + "]",
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

    valid_st = prod["weekly_sell_through"].dropna()
    if len(valid_st) and valid_st.median() > 2.5:
        prod["weekly_sell_through"] = prod["weekly_sell_through"] / 100.0

    prod["channel_norm"] = prod[pcols["channel"]].astype(str).str.upper().str.strip()
    prod["week_key"] = normalize_id_series(prod[pcols["week"]])

    # 2. Join Time File on fiscal_week_id = the_week (exact 52w Year_1 vs 52w Year_2)
    time_clean = time_df.copy()
    time_clean["week_key"] = normalize_id_series(time_clean[tcols["week"]])
    time_clean = time_clean.drop_duplicates(subset=["week_key"])
    if tcols.get("week_seq") and tcols["week_seq"] in time_clean.columns:
        time_clean["seq_week"] = pd.to_numeric(time_clean[tcols["week_seq"]], errors="coerce")
        time_clean = time_clean.sort_values("seq_week").reset_index(drop=True)
        if time_clean["seq_week"].isna().any():
            time_clean["seq_week"] = np.arange(1, len(time_clean) + 1)
        else:
            time_clean["seq_week"] = time_clean["seq_week"].astype(int)
    else:
        time_clean["week_num_sort"] = pd.to_numeric(time_clean["week_key"], errors="coerce")
        time_clean = time_clean.sort_values("week_num_sort" if time_clean["week_num_sort"].notna().all() else "week_key").reset_index(drop=True)
        time_clean["seq_week"] = np.arange(1, len(time_clean) + 1)

    total_chain_weeks = max(1, len(time_clean))
    half_point = max(1, total_chain_weeks // 2)
    time_clean["period_half"] = np.where(time_clean["seq_week"] <= half_point, "Year_1", "Year_2")

    if tcols["fiscal_quarter"]:
        time_clean["qtr_label"] = _normalize_quarter_label(time_clean[tcols["fiscal_quarter"]], time_clean["seq_week"])
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
        seg_all = age_map[seg]["all"]
        seg_sum = cust_clean[seg_all].sum(axis=1) if seg_all else pd.Series(0.0, index=cust_clean.index)
        has_buyers = seg_sum >= 0.05
        for bucket in ("under_51", "under_40", "liv_35_44", "young_18_34", "protect_45_plus"):
            bcols = age_map[seg][bucket]
            if bcols:
                raw_b = cust_clean[bcols].sum(axis=1)
                cust_clean[f"{seg.lower()}_{bucket}"] = np.where(has_buyers, raw_b / seg_sum.clip(lower=1e-9), np.nan)
            else:
                cust_clean[f"{seg.lower()}_{bucket}"] = np.nan

    # Empirical-Bayes shrinkage for sparse NTF rows (e.g. <=8 populated bands from 2-6 shoppers yielding 33.33%/50.00%)
    ntf_all = age_map["NTF"]["all"]
    if ntf_all:
        ntf_rel = ((cust_clean[ntf_all] > 1e-6).sum(axis=1) / 9.0).clip(0.0, 1.0)
        for bucket in ("under_51", "under_40", "liv_35_44", "young_18_34", "protect_45_plus"):
            ntf_col, tot_col = f"ntf_{bucket}", f"total_{bucket}"
            both_ok = cust_clean[ntf_col].notna() & cust_clean[tot_col].notna()
            cust_clean.loc[both_ok, ntf_col] = (
                ntf_rel.loc[both_ok] * cust_clean.loc[both_ok, ntf_col]
                + (1.0 - ntf_rel.loc[both_ok]) * cust_clean.loc[both_ok, tot_col]
            )

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

    # Style breadth: weekly max across channels (master styles offered that week)
    # Using total_style_weeks makes seasonal and 52-week categories comparable on actual floor/site slot usage
    wk_styles = (
        prod.groupby(["comp_key", "week_key"], as_index=False)
        .agg(weekly_styles=("style_count", "max"), soh_ref=("soh_units_total", "first"))
    )
    wk_styles["weekly_styles"] = wk_styles["weekly_styles"].fillna(0.0).clip(lower=0.0)
    style_agg = wk_styles.groupby("comp_key", as_index=False).agg(
        avg_style_count=("weekly_styles", "mean"),
        total_style_weeks=("weekly_styles", "sum"),
        avg_soh_ref=("soh_ref", "mean"),
    )
    style_agg["effective_weekly_styles"] = style_agg["total_style_weeks"] / float(total_chain_weeks)

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

    # YoY Momentum (Year 2 vs Year 1 — matched 52-week halves)
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
    sub["total_style_weeks"] = sub["total_style_weeks"].fillna(0.0)

    # Relative shares & masked-safe Productivity Indices (Chain = 100)
    pos_dollars = sub["total_sales_dollars"].clip(lower=0.0)
    pos_units = sub["total_sales_units"].clip(lower=0.0)
    chain_dollars = max(float(pos_dollars.sum()), 1e-9)
    chain_units = max(float(pos_units.sum()), 1e-9)
    chain_style_weeks = max(float(sub["total_style_weeks"].sum()), 1e-9)

    sub["sales_dollar_share"] = sub["total_sales_dollars"] / chain_dollars
    sub["sales_unit_share"] = sub["total_sales_units"] / chain_units
    sub["style_share"] = sub["total_style_weeks"] / chain_style_weeks
    sub["excess_style_share"] = sub["style_share"] - sub["sales_dollar_share"]
    sub["online_share"] = np.where(sub["total_sales_dollars"] > 0, (sub["online_sales_dollars"] / sub["total_sales_dollars"]).clip(0.0, 1.0), 0.0)

    sub["sales_per_style"] = np.where(sub["total_style_weeks"] > 0, sub["total_sales_dollars"] / sub["total_style_weeks"], np.nan)
    chain_sps = float(sub["total_sales_dollars"].sum() / chain_style_weeks)
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
    liv_blend = 0.50 * sub["ntf_liv_35_44"].fillna(sub["total_liv_35_44"]) + 0.50 * sub["total_liv_35_44"]
    sub["sc2_younger_ntf_pct"] = 100.0 * (
        0.35 * sub["ntf_under_51"].rank(pct=True)
        + 0.25 * sub["total_under_51"].rank(pct=True)
        + 0.25 * liv_blend.rank(pct=True)
        + 0.15 * sub["online_share"].rank(pct=True)
    )
    sub["ideal_assortment_score"] = 0.55 * sub["sc1_volume_profit_pct"] + 0.45 * sub["sc2_younger_ntf_pct"]

    # 4-Quadrant Merchandising Action Tier (computed against active non-micro baseline)
    active_mask = (sub["weeks_present"] >= min(8, max(1, total_chain_weeks // 10))) & (sub["total_sales_dollars"] > 0)
    ref_df = sub.loc[active_mask] if active_mask.any() else sub
    med_sps = float(ref_df["sales_per_style_idx"].median())
    med_youth = float(ref_df["ntf_under_51"].median()) if ref_df["ntf_under_51"].notna().any() else 0.50
    lean_styles_cut = float(ref_df["avg_style_count"].quantile(0.40))
    hero_vol_cut = float(ref_df["sales_dollar_share"].quantile(0.75))
    min_hero_share = float(ref_df["sales_dollar_share"].quantile(0.25)) if len(ref_df) > 25 else 0.0

    def _classify_row(r: pd.Series) -> str:
        if r["total_sales_dollars"] <= 0 or pd.isna(r["sales_per_style_idx"]):
            return "Rationalize Bloat (Cut Over-Assorted Tail)"
        hi_prod = bool(r["sales_per_style_idx"] >= max(med_sps, 95.0))
        youth_val = r["ntf_under_51"] if pd.notna(r["ntf_under_51"]) else r["total_under_51"]
        hi_youth = bool(pd.notna(youth_val) and youth_val >= med_youth)
        meaningful_scale = bool(r["sales_dollar_share"] >= min_hero_share and r["weeks_present"] >= min(8, total_chain_weeks))
        if hi_prod and hi_youth and meaningful_scale:
            if pd.notna(r["avg_style_count"]) and r["avg_style_count"] <= lean_styles_cut and r["sales_dollar_share"] < hero_vol_cut:
                return "Expand Depth & Styles (Under-Assorted Gem)"
            return "Invest & Scale (Hero + Liv Growth)"
        if hi_prod and meaningful_scale and not hi_youth:
            return "Protect Core (45+ Cash Cow)"
        if hi_youth:
            return "Curate & Refresh (Trim Styles, Keep Trend)"
        return "Rationalize Bloat (Cut Over-Assorted Tail)"

    sub["action_tier"] = sub.apply(_classify_row, axis=1)

    # 5. Volume-Weighted Rollups (Department, Class & Action Tier — NEVER unweighted age % mean!)
    dept_rollup = weighted_group_rollup(sub, ["dept_key", "dept_label"])
    class_rollup = weighted_group_rollup(sub, ["dept_key", "dept_label", "class_key", "class_label"])
    tier_rollup = weighted_group_rollup(sub, ["action_tier"])

    # 6. Weekly / Quarterly Time Series by Channel
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
        "tiers": tier_rollup.sort_values("sales_dollar_share", ascending=False).reset_index(drop=True),
        "weekly": ts_weekly,
        "diagnostics": {
            "product_rows": len(prod),
            "weeks_count": int(prod["week_key"].nunique()),
            "customer_subclasses": len(cust_clean),
            "total_product_subclasses": len(sub),
            "joined_subclasses": int(sub["ntf_under_51"].notna().sum()),
            "department_count": int(dept_rollup["dept_key"].nunique()),
            "class_count": len(class_rollup),
            "duplicate_descriptions_disambiguated": sorted(list(dup_descs)),
            "duplicate_count": len(dup_descs),
            "store_missing_soh_pct": round(100.0 * float(store_df["soh_units"].isna().mean()), 1) if len(store_df) else 0.0,
            "store_st_over_100_pct": round(100.0 * float((store_df["weekly_sell_through"].dropna() > 1.0).mean()), 1) if len(store_df) else 0.0,
            "store_median_st_pct": round(100.0 * float(store_df["weekly_sell_through"].dropna().median()), 1) if len(store_df) else 0.0,
            "negative_unit_rows": int((prod["sales_units"] < 0).sum()),
            "denim_subclass_count": int(sub["is_denim"].sum()),
            "denim_sales_share": float(sub.loc[sub["is_denim"], "sales_dollar_share"].sum()),
            "denim_style_share": float(sub.loc[sub["is_denim"], "style_share"].sum()),
            "chain_weighted_under_51": _wavg(sub["total_under_51"], sub["total_sales_units"]),
            "chain_weighted_under_40": _wavg(sub["total_under_40"], sub["total_sales_units"]),
            "chain_weighted_ntf_under_51": _wavg(sub["ntf_under_51"], sub["total_sales_units"]),
            "chain_weighted_ntf_under_40": _wavg(sub["ntf_under_40"], sub["total_sales_units"]),
            "chain_weighted_liv_35_44": _wavg(sub["ntf_liv_35_44"], sub["total_sales_units"]),
            "chain_weighted_protect_45_plus": _wavg(sub["existing_protect_45_plus"], sub["total_sales_units"]),
            "chain_online_share": float(sub["online_sales_dollars"].sum() / chain_dollars),
            "chain_yoy_growth": float((sub["Year_2"].sum() - sub["Year_1"].sum()) / max(float(sub["Year_1"].sum()), 1e-9)),
        },
    }


def weighted_group_rollup(sub: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Roll up subclass metrics to Class, Department, or Tier weighting age distributions by positive unit volume."""
    age_fields = [
        "total_under_51", "total_under_40", "total_liv_35_44", "total_protect_45_plus",
        "ntf_under_51", "ntf_under_40", "ntf_liv_35_44", "ntf_young_18_34", "ntf_protect_45_plus",
        "existing_under_51", "existing_protect_45_plus",
    ]
    rows: list[dict[str, Any]] = []
    chain_dollars = max(float(sub["total_sales_dollars"].clip(lower=0.0).sum()), 1e-9)
    chain_units = max(float(sub["total_sales_units"].clip(lower=0.0).sum()), 1e-9)
    chain_style_weeks = max(float(sub["total_style_weeks"].fillna(0).sum()), 1e-9)
    chain_sps = float(sub["total_sales_dollars"].sum()) / chain_style_weeks

    for keys, grp in sub.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        rec = {col: val for col, val in zip(group_cols, keys)}
        dollars = float(grp["total_sales_dollars"].sum())
        units = float(grp["total_sales_units"].sum())
        style_wks = float(grp["total_style_weeks"].fillna(0).sum())
        styles_avg = float(grp["avg_style_count"].fillna(0).sum())
        online_d = float(grp["online_sales_dollars"].sum())
        y1 = float(grp["Year_1"].sum())
        y2 = float(grp["Year_2"].sum())

        d_share = dollars / chain_dollars
        s_share = style_wks / chain_style_weeks
        rec.update(
            {
                "subclass_count": len(grp),
                "total_sales_dollars": dollars,
                "total_sales_units": units,
                "avg_style_count": styles_avg,
                "total_style_weeks": style_wks,
                "sales_dollar_share": d_share,
                "sales_unit_share": units / chain_units,
                "style_share": s_share,
                "assortment_gap_bps": (d_share - s_share) * 100.0,
                "sales_per_style_idx": 100.0 * ((dollars / max(style_wks, 1e-9)) / max(chain_sps, 1e-9)),
                "online_share": max(0.0, min(1.0, online_d / max(dollars, 1e-9))),
                "median_store_sell_through": float(grp["median_store_sell_through"].median()),
                "avg_depth_per_choice": float(grp["avg_depth_per_choice"].mean()),
                "yoy_sales_growth": (y2 - y1) / y1 if y1 > 0 else np.nan,
            }
        )
        for af in age_fields:
            rec[af] = _wavg(grp[af], grp["total_sales_units"])
        rec["ntf_youth_lift"] = rec["ntf_under_51"] - rec["existing_under_51"]
        rows.append(rec)

    return pd.DataFrame(rows)
