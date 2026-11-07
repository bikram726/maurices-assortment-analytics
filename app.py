"""Local Offline CLI + Interactive Streamlit Studio for maurices Assortment Analytics.

Usage (100% Local — Zero Data Uploaded Anywhere):
  1) Batch generate 12-slide .pptx deck + 7 high-DPI charts + CSV scorecards + brief:
       python app.py --data-dir ./data --out-dir ./slides_out
     (Or test immediately with synthetic mock data: `python app.py --demo`)

  2) Launch interactive local browser explorer (http://127.0.0.1:8501):
       streamlit run app.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from charts import export_full_pack
from deck_builder import build_presentation_deck
from engine import load_and_analyze
from mock_data import generate_synthetic_csvs

ROOT = Path(__file__).resolve().parent


def _resolve_csv_paths(data_dir: Path) -> tuple[Path, Path, Path] | None:
    p = data_dir / "product_file_masked.csv"
    t = data_dir / "time_file.csv"
    c = data_dir / "dept_class_subclass_age.csv"
    if p.exists() and t.exists() and c.exists():
        return p, t, c
    return None


def _default_local_dir() -> Path:
    """Prefer ./data if populated, else ~/Downloads if the 3 CSVs exist there locally."""
    local_data = ROOT / "data"
    if _resolve_csv_paths(local_data) is not None:
        return local_data
    dl = Path.home() / "Downloads"
    if _resolve_csv_paths(dl) is not None:
        return dl
    return local_data


def run_cli(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    demo_mode = bool(args.demo)

    resolved = _resolve_csv_paths(data_dir)
    if resolved is None:
        if demo_mode:
            demo_dir = ROOT / "data" / "_synthetic_demo"
            paths = generate_synthetic_csvs(demo_dir)
            resolved = (paths["product"], paths["time"], paths["customer"])
            if not args.quiet_privacy:
                print(f"[DEMO] Generated synthetic schema-accurate CSVs in {demo_dir}")
        else:
            print(
                f"ERROR: Could not find product_file_masked.csv, time_file.csv, and "
                f"dept_class_subclass_age.csv inside '{data_dir}'."
            )
            return 1

    analysis = load_and_analyze(resolved[0], resolved[1], resolved[2], denim_regex=args.denim_regex)
    outputs = export_full_pack(analysis, out_dir, demo_mode=demo_mode)
    pptx_path = build_presentation_deck(
        analysis,
        outputs,
        out_dir / "maurices_Assortment_Strategy_Deck.pptx",
        demo_mode=demo_mode,
    )
    outputs["pptx_deck"] = pptx_path

    if args.quiet_privacy:
        # Strict competition privacy mode: emit zero dataset figures or category strings to stdout
        print("STATUS=SUCCESS_LOCAL_OFFLINE")
        print(f"ARTIFACTS_WRITTEN={len(outputs)}")
        print(f"OUT_DIR={out_dir.resolve()}")
        for k, p in outputs.items():
            print(f"FILE_{k.upper()}={p.name} ({p.stat().st_size} bytes)")
        return 0

    d = analysis["diagnostics"]
    print("\n=== Assortment Analysis & 12-Slide Deck Complete (100% Local Offline) ===")
    print(f"Rows analyzed: {d['product_rows']:,} | Fiscal weeks: {d['weeks_count']} | Subclasses joined: {d['joined_subclasses']:,}")
    print(f"Duplicate descriptions separated ({d['duplicate_count']}): {d['duplicate_descriptions_disambiguated'][:6]}")
    print(f"Store missing SOH: {d['store_missing_soh_pct']}% | Store >100% sell-through weeks: {d['store_st_over_100_pct']}%")
    print(f"Generated {len(outputs)} slide-ready artifacts in: {out_dir.resolve()}")
    for k, p in outputs.items():
        print(f"  - {k}: {p.name}")
    return 0


def run_streamlit_app() -> None:
    import pandas as pd
    import streamlit as st

    st.set_page_config(page_title="maurices Assortment & 'Liv' Growth Studio (Offline)", page_icon="🛍️", layout="wide")
    st.title("🛍️ maurices Assortment Productivity & 'Liv' (35–44) Growth Studio")
    st.caption(
        "🔒 **100% Local Offline Execution** — Reads local CSVs on `127.0.0.1` with zero external API or AI calls. "
        "All monetary outputs are expressed as **% Share** and **Productivity Index (`100 = Chain Avg`)** per case rules."
    )

    st.sidebar.header("1. Local Data Source")
    default_dir = str(_default_local_dir())
    folder_str = st.sidebar.text_input("Local CSV Folder Path", value=default_dir)
    denim_rx = st.sidebar.text_input("Denim Keyword Filter (Regex)", value=r"\b(?:denim|dnm|jean|jeans|jns|jegging|jeggings|jeg)\b")

    data_path = Path(folder_str)
    resolved = _resolve_csv_paths(data_path)
    demo_mode = False

    if resolved is None:
        st.sidebar.warning("3 competition CSVs not found in selected folder — showing **Synthetic Demo Mode**.")
        demo_mode = True
        demo_dir = ROOT / "data" / "_synthetic_demo"
        if not _resolve_csv_paths(demo_dir):
            generate_synthetic_csvs(demo_dir)
        resolved = _resolve_csv_paths(demo_dir)
    else:
        st.sidebar.success(f"✅ Loaded real local CSVs offline from `{data_path}`.")

    @st.cache_data(show_spinner="Running caveat-safe composite joins, rollups & building 12-slide PPTX...")
    def _cached_run(p_str: str, t_str: str, c_str: str, mtime: float, rx: str, is_demo: bool):
        res = load_and_analyze(p_str, t_str, c_str, denim_regex=rx)
        target_sub = "demo_preview" if is_demo else "live_case"
        out_folder = ROOT / "slides_out" / target_sub
        pk = export_full_pack(res, out_folder, demo_mode=is_demo)
        pk["pptx_deck"] = build_presentation_deck(
            res, pk, out_folder / "maurices_Assortment_Strategy_Deck.pptx", demo_mode=is_demo
        )
        return res, pk

    mtime_sig = sum(p.stat().st_mtime for p in resolved)
    analysis, pack = _cached_run(str(resolved[0]), str(resolved[1]), str(resolved[2]), mtime_sig, denim_rx, demo_mode)

    st.sidebar.divider()
    st.sidebar.download_button(
        "📊 Download 12-Slide Strategy Deck (.pptx)",
        data=pack["pptx_deck"].read_bytes(),
        file_name="maurices_Assortment_Strategy_Deck.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        type="primary",
        use_container_width=True,
    )
    st.sidebar.download_button(
        "📥 Download Subclass Scorecard (.csv)",
        data=pack["recommendations_csv"].read_bytes(),
        file_name="assortment_recommendations_indexed.csv",
        mime="text/csv",
        use_container_width=True,
    )

    d = analysis["diagnostics"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Subclasses Audited", f"{d['total_product_subclasses']:,}", f"{d['joined_subclasses']:,} age-matched")
    c2.metric("NTF Buyers < Age 51", f"{100*d['chain_weighted_ntf_under_51']:.1f}%", f"{100*(d['chain_weighted_ntf_under_51']-d['chain_weighted_under_51']):+.1f} pts vs Total")
    c3.metric("'Liv' (35–44) NTF Share", f"{100*d['chain_weighted_liv_35_44']:.1f}%", "Primary Grow Cohort")
    c4.metric("Online Sales Share", f"{100*d['chain_online_share']:.1f}%", "Liv = 25% Omnichannel")
    c5.metric("Denim Footprint", f"{d['denim_subclass_count']} subs", f"{100*d['denim_sales_share']:.1f}% of Chain Sales")

    tabs = st.tabs([
        "📊 7 Slide-Ready Charts",
        "👖 The Denim Bet",
        "🗂️ Subclass & Dept Scorecards",
        "📝 CMO & Judge Presenter Script",
        "🔬 Optional PyGWalker Drag & Drop",
    ])

    with tabs[0]:
        st.subheader(f"High-DPI 16:9 Visuals + Editable PowerPoint Saved in `{pack['pptx_deck'].parent}`")
        st.image(str(pack["slide_07"]), use_container_width=True)
        col_a, col_b = st.columns(2)
        col_a.image(str(pack["slide_01"]), use_container_width=True)
        col_b.image(str(pack["slide_02"]), use_container_width=True)
        col_c, col_d = st.columns(2)
        col_c.image(str(pack["slide_03"]), use_container_width=True)
        col_d.image(str(pack["slide_04"]), use_container_width=True)
        col_e, col_f = st.columns(2)
        col_e.image(str(pack["slide_05"]), use_container_width=True)
        col_f.image(str(pack["slide_06"]), use_container_width=True)

    with tabs[1]:
        st.image(str(pack["slide_04"]), use_container_width=True)
        indexed_df = pd.read_csv(pack["recommendations_csv"])
        st.dataframe(indexed_df[indexed_df["is_denim"]], use_container_width=True)

    with tabs[2]:
        indexed_df = pd.read_csv(pack["recommendations_csv"])
        dept_df = pd.read_csv(pack["departments_csv"])
        st.markdown("#### Department Summary (Unit-Volume-Weighted Age Rollups)")
        st.dataframe(dept_df, use_container_width=True)
        st.markdown("#### Subclass Action Matrix (Composite-ID Safe)")
        col_f1, col_f2 = st.columns(2)
        depts = ["ALL"] + sorted(indexed_df["department"].dropna().unique().tolist())
        tiers_l = ["ALL"] + sorted(indexed_df["action_tier"].dropna().unique().tolist())
        sel_dept = col_f1.selectbox("Filter Department", depts)
        sel_tier = col_f2.selectbox("Filter Strategic Action Tier", tiers_l)
        view_df = indexed_df.copy()
        if sel_dept != "ALL":
            view_df = view_df[view_df["department"] == sel_dept]
        if sel_tier != "ALL":
            view_df = view_df[view_df["action_tier"] == sel_tier]
        st.dataframe(view_df, use_container_width=True, height=460)

    with tabs[3]:
        st.markdown(pack["brief_md"].read_text(encoding="utf-8"))

    with tabs[4]:
        try:
            from pygwalker.api.streamlit import StreamlitRenderer
            indexed_df = pd.read_csv(pack["recommendations_csv"])
            StreamlitRenderer(indexed_df, use_kernel_calc=True).explorer()
        except ImportError:
            st.info("Optional Tableau-style drag & drop: run `pip install pygwalker` locally to enable this tab offline.")


if __name__ == "__main__":
    if "streamlit" in sys.modules:
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            if get_script_run_ctx() is not None:
                run_streamlit_app()
                sys.exit(0)
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="maurices Local Offline Assortment Analyzer & 12-Slide PPTX Generator")
    parser.add_argument("--data-dir", default=str(_default_local_dir()), help="Folder containing the 3 local CSV files")
    parser.add_argument("--out-dir", default=str(ROOT / "slides_out" / "live_case"), help="Output folder for PPTX, PNGs & brief")
    parser.add_argument("--denim-regex", default=r"\b(?:denim|dnm|jean|jeans|jns|jegging|jeggings|jeg)\b", help="Regex for Denim subclasses")
    parser.add_argument("--demo", action="store_true", help="Run on synthetic schema-accurate mock data")
    parser.add_argument("--quiet-privacy", action="store_true", help="Print only file status codes (zero dataset metrics to stdout)")
    sys.exit(run_cli(parser.parse_args()))
