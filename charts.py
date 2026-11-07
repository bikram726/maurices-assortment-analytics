"""Publication-grade 16:9 slide visual generator for the maurices Case Competition.

Generates 7 widescreen (240-DPI) executive charts + CSV scorecards + Markdown slide
talking points tailored to maurices' CMO, Marketing Analytics, CRM, and Enterprise
Analytics judges. Never exposes raw masked dollar values (uses % Share & Index=100).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PALETTE = {
    "navy": "#13293D",
    "teal": "#0F766E",
    "teal_light": "#14B8A6",
    "plum": "#7E22CE",
    "berry": "#9D174D",
    "coral": "#EA580C",
    "amber": "#D97706",
    "slate": "#334155",
    "muted": "#64748B",
    "grid": "#E2E8F0",
    "bg": "#FFFFFF",
}

TIER_COLORS = {
    "Invest & Scale (Hero + Liv Growth)": "#0F766E",
    "Expand Depth & Styles (Under-Assorted Gem)": "#7E22CE",
    "Protect Core (45+ Cash Cow)": "#2563EB",
    "Curate & Refresh (Trim Styles, Keep Trend)": "#D97706",
    "Rationalize Bloat (Cut Over-Assorted Tail)": "#DC2626",
}


def _setup_slide_ax(
    title: str,
    subtitle: str,
    footnote: str,
    demo_mode: bool = False,
    left: float = 0.09,
    top: float = 0.81,
) -> tuple[plt.Figure, plt.Axes]:
    plt.rcParams.update(
        {
            "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
            "axes.edgecolor": "#CBD5E1",
            "axes.linewidth": 0.9,
            "text.parse_math": False,
        }
    )
    fig, ax = plt.subplots(figsize=(13.6, 7.6), dpi=240)
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor("#FAFBFD")
    ax.grid(True, color=PALETTE["grid"], linestyle="--", linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.subplots_adjust(top=top, bottom=0.14, left=left, right=0.95)
    fig.text(0.05, 0.935, title, fontsize=16.6, fontweight="bold", color="#0F172A")
    fig.text(0.05, 0.89, subtitle, fontsize=10.6, color=PALETTE["muted"])
    fig.text(0.05, 0.03, footnote, fontsize=8.6, color=PALETTE["muted"], style="italic")
    if demo_mode:
        fig.text(
            0.96, 0.94, "SYNTHETIC DEMO PREVIEW",
            fontsize=8.8, fontweight="bold", color="#B91C1C", ha="right",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#FEE2E2", edgecolor="#FCA5A5"),
        )
    return fig, ax


def _annotate_non_overlapping(
    ax: plt.Axes,
    xs: list[float],
    ys: list[float],
    labels: list[str],
    x_span: float,
    y_span: float,
    fontsize: float = 8.4,
) -> None:
    """Place scatter point labels with greedy vertical repulsion so text never collides."""
    if not xs:
        return
    placed: list[tuple[float, float]] = []
    min_dy = max(1e-6, y_span * 0.048)
    min_dx = max(1e-6, x_span * 0.19)

    order = np.argsort(ys)[::-1]
    for idx in order:
        px, py = float(xs[idx]), float(ys[idx])
        tx = px + x_span * 0.014
        ty = py + y_span * 0.012
        ha = "left"
        if px > (ax.get_xlim()[0] + 0.76 * x_span):
            tx = px - x_span * 0.015
            ha = "right"

        for _ in range(14):
            collision = False
            for ox, oy in placed:
                if abs(tx - ox) < min_dx and abs(ty - oy) < min_dy:
                    ty -= min_dy * 0.85
                    collision = True
                    break
            if not collision:
                break

        ty = max(ax.get_ylim()[0] + 0.03 * y_span, min(ax.get_ylim()[1] - 0.03 * y_span, ty))
        placed.append((tx, ty))
        ax.annotate(
            labels[idx],
            xy=(px, py),
            xytext=(tx, ty),
            ha=ha,
            va="center",
            fontsize=fontsize,
            fontweight="semibold",
            color="#0F172A",
            arrowprops=dict(arrowstyle="-", color="#94A3B8", lw=0.6, shrinkA=0, shrinkB=4),
            zorder=6,
        )


def plot_01_over_under_assorted(analysis: dict[str, Any], out_path: Path, demo_mode: bool = False) -> Path:
    """Slide 1: Class Over-Assorted vs Under-Invested Bubble Matrix."""
    df = analysis["classes"].dropna(subset=["sales_per_style_idx"]).copy()
    df = df[df["style_share"] > 0.001].copy()
    if len(df) > 18:
        df["_exc"] = df["style_share"] - df["sales_dollar_share"]
        df = pd.concat([
            df.nlargest(12, "sales_dollar_share"),
            df.nlargest(6, "_exc"),
        ]).drop_duplicates(subset=["dept_key", "class_key"])

    fig, ax = _setup_slide_ax(
        "Where maurices Is Over-Assorted vs. Under-Invested (Class Audit)",
        "Active Style-Week Share (%) vs. Assortment Productivity Index (Chain Avg = 100) • Color = NTF <51 Younger Buyer %",
        "Caveat note: Masked sales converted to % Share & Sales/Style-Week Index (100 = Chain Avg; proxy for profitability). Age shares unit-volume weighted.",
        demo_mode=demo_mode,
    )

    x = 100.0 * df["style_share"]
    y = df["sales_per_style_idx"].clip(lower=10.0, upper=320.0)
    sizes = (df["sales_dollar_share"].clip(lower=0.002) * 8500).clip(lower=130, upper=1550)
    youth = 100.0 * df["ntf_under_51"].fillna(df["total_under_51"]).fillna(0.5)

    x_pad = max(0.8, (float(x.max()) - float(x.min())) * 0.16)
    y_pad = max(12.0, (float(y.max()) - float(y.min())) * 0.18)
    ax.set_xlim(max(0.0, float(x.min()) - x_pad), float(x.max()) + x_pad * 1.35)
    ax.set_ylim(max(0.0, float(y.min()) - y_pad), float(y.max()) + y_pad * 1.25)

    sc = ax.scatter(
        x, y, s=sizes, c=youth, cmap="viridis", alpha=0.88,
        edgecolors="#0F172A", linewidth=1.1, zorder=4,
    )
    cbar = fig.colorbar(sc, ax=ax, pad=0.02, shrink=0.82)
    cbar.set_label("New-to-File (NTF) Buyers Under Age 51 (%)", fontsize=10, color=PALETTE["slate"])

    ax.axhline(100.0, color=PALETTE["slate"], linestyle="--", linewidth=1.2)
    ax.axvline(float(x.median()), color="#94A3B8", linestyle=":", linewidth=1.1)

    x_span = ax.get_xlim()[1] - ax.get_xlim()[0]
    y_span = ax.get_ylim()[1] - ax.get_ylim()[0]
    _annotate_non_overlapping(
        ax,
        x.tolist(),
        y.tolist(),
        [str(v)[:25] for v in df["class_label"]],
        x_span,
        y_span,
        fontsize=8.5,
    )

    ax.text(0.015, 0.97, "UNDER-ASSORTED WINNERS\nIndex > 100 • Expand Choice & Depth", transform=ax.transAxes,
            fontsize=9.2, fontweight="bold", color=PALETTE["teal"], va="top",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#F0FDFA", edgecolor="#99F6E4", alpha=0.92), zorder=7)
    ax.text(0.985, 0.04, "OVER-ASSORTED BLOAT\nIndex < 100 • Rationalize Style Tail", transform=ax.transAxes,
            fontsize=9.2, fontweight="bold", color="#B91C1C", ha="right", va="bottom",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#FEF2F2", edgecolor="#FECACA", alpha=0.92), zorder=7)

    ax.set_xlabel("Share of Active Style-Weeks Offered (% of Chain Assortment Footprint)", fontsize=11, fontweight="bold", color=PALETTE["slate"])
    ax.set_ylabel("Sales per Style Productivity Index (100 = Chain Avg)", fontsize=11, fontweight="bold", color=PALETTE["slate"])

    fig.savefig(out_path, dpi=240)
    plt.close(fig)
    return out_path


def plot_02_dual_mandate_quadrant(analysis: dict[str, Any], out_path: Path, demo_mode: bool = False) -> Path:
    """Slide 2: Success Criteria #1 (Volume & Sales/Style) vs #2 (Younger <51 Acquisition)."""
    sub = analysis["subclasses"].copy()
    valid = sub[sub["ntf_under_51"].notna() & (sub["total_sales_dollars"] > 0)].copy()
    if len(valid) > 36:
        plot_df = pd.concat([
            valid.nlargest(24, "total_sales_dollars"),
            valid.nlargest(12, "excess_style_share"),
        ]).drop_duplicates(subset=["comp_key"])
    else:
        plot_df = valid

    fig, ax = _setup_slide_ax(
        "Dual-Mandate Subclass Matrix: Driving Volume Productivity + Younger (<51) Growth",
        "X = Success Criterion #1 (Sales Share, Unit Volume & Sales/Style Rank) • Y = NTF Buyers Under Age 51 (%) • Bubble = Sales Share",
        "Composite IDs (dept+class+subclass) preserve distinct subclasses with shared names (e.g., FASHION CARDI). Bubble size = % of Chain Net Sales.",
        demo_mode=demo_mode,
        top=0.77,
    )

    ax.set_xlim(0, 106)
    y_vals = 100.0 * plot_df["ntf_under_51"]
    ax.set_ylim(max(0.0, float(y_vals.min()) - 8.0), min(104.0, float(y_vals.max()) + 9.0))

    med_y = 100.0 * float(valid["ntf_under_51"].median())
    ax.axvline(50.0, color="#64748B", linestyle="--", linewidth=1.1)
    ax.axhline(med_y, color="#64748B", linestyle="--", linewidth=1.1)

    for tier, color in TIER_COLORS.items():
        grp = plot_df[plot_df["action_tier"] == tier]
        if grp.empty:
            continue
        ax.scatter(
            grp["sc1_volume_profit_pct"],
            100.0 * grp["ntf_under_51"],
            s=(grp["sales_dollar_share"].clip(lower=0.001) * 9500).clip(lower=110, upper=1350),
            color=color,
            alpha=0.86,
            edgecolors="#0F172A",
            linewidth=0.9,
            label=tier,
            zorder=4,
        )

    label_rows = pd.concat([
        plot_df.nlargest(6, "ideal_assortment_score"),
        plot_df.nlargest(4, "excess_style_share"),
    ]).drop_duplicates(subset=["comp_key"])

    x_span = ax.get_xlim()[1] - ax.get_xlim()[0]
    y_span = ax.get_ylim()[1] - ax.get_ylim()[0]
    _annotate_non_overlapping(
        ax,
        label_rows["sc1_volume_profit_pct"].tolist(),
        (100.0 * label_rows["ntf_under_51"]).tolist(),
        [str(v)[:25] for v in label_rows["subclass_label"]],
        x_span,
        y_span,
        fontsize=8.2,
    )

    ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, 1.11), ncol=3,
        markerscale=0.42, frameon=True, facecolor="#FFFFFF", edgecolor="#CBD5E1", fontsize=8.4,
    )
    ax.set_xlabel("Success Criterion #1 Percentile: Sales Share, Unit Volume & Sales/Style Productivity (0–100)", fontsize=11, fontweight="bold", color=PALETTE["slate"])
    ax.set_ylabel("Success Criterion #2: New-to-File Customers Under Age 51 (%)", fontsize=11, fontweight="bold", color=PALETTE["slate"])

    fig.savefig(out_path, dpi=240)
    plt.close(fig)
    return out_path


