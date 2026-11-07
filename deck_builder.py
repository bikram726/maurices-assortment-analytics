"""Automated 12-Slide Widescreen (16:9) PowerPoint Deck Builder for maurices Case Competition.

Runs 100% locally offline using `python-pptx`. Embeds the 7 high-DPI charts, dynamic
subclass/department metrics (% Share & Index = 100, never raw masked dollars),
CMO/CRM "Liv + Protect + Free Styling" strategy, Enterprise A/B test design, and
presenter speaker notes on every slide.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

NAVY = RGBColor(0x13, 0x29, 0x3D)
TEAL = RGBColor(0x0F, 0x76, 0x6E)
TEAL_BRIGHT = RGBColor(0x14, 0xB8, 0xA6)
TEAL_TINT = RGBColor(0xF0, 0xFD, 0xFA)
PLUM = RGBColor(0x6B, 0x21, 0xA8)
BERRY = RGBColor(0x9D, 0x17, 0x4D)
BERRY_TINT = RGBColor(0xFD, 0xF2, 0xF8)
SLATE = RGBColor(0x33, 0x41, 0x55)
MUTED = RGBColor(0x64, 0x74, 0x8B)
CARD_BG = RGBColor(0xF8, 0xFA, 0xFC)
BORDER = RGBColor(0xCB, 0xD5, 0xE1)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def _add_rect(slide, x: float, y: float, w: float, h: float, fill: RGBColor, border: RGBColor | None = None, radius: bool = True):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if border:
        shp.line.color.rgb = border
        shp.line.width = Pt(1.0)
    else:
        shp.line.fill.background()
    if radius and hasattr(shp, "adjustments") and len(shp.adjustments) > 0:
        shp.adjustments[0] = 0.04
    return shp


def _add_textbox(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    size: float = 12,
    color: RGBColor = SLATE,
    bold: bool = False,
    align=PP_ALIGN.LEFT,
):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.05)
    tf.margin_right = Inches(0.05)
    tf.margin_top = Inches(0.03)
    tf.margin_bottom = Inches(0.03)
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.name = "Segoe UI"
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    return tb


def _add_bullets(slide, x: float, y: float, w: float, h: float, items: list[tuple[str, str]], font_size: float = 10.5):
    """Add clean bold-lead bullet paragraphs: [(lead_bold, body_text), ...]."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.06)
    tf.margin_right = Inches(0.06)
    tf.margin_top = Inches(0.04)
    tf.margin_bottom = Inches(0.04)
    for idx, (lead, body) in enumerate(items):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.space_after = Pt(5.5)
        r1 = p.add_run()
        r1.text = f"▪ {lead}: " if lead else "▪ "
        r1.font.name = "Segoe UI"
        r1.font.size = Pt(font_size)
        r1.font.bold = True
        r1.font.color.rgb = NAVY
        r2 = p.add_run()
        r2.text = body
        r2.font.name = "Segoe UI"
        r2.font.size = Pt(font_size)
        r2.font.color.rgb = SLATE
    return tb


def _set_notes(slide, text: str) -> None:
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = text.strip()


def _new_chrome_slide(prs: Presentation, blank_layout, slide_num: int, title: str, subtitle: str, footer: str, demo_mode: bool):
    slide = prs.slides.add_slide(blank_layout)
    _add_rect(slide, 0, 0, 13.333, 0.09, TEAL, radius=False)
    _add_textbox(slide, 0.45, 0.18, 11.7, 0.46, title, size=18.5, color=NAVY, bold=True)
    _add_textbox(slide, 0.45, 0.62, 12.1, 0.30, subtitle, size=10.5, color=MUTED)

    pill = _add_rect(slide, 12.32, 0.20, 0.58, 0.32, TEAL_TINT, border=TEAL)
    tf = pill.text_frame
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    r = tf.paragraphs[0].add_run()
    r.text = f"{slide_num}/12"
    r.font.name = "Segoe UI"
    r.font.size = Pt(9.5)
    r.font.bold = True
    r.font.color.rgb = TEAL

    if demo_mode:
        _add_textbox(slide, 10.1, 0.22, 2.15, 0.28, "DEMO DATA PREVIEW", size=9, color=BERRY, bold=True, align=PP_ALIGN.RIGHT)

    _add_rect(slide, 0.45, 7.08, 12.43, 0.015, BORDER, radius=False)
    _add_textbox(slide, 0.45, 7.12, 12.43, 0.28, footer, size=8.2, color=MUTED)
    return slide


def _add_kpi_card(slide, x: float, y: float, w: float, h: float, label: str, big_val: str, sub_txt: str, accent: RGBColor = TEAL):
    _add_rect(slide, x, y, w, h, CARD_BG, border=BORDER)
    _add_rect(slide, x, y, 0.08, h, accent, radius=False)
    _add_textbox(slide, x + 0.16, y + 0.08, w - 0.22, 0.28, label.upper(), size=8.8, color=MUTED, bold=True)
    _add_textbox(slide, x + 0.16, y + 0.34, w - 0.22, 0.46, big_val, size=20.5, color=NAVY, bold=True)
    _add_textbox(slide, x + 0.16, y + 0.82, w - 0.22, 0.36, sub_txt, size=9.0, color=SLATE)