def plot_03_liv_vs_protect_age_mix(analysis: dict[str, Any], out_path: Path, demo_mode: bool = False) -> Path:
    """Slide 3: Customer Age Architecture by Department — NTF vs Existing ('Liv' 35-44 vs 'Protect' 45+)."""
    dept = analysis["departments"].dropna(subset=["ntf_under_51"]).head(10).copy()
    dept = dept.sort_values("ntf_under_51", ascending=True)

    fig, ax = _setup_slide_ax(
        "Winning 'Liv' (35–44) Without Losing 'Protect' (45+): Age Mix by Department",
        "Unit-Volume-Weighted New-to-File (NTF) Customer Age Distribution vs. Existing Customer Under-51 Baseline",
        "Age distributions stripped of '%' and weighted by subclass net_sales_units (never unweighted averages). Target: pull file younger than current avg age 51.",
        demo_mode=demo_mode,
        left=0.20,
        top=0.79,
    )

    y_pos = np.arange(len(dept))
    c_young = 100.0 * dept["ntf_young_18_34"].fillna(0)
    c_liv = 100.0 * dept["ntf_liv_35_44"].fillna(0)
    c_45_50 = (100.0 * (dept["ntf_under_51"] - dept["ntf_young_18_34"] - dept["ntf_liv_35_44"])).clip(lower=0)
    c_51p = (100.0 - (c_young + c_liv + c_45_50)).clip(lower=0)

    ax.barh(y_pos, c_young, color="#14B8A6", height=0.56, label="18–34 (Entry / Event & Social)")
    ax.barh(y_pos, c_liv, left=c_young, color="#7E22CE", height=0.56, label="35–44 'Liv' (Primary Grow Target)")
    ax.barh(y_pos, c_45_50, left=c_young + c_liv, color="#60A5FA", height=0.56, label="45–49 (Bridge Core)")
    ax.barh(y_pos, c_51p, left=c_young + c_liv + c_45_50, color="#94A3B8", height=0.56, label="50+ ('Protect' Loyalists)")

    ex_u51 = 100.0 * dept["existing_under_51"].fillna(0)
    ax.scatter(ex_u51, y_pos, color="#EA580C", marker="D", s=65, zorder=6, label="Existing Buyers <51% (Baseline)")

    for idx, (_, r) in enumerate(dept.iterrows()):
        u51_val = 100.0 * float(r["ntf_under_51"])
        lift = 100.0 * float(r["ntf_youth_lift"])
        sign = "+" if lift >= 0 else ""
        ax.text(
            101.2, idx,
            f"{u51_val:.0f}% NTF <51 ({sign}{lift:.1f} pts)",
            va="center", fontsize=8.5, fontweight="bold", color="#0F172A",
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(dept["dept_label"].str.slice(0, 26), fontsize=9.6, fontweight="bold", color="#1E293B")
    ax.set_xlim(0, 127)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("Share of New-to-File (NTF) Customers (%)", fontsize=11, fontweight="bold", color=PALETTE["slate"])
    ax.legend(loc="upper center", bbox_to_anchor=(0.46, 1.09), ncol=3, frameon=False, fontsize=8.5)

    fig.savefig(out_path, dpi=240)
    plt.close(fig)
    return out_path


def plot_04_denim_bet_scorecard(analysis: dict[str, Any], out_path: Path, demo_mode: bool = False) -> Path:
    """Slide 4: Testing the Denim Bet — Subclass Productivity, Liv/NTF Pull & Omnichannel Index."""
    plt.rcParams["text.parse_math"] = False
    sub = analysis["subclasses"]
    denim_all = sub[sub["is_denim"] & sub["ntf_under_51"].notna() & (sub["total_sales_dollars"] > 0)].copy()
    if denim_all.empty:
        denim = sub[sub["ntf_under_51"].notna()].nlargest(10, "ideal_assortment_score").sort_values("sales_per_style_idx", ascending=True)
        title_prefix = "Signature Hero Subclasses"
    else:
        if len(denim_all) > 10:
            med_sh = float(denim_all["sales_dollar_share"].median())
            top_d = denim_all[denim_all["sales_dollar_share"] >= med_sh].nlargest(6, "ideal_assortment_score")
            bot_d = denim_all.nlargest(4, "excess_style_share")
            denim = pd.concat([top_d, bot_d]).drop_duplicates(subset=["comp_key"]).sort_values("sales_per_style_idx", ascending=True)
        else:
            denim = denim_all.sort_values("sales_per_style_idx", ascending=True)
        title_prefix = "Testing the Denim Bet"

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 7.6), dpi=240, sharey=True)
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.subplots_adjust(top=0.81, bottom=0.14, left=0.23, right=0.96, wspace=0.14)

    fig.text(0.05, 0.935, f"{title_prefix}: Which Fits Win Volume, Productivity & Younger 'Liv' Shoppers",
             fontsize=16.4, fontweight="bold", color="#0F172A")
    fig.text(0.05, 0.89, "Left: Sales/Style Productivity Index (100 = Chain Avg) • Right: Younger NTF (<51 %) & Online Omnichannel Share (%)",
             fontsize=10.6, color=PALETTE["muted"])
    fig.text(0.05, 0.03,
             "Marketing & Fit Hook: 1 in 3 women changed sizes this year (nearly 4 in 10 on/considering GLP-1s) — pair modern stretch/wide-leg fits (sizes 0–24) with Free In-Store Styling.",
             fontsize=8.6, color=PALETTE["muted"], style="italic")
    if demo_mode:
        fig.text(0.96, 0.94, "SYNTHETIC DEMO PREVIEW", fontsize=8.8, fontweight="bold", color="#B91C1C", ha="right",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#FEE2E2", edgecolor="#FCA5A5"))

    y = np.arange(len(denim))
    sps_disp = denim["sales_per_style_idx"].clip(upper=320.0)
    bar_colors = [TIER_COLORS.get(t, PALETTE["teal"]) for t in denim["action_tier"]]

    ax1.set_facecolor("#FAFBFD")
    ax1.grid(True, axis="x", color=PALETTE["grid"], linestyle="--")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.barh(y, sps_disp, color=bar_colors, height=0.58)
    ax1.axvline(100.0, color="#0F172A", linestyle="--", linewidth=1.1)
    ax1.set_xlim(0, max(140.0, float(sps_disp.max()) * 1.18))
    for idx, val in enumerate(sps_disp):
        ax1.text(val + 3, idx, f"{val:.0f}", va="center", fontsize=8.8, fontweight="bold", color="#1E293B")
    ax1.set_yticks(y)
    ax1.set_yticklabels(denim["subclass_label"].str.slice(0, 29), fontsize=9.3, fontweight="bold", color="#0F172A")
    ax1.set_xlabel("Sales per Style Productivity Index", fontsize=10.5, fontweight="bold", color=PALETTE["slate"])

    ax2.set_facecolor("#FAFBFD")
    ax2.grid(True, axis="x", color=PALETTE["grid"], linestyle="--")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    u51_vals = 100.0 * denim["ntf_under_51"].fillna(0)
    om_vals = 100.0 * denim["online_share"].fillna(0)
    ax2.barh(y + 0.16, u51_vals, height=0.30, color=PALETTE["plum"], label="NTF Buyers <51 (%)")
    ax2.barh(y - 0.16, om_vals, height=0.30, color=PALETTE["teal_light"], label="Online Sales Share (% • Liv=25% Omni)")
    ax2.axvline(16.0, color=PALETTE["teal"], linestyle=":", linewidth=1.1, label="Chain Omni Benchmark (16%)")
    ax2.set_xlim(0, 109)
    for idx, (uv, ov) in enumerate(zip(u51_vals, om_vals)):
        ax2.text(uv + 1.2, idx + 0.16, f"{uv:.0f}%", va="center", fontsize=8.1, fontweight="bold", color=PALETTE["plum"])
        ax2.text(ov + 1.2, idx - 0.16, f"{ov:.0f}%", va="center", fontsize=8.1, fontweight="bold", color=PALETTE["teal"])
    ax2.set_xlabel("Customer Youth Mix & Online Channel Share (%)", fontsize=10.5, fontweight="bold", color=PALETTE["slate"])
    ax2.legend(loc="upper center", bbox_to_anchor=(0.48, 1.09), ncol=2, frameon=False, fontsize=8.2)

    fig.savefig(out_path, dpi=240)
    plt.close(fig)
    return out_path


def plot_05_store_inventory_velocity(analysis: dict[str, Any], out_path: Path, demo_mode: bool = False) -> Path:
    """Slide 5: STORE-Only Sell-Through vs Depth per Choice (Replenishment & Stockout Diagnostic)."""
    sub = analysis["subclasses"].dropna(subset=["median_store_sell_through", "avg_depth_per_choice"]).copy()
    sub = sub[sub["store_sales_dollars"] > 0].copy()
    plot_df = sub.nlargest(28, "store_sales_dollars") if len(sub) > 28 else sub

    fig, ax = _setup_slide_ax(
        "Store Inventory Execution: Median Weekly Sell-Through vs. Depth per Choice",
        "STORE Channel Only (Online excluded per schema) • Color = % of Weeks >100% Sell-Through (Mid-Week Restock Signal)",
        "Caveat note: soh_units averaged across active STORE weeks (never summed; ~14% seasonal null SOH excluded). >100% sell-through reflects mid-week restocking.",
        demo_mode=demo_mode,
    )

    x_cap = float(plot_df["avg_depth_per_choice"].quantile(0.96)) * 1.15 if len(plot_df) > 10 else float(plot_df["avg_depth_per_choice"].max())
    y_cap = float((100.0 * plot_df["median_store_sell_through"]).quantile(0.96)) * 1.15 if len(plot_df) > 10 else float(100.0 * plot_df["median_store_sell_through"].max())
    x = plot_df["avg_depth_per_choice"].clip(upper=max(x_cap, 3.0))
    y = (100.0 * plot_df["median_store_sell_through"]).clip(upper=max(y_cap, 8.0))
    restock = 100.0 * plot_df["pct_weeks_st_over_100"].fillna(0)
    sizes = (plot_df["sales_unit_share"].clip(lower=0.001) * 9000).clip(lower=120, upper=1450)

    x_pad = max(0.8, (float(x.max()) - float(x.min())) * 0.16)
    y_pad = max(1.5, (float(y.max()) - float(y.min())) * 0.16)
    ax.set_xlim(max(0.0, float(x.min()) - x_pad), float(x.max()) + x_pad * 1.35)
    ax.set_ylim(max(0.0, float(y.min()) - y_pad), float(y.max()) + y_pad * 1.25)

    sc = ax.scatter(x, y, s=sizes, c=restock, cmap="plasma", alpha=0.86, edgecolors="#0F172A", linewidth=1.0, zorder=4)
    cbar = fig.colorbar(sc, ax=ax, pad=0.02, shrink=0.82)
    cbar.set_label("% of Store Weeks with >100% Sell-Through (Fast Restock)", fontsize=9.8, color=PALETTE["slate"])

    ax.axvline(float(x.median()), color="#64748B", linestyle="--", linewidth=1.0)
    ax.axhline(float(y.median()), color="#64748B", linestyle="--", linewidth=1.0)

    plot_df = plot_df.assign(_x=x, _y=y)
    top_st = plot_df.nlargest(9, "_y")
    x_span = ax.get_xlim()[1] - ax.get_xlim()[0]
    y_span = ax.get_ylim()[1] - ax.get_ylim()[0]
    _annotate_non_overlapping(
        ax,
        top_st["_x"].tolist(),
        top_st["_y"].tolist(),
        [str(v)[:24] for v in top_st["subclass_label"]],
        x_span,
        y_span,
        fontsize=8.2,
    )

    ax.set_xlabel("Average Store Depth per Style-Color Choice (SOH Units / Style-Color)", fontsize=11, fontweight="bold", color=PALETTE["slate"])
    ax.set_ylabel("Median Weekly Store Sell-Through (%)", fontsize=11, fontweight="bold", color=PALETTE["slate"])

    fig.savefig(out_path, dpi=240)
    plt.close(fig)
    return out_path


def plot_06_seasonality_and_yoy(analysis: dict[str, Any], out_path: Path, demo_mode: bool = False) -> Path:
    """Slide 6: 4-5-4 Fiscal Quarter Demand & YoY Growth by Strategic Assortment Tier."""
    plt.rcParams["text.parse_math"] = False
    wk = analysis["weekly"].copy()
    sub = analysis["subclasses"].copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 7.6), dpi=240)
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.subplots_adjust(top=0.81, bottom=0.15, left=0.07, right=0.96, wspace=0.36)

    fig.text(0.05, 0.935, "4-5-4 Fiscal Seasonality & Year-over-Year Momentum by Assortment Tier",
             fontsize=16.5, fontweight="bold", color="#0F172A")
    fig.text(0.05, 0.89, "Left: Share of Sales by Fiscal Quarter (Aug–Jul Calendar) & Channel • Right: YoY Sales Growth (%) by Strategic Action Tier",
             fontsize=10.6, color=PALETTE["muted"])
    fig.text(0.05, 0.03,
             "4-5-4 Calendar: Q1 (Aug–Oct Back-to-Fall), Q2 (Nov–Jan Holiday Peak), Q3 (Feb–Apr Spring), Q4 (May–Jul Summer). Younger 20–39 buyers spike around Q2/event drops.",
             fontsize=8.6, color=PALETTE["muted"], style="italic")
    if demo_mode:
        fig.text(0.96, 0.94, "SYNTHETIC DEMO PREVIEW", fontsize=8.8, fontweight="bold", color="#B91C1C", ha="right",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#FEE2E2", edgecolor="#FCA5A5"))

    q_piv = wk.pivot_table(index="qtr_label", columns="channel_norm", values="sales_share_pct", aggfunc="sum").fillna(0)
    q_order = [q for q in ("Q1", "Q2", "Q3", "Q4") if q in q_piv.index] or list(q_piv.index)
    q_piv = q_piv.loc[q_order]

    ax1.set_facecolor("#FAFBFD")
    ax1.grid(True, axis="y", color=PALETTE["grid"], linestyle="--")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    bottom = np.zeros(len(q_piv))
    ch_colors = [PALETTE["teal"], PALETTE["plum"], PALETTE["amber"]]
    for idx_c, ch in enumerate(q_piv.columns):
        vals = q_piv[ch].values
        ax1.bar(q_piv.index, vals, bottom=bottom, color=ch_colors[idx_c % len(ch_colors)], width=0.52, label=ch)
        bottom += vals
    for idx_q, tot_v in enumerate(bottom):
        ax1.text(idx_q, tot_v + 0.6, f"{tot_v:.1f}%", ha="center", fontsize=9.0, fontweight="bold", color="#0F172A")
    ax1.set_ylim(0, max(35.0, float(bottom.max()) * 1.15))
    ax1.set_ylabel("Share of 2-Year Chain Sales (%)", fontsize=10.5, fontweight="bold", color=PALETTE["slate"])
    ax1.set_xlabel("maurices 4-5-4 Fiscal Quarter (FY Starts Aug)", fontsize=10.5, fontweight="bold", color=PALETTE["slate"])
    ax1.legend(frameon=True, facecolor="#FFFFFF", fontsize=9)

    tier_yoy = (
        sub.groupby("action_tier", as_index=False)
        .agg(y1=("Year_1", "sum"), y2=("Year_2", "sum"))
    )
    tier_yoy["yoy_pct"] = np.where(tier_yoy["y1"] > 0, 100.0 * (tier_yoy["y2"] - tier_yoy["y1"]) / tier_yoy["y1"], 0.0)
    tier_yoy = tier_yoy.sort_values("yoy_pct", ascending=True)

    ax2.set_facecolor("#FAFBFD")
    ax2.grid(True, axis="x", color=PALETTE["grid"], linestyle="--")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    cols2 = [TIER_COLORS.get(t, PALETTE["slate"]) for t in tier_yoy["action_tier"]]
    short_labels = [t.split("(")[0].strip() for t in tier_yoy["action_tier"]]
    ax2.barh(short_labels, tier_yoy["yoy_pct"], color=cols2, height=0.55)
    ax2.axvline(0.0, color="#0F172A", linewidth=1.0)

    min_v = float(tier_yoy["yoy_pct"].min())
    max_v = float(tier_yoy["yoy_pct"].max())
    span_v = max(15.0, max_v - min_v)
    ax2.set_xlim(min(0.0, min_v) - 0.25 * span_v, max(0.0, max_v) + 0.24 * span_v)

    for idx_t, val in enumerate(tier_yoy["yoy_pct"]):
        offset = 0.03 * span_v if val >= 0 else -0.03 * span_v
        ha = "left" if val >= 0 else "right"
        ax2.text(val + offset, idx_t, f"{val:+.1f}%", va="center", ha=ha, fontsize=9.2, fontweight="bold", color="#0F172A")
    ax2.set_xlabel("Year-over-Year Net Sales Growth (%)", fontsize=10.5, fontweight="bold", color=PALETTE["slate"])

    fig.savefig(out_path, dpi=240)
    plt.close(fig)
    return out_path


def plot_07_otb_reallocation_blueprint(analysis: dict[str, Any], out_path: Path, demo_mode: bool = False) -> Path:
    """Slide 7: OTB Assortment Reallocation Blueprint — Style Share vs Sales Share by Tier."""
    tiers = analysis["tiers"].copy()
    order_list = [
        "Rationalize Bloat (Cut Over-Assorted Tail)",
        "Curate & Refresh (Trim Styles, Keep Trend)",
        "Protect Core (45+ Cash Cow)",
        "Expand Depth & Styles (Under-Assorted Gem)",
        "Invest & Scale (Hero + Liv Growth)",
    ]
    tiers["_ord"] = tiers["action_tier"].apply(lambda x: order_list.index(x) if x in order_list else 99)
    tiers = tiers.sort_values("_ord").reset_index(drop=True)

    fig, ax = _setup_slide_ax(
        "OTB Reallocation Blueprint: Style Footprint Share vs. Net Sales Share by Strategic Tier",
        "Comparing Current Active Style Share (%) vs. Net Sales Contribution (%) & Volume-Weighted NTF <51 Buyer Mix",
        "Actionable OTB shift: Rationalize low-productivity bloat style slots and reinvest directly into Hero & Under-Assorted Gem subclasses.",
        demo_mode=demo_mode,
        left=0.25,
        top=0.79,
    )

    y = np.arange(len(tiers))
    st_sh = 100.0 * tiers["style_share"]
    sa_sh = 100.0 * tiers["sales_dollar_share"]

    from matplotlib.patches import Patch
    ax.barh(y - 0.18, st_sh, height=0.33, color="#94A3B8")
    ax.barh(y + 0.18, sa_sh, height=0.33, color=[TIER_COLORS.get(t, PALETTE["teal"]) for t in tiers["action_tier"]])

    max_x = max(35.0, float(max(st_sh.max(), sa_sh.max())) * 1.38)
    ax.set_xlim(0, max_x)
    for idx, (_, r) in enumerate(tiers.iterrows()):
        sv = 100.0 * float(r["style_share"])
        dv = 100.0 * float(r["sales_dollar_share"])
        idx_v = float(r["sales_per_style_idx"])
        u51 = 100.0 * float(r["ntf_under_51"]) if pd.notna(r["ntf_under_51"]) else 0.0
        ax.text(sv + 0.5, idx - 0.18, f"{sv:.1f}% styles", va="center", fontsize=8.4, color="#475569", fontweight="semibold")
        ax.text(dv + 0.5, idx + 0.18, f"{dv:.1f}% sales  (Idx {idx_v:.0f} • {u51:.0f}% NTF <51)", va="center", fontsize=8.6, color="#0F172A", fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels([t.replace(" (", "\n(") for t in tiers["action_tier"]], fontsize=9.2, fontweight="bold", color="#0F172A")
    ax.set_xlabel("Share of Total Chain Styles vs. Net Sales (%)", fontsize=11, fontweight="bold", color=PALETTE["slate"])
    ax.legend(
        handles=[
            Patch(facecolor="#94A3B8", label="Current Active Style Share (% of Assortment)"),
            Patch(facecolor=PALETTE["teal"], label="Net Sales Dollar Share (% of Chain • Colored by Action Tier)"),
        ],
        loc="upper center", bbox_to_anchor=(0.45, 1.09), ncol=2, frameon=False, fontsize=9.0,
    )

    fig.savefig(out_path, dpi=240)
    plt.close(fig)
    return out_path


def export_full_pack(analysis: dict[str, Any], out_dir: Path | str, demo_mode: bool = False) -> dict[str, Path]:
    """Generate all 7 slide charts, masked-safe CSV scorecards, and judge narrative brief."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    files = {
        "slide_01": plot_01_over_under_assorted(analysis, out / "01_over_vs_under_assorted_matrix.png", demo_mode),
        "slide_02": plot_02_dual_mandate_quadrant(analysis, out / "02_dual_mandate_scorecard.png", demo_mode),
        "slide_03": plot_03_liv_vs_protect_age_mix(analysis, out / "03_liv_vs_protect_age_bridge.png", demo_mode),
        "slide_04": plot_04_denim_bet_scorecard(analysis, out / "04_denim_bet_deep_dive.png", demo_mode),
        "slide_05": plot_05_store_inventory_velocity(analysis, out / "05_store_inventory_velocity.png", demo_mode),
        "slide_06": plot_06_seasonality_and_yoy(analysis, out / "06_fiscal_seasonality_omnichannel.png", demo_mode),
        "slide_07": plot_07_otb_reallocation_blueprint(analysis, out / "07_otb_reallocation_blueprint.png", demo_mode),
    }

    sub = analysis["subclasses"].copy()
    export_cols = pd.DataFrame(
        {
            "composite_id": sub["comp_key"],
            "department": sub["dept_label"],
            "class": sub["class_label"],
            "subclass": sub["subclass_label"],
            "is_denim": sub["is_denim"],
            "action_tier": sub["action_tier"],
            "ideal_assortment_score": sub["ideal_assortment_score"].round(1),
            "sales_dollar_share_pct": (100.0 * sub["sales_dollar_share"]).round(3),
            "sales_unit_share_pct": (100.0 * sub["sales_unit_share"]).round(3),
            "style_share_pct": (100.0 * sub["style_share"]).round(3),
            "excess_style_share_pct": (100.0 * sub["excess_style_share"]).round(3),
            "sales_per_style_index": sub["sales_per_style_idx"].round(1),
            "avg_weekly_styles": sub["avg_style_count"].round(1),
            "weeks_active": sub["weeks_present"],
            "median_store_sell_through_pct": (100.0 * sub["median_store_sell_through"]).round(1),
            "avg_store_depth_per_choice": sub["avg_depth_per_choice"].round(2),
            "online_sales_share_pct": (100.0 * sub["online_share"]).round(1),
            "ntf_under_51_pct": (100.0 * sub["ntf_under_51"]).round(1),
            "ntf_liv_35_44_pct": (100.0 * sub["ntf_liv_35_44"]).round(1),
            "existing_protect_45_plus_pct": (100.0 * sub["existing_protect_45_plus"]).round(1),
            "yoy_sales_growth_pct": (100.0 * sub["yoy_sales_growth"]).round(1),
        }
    )
    csv_path = out / "assortment_recommendations_indexed.csv"
    export_cols.to_csv(csv_path, index=False)
    files["recommendations_csv"] = csv_path

    dept_csv = out / "department_scorecard_indexed.csv"
    analysis["departments"].drop(columns=["total_sales_dollars", "total_sales_units"], errors="ignore").to_csv(dept_csv, index=False)
    files["departments_csv"] = dept_csv

    d = analysis["diagnostics"]
    heroes = export_cols[export_cols["action_tier"].str.startswith(("Invest", "Expand"))].head(6)
    cuts = (
        export_cols[export_cols["action_tier"].str.startswith("Rationalize")]
        .sort_values("excess_style_share_pct", ascending=False)
        .head(6)
    )
    denim_winners = export_cols[export_cols["is_denim"]].head(5)

    hero_lines = "\n".join(
        f"- **{r['subclass']}** ({r['department']}): `{r['sales_per_style_index']}` Sales/Style Index, "
        f"`{r['sales_dollar_share_pct']:.2f}%` Sales Share vs `{r['style_share_pct']:.2f}%` Style Share, "
        f"`{r['ntf_under_51_pct']}%` NTF <51 (`{r['ntf_liv_35_44_pct']}%` Liv 35–44), `{r['online_sales_share_pct']}%` Online → *{r['action_tier']}*"
        for _, r in heroes.iterrows()
    )
    cut_lines = "\n".join(
        f"- **{r['subclass']}** ({r['department']}): `{r['style_share_pct']:.2f}%` Style Share (`{r['avg_weekly_styles']}` wkly styles) "
        f"for just `{r['sales_dollar_share_pct']:.2f}%` Sales Share (`{r['sales_per_style_index']}` Sales/Style Index)"
        for _, r in cuts.iterrows()
    )
    denim_lines = "\n".join(
        f"- **{r['subclass']}**: `{r['sales_per_style_index']}` Sales/Style Index | `{r['median_store_sell_through_pct']}%` Store Sell-Through | `{r['ntf_under_51_pct']}%` NTF <51 (`{r['online_sales_share_pct']}%` Online)"
        for _, r in denim_winners.iterrows()
    )

    dup_preview = ", ".join(d["duplicate_descriptions_disambiguated"][:8]) or "None"
    if d["duplicate_count"] > 8:
        dup_preview += f" (+{d['duplicate_count'] - 8} more)"

    brief_md = f"""# Executive Slide Brief — maurices Assortment & 'Liv' Growth Strategy

> **Methodology & Data Caveat Callout (Include on Slide 3 for Analytics Judges):**
> - All monetary figures are masked; performance is reported as **% Share of Chain** and **Sales-per-Style-Week Productivity Index (`100 = Chain Avg`)**.
> - With no COGS/margin column, **Profitability** is measured via **Assortment Productivity** (`Sales/Style Index`, `STORE Median Weekly Sell-Through`, and `Depth per Choice`).
> - Subclasses are joined on composite `(dept, class, subclass)` IDs after integer/text normalization (`{d['joined_subclasses']:,}` of `{d['total_product_subclasses']:,}` subclasses matched; `{d['duplicate_count']}` shared descriptions disambiguated: `{dup_preview}`).
> - `soh_units` (`{d['store_missing_soh_pct']}%` seasonal nulls) is averaged across active STORE weeks—never summed. `{d['store_st_over_100_pct']}%` of store weeks exceed `100%` sell-through due to mid-week restocking. Age distributions are positive-unit-volume weighted.

## 1. Chain Baseline Snapshot
- **Volume-Weighted Customer Mix (<51):** `{100*d['chain_weighted_under_51']:.1f}%` overall vs. **`{100*d['chain_weighted_ntf_under_51']:.1f}%` among New-to-File (NTF)** (`{100*d['chain_weighted_liv_35_44']:.1f}%` in Liv's `35–44` cohort; `{100*d['chain_weighted_protect_45_plus']:.1f}%` Existing `45+` Protect).
- **Omnichannel Online Share:** `{100*d['chain_online_share']:.1f}%` chain average (subclasses above `25%` strongly index to **Liv**).
- **Denim Signature Footprint:** `{d['denim_subclass_count']}` subclasses driving `{100*d['denim_sales_share']:.1f}%` of Chain Net Sales on `{100*d['denim_style_share']:.1f}%` of Active Style-Weeks.

## 2. Top Growth & Under-Assorted Winners (Reinvest Here)
{hero_lines}

## 3. Largest Over-Assorted Style-Bloat Subclasses to Rationalize (Fund OTB Reallocation)
{cut_lines}

## 4. The Denim Bet + CMO Marketing Activation (For Kristine, Renee & Kylie)
{denim_lines}

- **Why Denim + Fit Wins Both 'Liv' (35–44) & 'Protect' (45+):**
  1. **Body-Transition Authority:** `1 in 3` women changed clothing sizes this year (`~40%` using/considering GLP-1s). Position maurices' `0–24` inclusive sizing + modern stretch/wide-leg denim as the **"Confidence Fit Destination"**.
  2. **Unlock the Hidden Gem (Free In-Store Styling):** Awareness is `4%` unaided (`43%` aided), yet fashion-forward women convert strongly once considering maurices. Pair TikTok/IG creator "Fit-Drop" reels (`Liv` discovery) with **1-click "Book a Free 15-Min Denim & Outfit Styling Session"** (omnichannel store traffic driver) while keeping proven bootcut/core replenishment intact for `45+ Protect` loyalists.
"""
    brief_path = out / "slide_narrative_brief.md"
    brief_path.write_text(brief_md, encoding="utf-8")
    files["brief_md"] = brief_path
    return files