def build_presentation_deck(
    analysis: dict[str, Any],
    chart_files: dict[str, Path],
    out_pptx: Path | str,
    demo_mode: bool = False,
) -> Path:
    """Build the complete 12-slide 16:9 maurices strategy presentation."""
    out_path = Path(out_pptx)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    d = analysis["diagnostics"]
    sub = analysis["subclasses"]
    depts = analysis["departments"]
    clss = analysis["classes"]
    tiers = analysis["tiers"]

    def _tier_stat(prefix: str, col: str) -> float:
        m = tiers[tiers["action_tier"].str.startswith(prefix)]
        return float(m[col].sum()) if not m.empty else 0.0

    bloat_style_sh = 100.0 * _tier_stat("Rationalize", "style_share")
    bloat_sales_sh = 100.0 * _tier_stat("Rationalize", "sales_dollar_share")
    hero_style_sh = 100.0 * (_tier_stat("Invest", "style_share") + _tier_stat("Expand", "style_share"))
    hero_sales_sh = 100.0 * (_tier_stat("Invest", "sales_dollar_share") + _tier_stat("Expand", "sales_dollar_share"))
    protect_sales_sh = 100.0 * _tier_stat("Protect", "sales_dollar_share")

    heroes = sub[sub["action_tier"].str.startswith(("Invest", "Expand"))].head(5)
    cuts = sub[sub["action_tier"].str.startswith("Rationalize")].sort_values("excess_style_share", ascending=False).head(5)
    denim_df = sub[sub["is_denim"]].copy()
    denim_top = denim_df.head(3)
    denim_cut = denim_df.sort_values("excess_style_share", ascending=False).head(2)

    footer_std = "maurices × UMD 24-Hour Case Competition • All masked sales expressed as % Share & Productivity Index (Chain Avg = 100)"

    # ---------------- SLIDE 1: COVER ----------------
    s1 = prs.slides.add_slide(blank)
    _add_rect(s1, 0, 0, 13.333, 7.5, NAVY, radius=False)
    _add_rect(s1, 0, 0, 0.22, 7.5, TEAL_BRIGHT, radius=False)
    _add_rect(s1, 0.85, 1.05, 4.9, 0.40, TEAL, radius=True)
    _add_textbox(s1, 0.95, 1.10, 4.7, 0.32, "2026 UMD × maurices DATA COMPETITION", size=10.5, color=WHITE, bold=True)
    _add_textbox(s1, 0.85, 1.75, 11.4, 1.45, "Rebalancing the Rack for 'Liv' & Loyalty", size=36, color=WHITE, bold=True)
    _add_textbox(
        s1, 0.85, 3.15, 10.8, 0.95,
        "An Assortment Productivity, Inclusive 0–24 Fit & Omnichannel Styling Playbook to Grow Younger (<51) Shoppers While Protecting maurices' Core Loyalists",
        size=15.5, color=RGBColor(0xCB, 0xD5, 0xE1),
    )
    cards_cover = [
        ("1. REALLOCATE OTB", f"Trim {bloat_style_sh:.1f}% bloat style footprint returning just {bloat_sales_sh:.1f}% of sales; fund high-index winners."),
        ("2. WIN 'LIV' (35–44)", f"Scale high-velocity Denim & Outfit heroes indexing at {100*d['chain_weighted_ntf_under_51']:.0f}%+ NTF <51 & 25%+ Omni."),
        ("3. STYLING + FIT HOOK", "Pair 0–24 GLP-1/size-shift fit authority with maurices' hidden-gem Free In-Store Styling."),
    ]
    for i, (ct, cb) in enumerate(cards_cover):
        cx = 0.85 + i * 3.95
        _add_rect(s1, cx, 4.85, 3.72, 1.65, RGBColor(0x1E, 0x3A, 0x52), border=TEAL_BRIGHT)
        _add_textbox(s1, cx + 0.18, 5.00, 3.36, 0.34, ct, size=11, color=TEAL_BRIGHT, bold=True)
        _add_textbox(s1, cx + 0.18, 5.38, 3.36, 0.98, cb, size=10.2, color=WHITE)
    _set_notes(
        s1,
        "Welcome Kristine, Derick, Renee, and Kylie. Today we answer maurices' core challenge: how to reverse a shrinking, aging customer file—where median age hit 51 and 30-to-39 shoppers fell 175 bps—without alienating the 45+ loyalists who power top-decile visits. Our answer combines rigorous assortment productivity rebalancing with 'Hometown is our why, Styling is our how.'",
    )

    # ---------------- SLIDE 2: EXECUTIVE SUMMARY ----------------
    s2 = _new_chrome_slide(
        prs, blank, 2,
        "Executive Summary: Self-Funding 'Liv' Growth by Cutting Unproductive Style Bloat",
        "Across 104 fiscal weeks, maurices has the right hero categories—but style breadth is trapped in low-velocity, older-skewing tails",
        footer_std, demo_mode,
    )
    _add_kpi_card(s2, 0.45, 1.08, 2.95, 1.25, "Assortment Audited", f"{d['total_product_subclasses']:,} Subclasses", f"{d['weeks_count']} wks • {d['department_count']} Depts • {d['class_count']} Classes", TEAL)
    _add_kpi_card(s2, 3.60, 1.08, 2.95, 1.25, "NTF Younger (<51) Share", f"{100*d['chain_weighted_ntf_under_51']:.1f}%", f"'Liv' (35–44) = {100*d['chain_weighted_liv_35_44']:.1f}% of NTF units", PLUM)
    _add_kpi_card(s2, 6.75, 1.08, 2.95, 1.25, "Hero + Gem Efficiency", f"{hero_sales_sh:.1f}% Sales", f"Generated on just {hero_style_sh:.1f}% of active styles", TEAL_BRIGHT)
    _add_kpi_card(s2, 9.90, 1.08, 2.98, 1.25, "Over-Assorted Tail Bloat", f"{bloat_style_sh:.1f}% Styles", f"Yielding only {bloat_sales_sh:.1f}% of net sales", BERRY)

    pillars = [
        (
            "MOVE 1: Rationalize Style Tail (-25% to -35% Choices)",
            BERRY,
            [
                ("The Leak", f"Rationalize-tier subclasses absorb {bloat_style_sh:.1f}% of active style-weeks for just {bloat_sales_sh:.1f}% of sales—fragmenting store racks and starving depth."),
                ("OTB Unlock", "Eliminate Bottom-Quartile duplicate styles in over-assorted classes to self-fund inventory depth in top turns without raising total OTB risk."),
            ],
        ),
        (
            "MOVE 2: Double Down on 'Liv' & Under-Assorted Gems",
            TEAL,
            [
                ("Success Criteria #1 & #2", f"Hero & Gem tiers deliver {hero_sales_sh:.1f}% of sales on {hero_style_sh:.1f}% of styles while over-indexing on <51 NTF & {100*d['chain_online_share']:.1f}%+ Online demand."),
                ("Protect Guardrail", f"Preserve choice depth on {protect_sales_sh:.1f}% sales share in 'Protect Core' (45+ Cash Cows) so top-decile loyalists always find proven fits."),
            ],
        ),
        (
            "MOVE 3: Activate Fit Confidence + Free Styling",
            PLUM,
            [
                ("GLP-1 / Size Shift Moment", "1 in 3 women changed sizes this year (~40% GLP-1 impact). Own 0–24 fit transitions led by modern stretch Denim + polished layers."),
                ("4% → Omni Flywheel", "Turn near-zero awareness of Free In-Store Styling into 'Liv's' #1 reason to visit stores via creator reels + 1-click fit booking."),
            ],
        ),
    ]
    for i, (ptitle, pcol, pbullets) in enumerate(pillars):
        px = 0.45 + i * 4.20
        _add_rect(s2, px, 2.55, 4.02, 4.35, CARD_BG, border=BORDER)
        _add_rect(s2, px, 2.55, 4.02, 0.46, pcol, radius=False)
        _add_textbox(s2, px + 0.14, 2.62, 3.75, 0.34, ptitle, size=10.8, color=WHITE, bold=True)
        _add_bullets(s2, px + 0.10, 3.12, 3.82, 3.65, pbullets, font_size=10.2)
    _set_notes(
        s2,
        "Here is our entire recommendation on one page. We don't ask maurices to spend more OTB—we reallocate existing style slots from over-assorted tails into high-productivity subclasses that pull younger NTF buyers, while ring-fencing 45+ cash cows and pairing the assortment shift with Free In-Store Styling.",
    )

    # ---------------- SLIDE 3: METHODOLOGY & CAVEATS ----------------
    s3 = _new_chrome_slide(
        prs, blank, 3,
        "Analytical Governance: Every Data Dictionary Caveat Explicitly Engineered",
        "Built for enterprise auditability—zero raw masked dollar claims, zero unweighted age averages, and clean channel separation",
        footer_std, demo_mode,
    )
    gov_items = [
        ("1. Masked Values → Share & Index", f"Never quote masked dollars/AUR as real figures. All visuals use % Share of Chain and Sales/Style-Week Index (100 = Chain Avg) across {d['product_rows']:,} rows."),
        ("2. Profitability Proxy (No COGS)", "With margin absent, profitability is operationalized via Sales per Style-Week (breadth efficiency), STORE Median Weekly Sell-Through, and Depth per Choice."),
        ("3. Composite Key Normalization", f"Cast text IDs ('004') and integer IDs (4) to canonical dept|class|subclass keys—matching {d['joined_subclasses']:,} customer rows and separating {d['duplicate_count']} shared subclass names."),
        ("4. Unit-Weighted & Stabilized Age Mix", "Stripped '%' text across all 48 age columns, shrunk sparse small-sample NTF rows (33.3%/50% flukes), and unit-weighted every rollup."),
        ("5. Weekly STORE Snapshot SOH", f"Averaged soh_units across active STORE weeks only (never summed across weeks or channels; {d['store_missing_soh_pct']}% seasonal null store rows handled cleanly)."),
        ("6. >100% Sell-Through & Returns", f"{d['store_st_over_100_pct']}% of STORE rows exceed 100% sell-through from mid-week restocking (modeled via median + restock frequency); {d['negative_unit_rows']:,} net-return rows preserved."),
    ]
    for idx, (gt, gb) in enumerate(gov_items):
        col_i = idx % 2
        row_i = idx // 2
        gx = 0.45 + col_i * 6.28
        gy = 1.12 + row_i * 1.92
        _add_rect(s3, gx, gy, 6.12, 1.74, CARD_BG, border=BORDER)
        _add_rect(s3, gx, gy, 0.09, 1.74, TEAL if col_i == 0 else PLUM, radius=False)
        _add_textbox(s3, gx + 0.18, gy + 0.12, 5.8, 0.34, gt, size=12, color=NAVY, bold=True)
        _add_textbox(s3, gx + 0.18, gy + 0.50, 5.8, 1.14, gb, size=10.3, color=SLATE)
    _set_notes(
        s3,
        "For Derick and Renee's analytics teams: before touching strategy, we locked down every schema trap in the data dictionary—composite dept-class-subclass joins across varchar and integer IDs, disambiguating shared names like FASHION CARDI, weighting age percentages by unit volume, and isolating STORE-only weekly stock snapshots.",
    )

    # ---------------- SLIDE 4: CUSTOMER ARCHITECTURE (LIV VS PROTECT) ----------------
    s4 = _new_chrome_slide(
        prs, blank, 4,
        "Customer Diagnosis: Why the File Aged to 51—and Where 'Liv' (35–44) Converts",
        "Legacy basics attract bimodal (60+ & 1-trip) NTF buyers—whereas modern gateway categories pull 70%+ under age 51",
        footer_std, demo_mode,
    )
    s4.shapes.add_picture(str(chart_files["slide_03"]), Inches(0.42), Inches(1.06), width=Inches(8.35))
    top_youth_depts = depts.dropna(subset=["ntf_under_51"]).sort_values("ntf_under_51", ascending=False).head(3)
    youth_dept_str = ", ".join(f"{r['dept_label']} ({100*r['ntf_under_51']:.0f}% NTF <51)" for _, r in top_youth_depts.iterrows())
    _add_rect(s4, 8.92, 1.08, 3.96, 5.82, CARD_BG, border=BORDER)
    _add_textbox(s4, 9.08, 1.20, 3.65, 0.36, "WHY THE FILE IS AGING—AND THE FIX", size=11.5, color=PLUM, bold=True)
    _add_bullets(
        s4, 9.04, 1.60, 3.74, 5.20,
        [
            ("The Bimodal NTF Trap", "In traditional core basics, even New-to-File entrants skew 60+ or 1-trip 18–29—under-indexing on 35–44 ('Liv') vs. Existing and driving the -175 bps 30–39 leak."),
            ("Gateway Depts Pull Younger", f"Modern gateway categories break the aging trend: {youth_dept_str}."),
            ("Meet 'Liv' (Age 35, $236/yr)", "25% omnichannel (vs 16% chain avg), $75K–$125K HHI, cross-shops AE, GAP & Target. Wants fit confidence, current silhouettes, and value beyond promo."),
            ("Dual-Track Architecture", "Shift style breadth into modern gateway subclasses to acquire 'Liv' while ring-fencing core fit blocks for 45+ 'Protect' decile 1–3 loyalists."),
        ],
        font_size=9.8,
    )
    _set_notes(
        s4,
        "Look closely at the orange diamonds versus the bars on Slide 4—this is a critical finding in the customer file. maurices isn't just passively aging with existing shoppers: in traditional basics, even New-to-File entrants skew 60+ and under-index on 35-to-44 'Liv', directly explaining why 30-to-39 fell 175 bps while 60+ grew 246 bps. Yet in modern gateway departments and trend subclasses, under-51 share surges past 70%. When the product feels current, Liv converts.",
    )

    # ---------------- SLIDE 5: OVER VS UNDER ASSORTED ----------------
    s5 = _new_chrome_slide(
        prs, blank, 5,
        "Class Assortment Audit: Identifying Over-Assorted Bloat vs. Under-Invested Gems",
        "Comparing active style-week share against Sales-per-Style Productivity Index exposes immediate OTB reallocation targets",
        footer_std, demo_mode,
    )
    s5.shapes.add_picture(str(chart_files["slide_01"]), Inches(0.42), Inches(1.06), width=Inches(8.35))
    valid_cls = clss[clss["style_share"] > 0.003].copy()
    win_cls = valid_cls.sort_values("sales_per_style_idx", ascending=False).head(3)
    bloat_cls = valid_cls.assign(_exc=valid_cls["style_share"] - valid_cls["sales_dollar_share"]).sort_values("_exc", ascending=False).head(3)
    win_txt = "; ".join(f"{r['class_label']} (Idx {r['sales_per_style_idx']:.0f})" for _, r in win_cls.iterrows())
    bloat_txt = "; ".join(f"{r['class_label']} (Idx {r['sales_per_style_idx']:.0f})" for _, r in bloat_cls.iterrows())
    _add_rect(s5, 8.92, 1.08, 3.96, 5.82, CARD_BG, border=BORDER)
    _add_textbox(s5, 9.08, 1.20, 3.65, 0.36, "CLASS PRODUCTIVITY DIAGNOSIS", size=11.5, color=TEAL, bold=True)
    _add_bullets(
        s5, 9.04, 1.60, 3.74, 5.20,
        [
            ("Under-Assorted Winners", f"Highest productivity classes ({win_txt}) generate outsized sales per style slot—signal to expand colorways and size depth."),
            ("Over-Assorted Style Bloat", f"Largest style-excess classes ({bloat_txt}) dilute visual merchandising on the floor and trap working capital."),
            ("Why Breadth Hurts 'Liv'", "Too many near-identical traditional styles create decision fatigue in-store instead of a curated 'outfit drop' point of view."),
            ("Rule of 100", "Classes below Index 80 with <median NTF <51 fund OTB transfers into Index 115+ classes."),
        ],
        font_size=9.9,
    )
    _set_notes(
        s5,
        "Here we test maurices' hypothesis directly: yes, the assortment is over-skewed in low-productivity legacy classes and under-invested in high-velocity classes. Every point above the dashed 100 line delivers superior sales per style-week on the floor.",
    )

    # ---------------- SLIDE 6: DUAL MANDATE MATRIX ----------------
    s6 = _new_chrome_slide(
        prs, blank, 6,
        "Dual-Mandate Subclass Matrix: Scoring Both Success Criteria Simultaneously",
        "Every subclass ranked on SC#1 (Dollar Share, Unit Volume & Sales/Style) and SC#2 (Younger <51 NTF + Liv 35–44 + Omni)",
        footer_std, demo_mode,
    )
    s6.shapes.add_picture(str(chart_files["slide_02"]), Inches(0.42), Inches(1.06), width=Inches(8.35))
    _add_rect(s6, 8.92, 1.08, 3.96, 5.82, CARD_BG, border=BORDER)
    _add_textbox(s6, 9.08, 1.20, 3.65, 0.36, "5-TIER MERCHANDISING RULES", size=11.5, color=NAVY, bold=True)
    _add_bullets(
        s6, 9.04, 1.60, 3.74, 5.20,
        [
            ("Invest & Scale (Hero + Liv)", "Top SC#1 & SC#2: +15–20% OTB depth, lead window/social drops, full 0–24 size curve."),
            ("Expand Depth & Styles (Gem)", "High productivity & young NTF on lean style counts: add +2–4 fresh seasonal styles per quarter."),
            ("Protect Core (45+ Cash Cow)", "High volume/productivity, older loyalist base: lock never-out replenishment, zero style bloat."),
            ("Curate & Refresh (Trend)", "Attracts <51 NTF but low sales/style: trim duplicate styles by 20%, rotate faster capsule drops."),
            ("Rationalize Bloat (Cut Tail)", "Low sales/style & older skew: cut 30–40% of tail styles to fund Heroes & Gems."),
        ],
        font_size=9.8,
    )
    _set_notes(
        s6,
        "Instead of a one-size-fits-all cut, our 5-tier classification balances both competition success criteria at the composite subclass ID level—ensuring we grow Liv in the upper-right quadrant while protecting 45+ cash cows in the lower-right.",
    )

    # ---------------- SLIDE 7: OTB BLUEPRINT + ACTION TABLE ----------------
    s7 = _new_chrome_slide(
        prs, blank, 7,
        "Actionable Assortment Plan: Specific Subclasses to Scale vs. Rationalize",
        "Left: Chain OTB style-to-sales mismatch by tier • Right: Priority Hero expansions & largest style-bloat reductions",
        footer_std, demo_mode,
    )
    s7.shapes.add_picture(str(chart_files["slide_07"]), Inches(0.40), Inches(1.12), width=Inches(6.05))

    tbl_rows_data = []
    for _, r in heroes.head(5).iterrows():
        tbl_rows_data.append((str(r["subclass_label"])[:22], str(r["dept_label"])[:12], f"{100*r['style_share']:.2f}%", f"{100*r['sales_dollar_share']:.2f}%", f"{r['sales_per_style_idx']:.0f}", f"{100*r['ntf_under_51']:.0f}%", "SCALE / EXPAND"))
    for _, r in cuts.head(5).iterrows():
        tbl_rows_data.append((str(r["subclass_label"])[:22], str(r["dept_label"])[:12], f"{100*r['style_share']:.2f}%", f"{100*r['sales_dollar_share']:.2f}%", f"{r['sales_per_style_idx']:.0f}", f"{100*(r['ntf_under_51'] if pd.notna(r['ntf_under_51']) else 0):.0f}%", "TRIM BLOAT"))

    headers = ["Subclass (ID-Safe)", "Dept", "Style%", "Sales%", "Idx", "NTF<51", "Action"]
    n_rows = len(tbl_rows_data) + 1
    tbl_shape = s7.shapes.add_table(n_rows, len(headers), Inches(6.55), Inches(1.12), Inches(6.35), Inches(5.72))
    tbl = tbl_shape.table
    col_widths = [1.85, 1.05, 0.66, 0.66, 0.52, 0.63, 0.98]
    for ci, cw in enumerate(col_widths):
        tbl.columns[ci].width = Inches(cw)

    for ci, htxt in enumerate(headers):
        cell = tbl.cell(0, ci)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if ci >= 2 else PP_ALIGN.LEFT
        run = p.add_run()
        run.text = htxt
        run.font.name = "Segoe UI"
        run.font.size = Pt(8.5)
        run.font.bold = True
        run.font.color.rgb = WHITE

    for ri, row_vals in enumerate(tbl_rows_data, start=1):
        is_scale = row_vals[-1].startswith("SCALE")
        row_bg = TEAL_TINT if is_scale else BERRY_TINT
        for ci, val in enumerate(row_vals):
            cell = tbl.cell(ri, ci)
            cell.fill.solid()
            cell.fill.fore_color.rgb = row_bg if ci == 6 else (WHITE if ri % 2 == 1 else CARD_BG)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if ci >= 2 else PP_ALIGN.LEFT
            run = p.add_run()
            run.text = val
            run.font.name = "Segoe UI"
            run.font.size = Pt(8.0)
            run.font.bold = ci in (0, 6)
            run.font.color.rgb = (TEAL if is_scale else BERRY) if ci == 6 else SLATE
    _set_notes(
        s7,
        "Slide 7 translates analytics into Monday-morning buying actions: on the left is the exact OTB mismatch across tiers, and on the right are the top 5 subclasses to expand versus the 5 largest style-excess subclasses to rationalize.",
    )

    # ---------------- SLIDE 8: THE DENIM BET ----------------
    s8 = _new_chrome_slide(
        prs, blank, 8,
        "Testing the Denim Bet: Anchor 'Liv' Acquisition in Modern 0–24 Fit Solutions",
        "Denim is maurices' heritage superpower—modernizing silhouettes while trimming stale washes wins both volume and youth",
        footer_std, demo_mode,
    )
    s8.shapes.add_picture(str(chart_files["slide_04"]), Inches(0.42), Inches(1.06), width=Inches(8.35))
    d_win_names = ", ".join(str(r["subclass_label"])[:22] for _, r in denim_top.iterrows()) or "Top Modern Fits"
    d_cut_names = ", ".join(str(r["subclass_label"])[:22] for _, r in denim_cut.iterrows()) or "Legacy Slow Washes"
    _add_rect(s8, 8.92, 1.08, 3.96, 5.82, CARD_BG, border=BORDER)
    _add_textbox(s8, 9.08, 1.20, 3.65, 0.36, "DENIM + BODY-CHANGE VERDICT", size=11.5, color=TEAL, bold=True)
    _add_bullets(
        s8, 9.04, 1.60, 3.74, 5.20,
        [
            ("Data Proof", f"{d['denim_subclass_count']} denim subclasses generate {100*d['denim_sales_share']:.1f}% of chain sales on {100*d['denim_style_share']:.1f}% of active styles."),
            ("Scale Modern Fits", f"Prioritize depth in {d_win_names}—high Sales/Style Index, strong <51 NTF pull, and strong Online share."),
            ("Consolidate Legacy Washes", f"Rationalize duplicate washes in {d_cut_names} while keeping core bootcut sizes stocked for 45+ loyalists."),
            ("The GLP-1 / Size-Change Hook", "With 1 in 3 women changing sizes (~40% GLP-1 consideration), jeans are the hardest item to re-buy. Own 'Find Your New Fit in Sizes 0–24'."),
        ],
        font_size=9.8,
    )
    _set_notes(
        s8,
        "Why lead with Denim? Because 1 in 3 women changed clothing sizes this year, and nearly 4 in 10 are using or considering GLP-1s. When your body changes, buying jeans is stressful—and maurices carries sizes 0 to 24 under one roof with free stylists.",
    )

    # ---------------- SLIDE 9: STORE INVENTORY EXECUTION ----------------
    s9 = _new_chrome_slide(
        prs, blank, 9,
        "Store Inventory Execution: Rebuilding Size Depth on Fast-Restock Winners",
        "STORE-only sell-through and choice depth show hero items outrunning shelf stock while bloat styles sit shallow and slow",
        footer_std, demo_mode,
    )
    s9.shapes.add_picture(str(chart_files["slide_05"]), Inches(0.42), Inches(1.06), width=Inches(8.35))
    _add_rect(s9, 8.92, 1.08, 3.96, 5.82, CARD_BG, border=BORDER)
    _add_textbox(s9, 9.08, 1.20, 3.65, 0.36, "STORE REPLENISHMENT PLAYBOOK", size=11.5, color=NAVY, bold=True)
    _add_bullets(
        s9, 9.04, 1.60, 3.74, 5.20,
        [
            ("Mid-Week Restock Signal", f"{d['store_st_over_100_pct']}% of active store weeks exceed 100% weekly sell-through (median normal week: {d['store_median_st_pct']}%)—proving rapid store turn on key items."),
            ("Broken Size Curves Hurt Fit", "When depth per style-color drops to 1–3 units on trend winners, 'Liv' walks into a store and misses her size (especially mid-curve sizes 8–18)."),
            ("Fewer Choices, Deeper Runs", "Reinvest cut bloat units to raise store depth per choice by +25% on Hero Denim, Tees & Occasion Tops."),
            ("BOPIS / Ship-from-Store", "Deeper hero store stock simultaneously powers Liv's 25% omnichannel shopping habit."),
        ],
        font_size=9.8,
    )
    _set_notes(
        s9,
        "Nothing kills an in-store styling session faster than a broken size run. In our STORE-only analysis, over a fifth of subclass-weeks experience mid-week restocking over 100% sell-through. Fewer slow choices means deeper 0-to-24 size curves on winners.",
    )

    # ---------------- SLIDE 10: 4-5-4 SEASONALITY ----------------
    s10 = _new_chrome_slide(
        prs, blank, 10,
        "4-5-4 Fiscal Calendar Pacing: Converting Episodic Event Shoppers into Repeat Buyers",
        "Aligning newness drops and YoY growth tiers to maurices' August-start fiscal calendar (Q1 Fall → Q4 Summer)",
        footer_std, demo_mode,
    )
    s10.shapes.add_picture(str(chart_files["slide_06"]), Inches(0.42), Inches(1.06), width=Inches(8.35))
    _add_rect(s10, 8.92, 1.08, 3.96, 5.82, CARD_BG, border=BORDER)
    _add_textbox(s10, 9.08, 1.20, 3.65, 0.36, "4-QUARTER DROP & FLOW CALENDAR", size=11.5, color=PLUM, bold=True)
    _add_bullets(
        s10, 9.04, 1.60, 3.74, 5.20,
        [
            ("Q1 (Aug–Oct): Fit & Fall Reset", "Anchor Back-to-School/Work with Sculpt & Wide-Leg Denim + Blazer/Cardi outfit bundles."),
            ("Q2 (Nov–Jan): Holiday Capture", "Peak traffic from bottom-decile 20–39 event shoppers—insert 'January Fit Refresh' styling bounce-back on every Q2 receipt."),
            ("Q3 (Feb–Apr): Occasion & Spring", "Capture weddings, graduations & spring break with Midi Event Dresses + light layers."),
            ("Q4 (May–Jul): Travel & Ease", "Lean capsule drops in breathable knits, shorts & travel sets; clear seasonal SOH cleanly before Aug Q1."),
        ],
        font_size=9.8,
    )
    _set_notes(
        s10,
        "The kickoff deck revealed that 20-to-39 shoppers cluster in light and bottom deciles—showing up for Q2 holidays or special events and disappearing. Our 4-5-4 calendar uses Q2 holiday dresses and gifting as the acquisition hook into a Q3 Denim Fit Refresh.",
    )

    # ---------------- SLIDE 11: CMO & CRM PLAYBOOK ----------------
    s11 = _new_chrome_slide(
        prs, blank, 11,
        "Marketing & CRM Activation: 'Hometown Is Our Why + Styling Is Our How'",
        "Connecting the rebalanced assortment to Kristine, Renee & Kylie's customer funnel—without leading on margin-eroding promos",
        footer_std, demo_mode,
    )
    funnel_cols = [
        (
            "1. DISCOVERY (4% → 15%+ Unaided)",
            TEAL,
            [
                ("Creator 'Same Look, 3 Sizes'", "Midwest micro-creators style 1 Hero Jean + Top on sizes 4, 12 & 20—solving 'will this work on my body?' on IG/TikTok."),
                ("Drop Storytelling, Not % Off", "Lead with product benefit (sculpt stretch, desk-to-dinner versatility); save promo nudge strictly as cart closer."),
                ("Geo-Targeted Hometown Paid", "Focus paid social within 15 miles of 800+ stores targeting HHI $75K–$125K women 30–44."),
            ],
        ),
        (
            "2. CONVERSION (Free Styling Engine)",
            PLUM,
            [
                ("Rebrand Free In-Store Styling", "Launch '15-Minute Confidence Fit Session'—zero pressure, pre-pulled dressing room in sizes 0–24."),
                ("GLP-1 / Size-Transition Hook", "'Changed sizes this year? Let a stylist rebuild your 3 core outfits'—turns anxiety into store love."),
                ("BOPIS-to-Fitting-Room Bridge", "Online order pickup triggers instant $15 styling outfit add-on credit when trying on 2+ complementary pieces."),
            ],
        ),
        (
            "3. CRM RETENTION (Kylie's 2-Track)",
            BERRY,
            [
                ("Track A — 'Liv' NTF (<45)", "Day-21 post-purchase SMS/email dynamically pairing her exact subclass (e.g., Wide-Leg Jean → 3 Trending Tops) to drive Trip #2."),
                ("Track B — 'Protect' Core (45+)", "VIP early-access restock alerts & fit-continuity guarantees on Core Bootcut, Tees & Pullovers."),
                ("Decile 7–10 Win-Back", "Convert single-trip Q2 holiday buyers with personalized Spring Occasion + Free Styling invite."),
            ],
        ),
    ]
    for i, (ftitle, fcol, fbullets) in enumerate(funnel_cols):
        fx = 0.45 + i * 4.20
        _add_rect(s11, fx, 1.12, 4.02, 5.78, CARD_BG, border=BORDER)
        _add_rect(s11, fx, 1.12, 4.02, 0.46, fcol, radius=False)
        _add_textbox(s11, fx + 0.14, 1.19, 3.75, 0.34, ftitle, size=10.8, color=WHITE, bold=True)
        _add_bullets(s11, fx + 0.10, 1.70, 3.82, 5.05, fbullets, font_size=10.0)
    _set_notes(
        s11,
        "Assortment alone doesn't fix 4% unaided awareness. Here is how Marketing and CRM turn our hero subclasses into customer lifetime value: creator '3-size' reels build social relevance for Liv, 15-minute Free Fit Sessions convert omnichannel traffic, and segmented CRM journeys protect 45+ loyalty while pushing NTF buyers from 1 trip to 3.2+ trips.",
    )

    # ---------------- SLIDE 12: TESTING & ROLLOUT ----------------
    s12 = _new_chrome_slide(
        prs, blank, 12,
        "Enterprise Testing & 90-Day Rollout: Proving Lift Before Chainwide Scale",
        "Designed for Derick's Enterprise Analytics & Testing team—matched-market store test + CRM holdout with strict guardrails",
        footer_std, demo_mode,
    )
    _add_rect(s12, 0.45, 1.12, 5.95, 5.78, CARD_BG, border=BORDER)
    _add_textbox(s12, 0.62, 1.24, 5.6, 0.36, "MATCHED-PAIR TEST & LEARN DESIGN (13 WEEKS)", size=11.8, color=NAVY, bold=True)
    _add_bullets(
        s12, 0.58, 1.66, 5.7, 5.05,
        [
            ("Cell 1 — Assortment Only (15 Stores)", "Trim Bottom-Quartile bloat styles (-30%), increase Hero & Gem choice depth (+25%) vs 15 matched control stores."),
            ("Cell 2 — Assortment + Styling Activation (15 Stores)", "Rebalanced assortment PLUS localized IG/TikTok Fit-Session ads, mirror QR codes, and BOPIS styling prompts."),
            ("Digital & CRM Holdout (10% Control)", "A/B test 'Complete-the-Look' subclass triggers vs standard promo blast on NTF <45 60-day repeat rate."),
            ("90-Day Phased Execution", "Days 1–30: OTB open-to-buy freeze on bloat tail • Days 31–60: 30-store pilot launch • Days 61–90: Read lift & scale for Q1/Q2 peak."),
        ],
        font_size=10.0,
    )

    kpi_headers = ["Dimension", "Primary Metric", "Target / Guardrail"]
    kpi_rows = [
        ("SC #1 Productivity", "Sales per Style-Week Index", "+8% to +12% vs Matched Control"),
        ("Store Velocity", "Median Weekly Store Sell-Through", "+150 to +250 bps; fewer Hero stockouts"),
        ("SC #2 Acquisition", "New-to-File Share Under Age 51", "+300 bps lift (led by 'Liv' 35–44)"),
        ("Omnichannel Lift", "2-Channel Shopper Rate & Styling Bookings", "Move chain 16% omni toward Liv's 25%"),
        ("Protect Guardrail", "45+ Existing Customer Retention & Units", ">= 100% of Control (zero core erosion)"),
    ]
    t12 = s12.shapes.add_table(len(kpi_rows) + 1, 3, Inches(6.62), Inches(1.12), Inches(6.25), Inches(4.15)).table
    for ci, cw in enumerate([1.65, 2.35, 2.25]):
        t12.columns[ci].width = Inches(cw)
    for ci, htxt in enumerate(kpi_headers):
        c = t12.cell(0, ci)
        c.fill.solid()
        c.fill.fore_color.rgb = TEAL
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
        r = c.text_frame.paragraphs[0].add_run()
        r.text = htxt
        r.font.name = "Segoe UI"
        r.font.size = Pt(9.5)
        r.font.bold = True
        r.font.color.rgb = WHITE
    for ri, rvals in enumerate(kpi_rows, start=1):
        for ci, val in enumerate(rvals):
            c = t12.cell(ri, ci)
            c.fill.solid()
            c.fill.fore_color.rgb = WHITE if ri % 2 == 1 else TEAL_TINT
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            r = c.text_frame.paragraphs[0].add_run()
            r.text = val
            r.font.name = "Segoe UI"
            r.font.size = Pt(9.0)
            r.font.bold = ci == 0
            r.font.color.rgb = NAVY if ci == 0 else SLATE

    _add_rect(s12, 6.62, 5.48, 6.25, 1.42, NAVY)
    _add_textbox(
        s12, 6.80, 5.60, 5.90, 1.20,
        "Bottom Line: maurices doesn't need to reinvent who she is. By trimming unproductive style bloat, backing high-velocity 0–24 Denim & Outfit heroes, and making Free Styling famous, maurices wins 'Liv' today and protects hometown loyalty tomorrow.",
        size=10.5, color=WHITE, bold=True,
    )
    _set_notes(
        s12,
        "Finally, we de-risk execution with a rigorous 2-cell matched-market store test and a 10% CRM holdout—measuring incremental Sales per Style, Store Sell-Through, NTF under-51 share, and a hard non-erosion guardrail on 45+ Protect retention. Thank you—we'd love your questions!",
    )

    prs.save(str(out_path))
    return out_path
