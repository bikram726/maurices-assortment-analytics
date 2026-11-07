"""Local Offline CLI + Interactive Streamlit Studio for maurices Assortment Analytics.

Usage (100% Local — Zero Data Uploaded Anywhere):
  1) Batch generate all 6 300-DPI slide visuals + CSV + talking points:
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
            print(f"[DEMO] Generated synthetic schema-accurate CSVs in {demo_dir}")
        else:
            print(
                f"ERROR: Could not find product_file_masked.csv, time_file.csv, and "
                f"dept_class_subclass_age.csv inside '{data_dir}'.\n"
                f"Drop the 3 local CSVs into '{data_dir}' (stays 100% offline & gitignored), "
                f"or pass --demo to test with synthetic data."
            )
            return 1

    analysis = load_and_analyze(resolved[0], resolved[1], resolved[2], denim_regex=args.denim_regex)
    outputs = export_full_pack(analysis, out_dir, demo_mode=demo_mode)

    d = analysis["diagnostics"]
    print(f"\n=== Assortment Analysis Complete (100% Local Offline) ===")
    print(f"Rows analyzed: {d['product_rows']:,} | Fiscal weeks: {d['weeks_count']} | Subclasses joined: {d['joined_subclasses']}")
    print(f"Duplicate descriptions separated: {d['duplicate_descriptions_disambiguated']}")
    print(f"Store missing SOH: {d['store_missing_soh_pct']}% | Store >100% sell-through weeks: {d['store_st_over_100_pct']}%")
    print(f"Generated {len(outputs)} slide-ready artifacts in: {out_dir.resolve()}")
    for k, p in outputs.items():
        print(f"  - {k}: {p.name}")
    return 0


def run_streamlit_app() -> None:
    import pandas as pd
    import streamlit as st

    st.set_page_config(page_title="maurices Assortment & 'Liv' Growth Analyzer (Offline)", page_icon="🛍️", layout="wide")
    st.title("🛍️ maurices Assortment Productivity & 'Liv' (35–44) Growth Studio")
    st.caption(
        "🔒 **100% Local Offline Execution** — Reads local CSVs on `127.0.0.1` with zero external API or AI calls. "
        "All monetary outputs are expressed as **% Share** and **Productivity Index (`100 = Chain Avg`)** per case rules."
    )

    st.sidebar.header("1. Local Data Source")
    default_dir = str(ROOT / "data")
    folder_str = st.sidebar.text_input("Local CSV Folder Path", value=default_dir)
    denim_rx = st.sidebar.text_input("Denim Keyword Filter (Regex)", value=r"\b(?:denim|jean|jeans|jegging)\b")

    data_path = Path(folder_str)
    resolved = _resolve_csv_paths(data_path)
    demo_mode = False

    if resolved is None:
        st.sidebar.warning("3 competition CSVs not found in `data/` yet — showing **Synthetic Demo Mode**.")
        demo_mode = True
        demo_dir = ROOT / "data" / "_synthetic_demo"
        if not _resolve_csv_paths(demo_dir):
            generate_synthetic_csvs(demo_dir)
        resolved = _resolve_csv_paths(demo_dir)
    else:
        st.sidebar.success("✅ Loaded real local CSVs from disk (offline).")

    @st.cache_data(show_spinner="Running caveat-safe composite joins & volume-weighted rollups...")
    def _cached_run(p_str: str, t_str: str, c_str: str, mtime: float, rx: str):
        return load_and_analyze(p_str, t_str, c_str, denim_regex=rx)

    mtime_sig = sum(p.stat().st_mtime for p in resolved)
    analysis = _cached_run(str(resolved[0]), str(resolved[1]), str(resolved[2]), mtime_sig, denim_rx)
    out_dir = ROOT / "slides_out"
    pack = export_full_pack(analysis, out_dir, demo_mode=demo_mode)

    d = analysis["diagnostics"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Subclasses Joined", f"{d['joined_subclasses']:,}", f"{d['weeks_count']} fiscal wks")
    c2.metric("NTF Buyers < Age 51", f"{100*d['chain_weighted_ntf_under_51']:.1f}%", f"{100*(d['chain_weighted_ntf_under_51']-d['chain_weighted_under_51']):+.1f} pts vs Total")
    c3.metric("'Liv' (35–44) NTF Share", f"{100*d['chain_weighted_liv_35_44']:.1f}%", "Primary Grow Cohort")
    c4.metric("Online Sales Share", f"{100*d['chain_online_share']:.1f}%", "Liv = 25% Omnichannel")
    c5.metric("Denim Subclasses", f"{d['denim_subclass_count']}", f"Missing SOH: {d['store_missing_soh_pct']}%")

    tabs = st.tabs([
        "📊 6 Slide-Ready Charts",
        "👖 The Denim Bet",
        "🗂️ Subclass Action Matrix",
        "📝 CMO & Analytics Judge Brief",
        "🔬 Optional PyGWalker Drag & Drop",
    ])

    with tabs[0]:
        st.subheader("300-DPI Widescreen Charts (Saved in `slides_out/` for PowerPoint / Google Slides)")
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
        depts = ["ALL"] + sorted(indexed_df["department"].unique().tolist())
        sel_dept = st.selectbox("Filter Department", depts)
        view_df = indexed_df if sel_dept == "ALL" else indexed_df[indexed_df["department"] == sel_dept]
        st.dataframe(view_df, use_container_width=True, height=480)
        st.download_button(
            "⬇ Download Masked-Safe Subclass Scorecard (CSV)",
            data=pack["recommendations_csv"].read_bytes(),
            file_name="assortment_recommendations_indexed.csv",
            mime="text/csv",
        )

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
    # Detect whether invoked via `streamlit run app.py` or `python app.py`
    if "streamlit" in sys.modules:
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            if get_script_run_ctx() is not None:
                run_streamlit_app()
                sys.exit(0)
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="maurices Local Offline Assortment Analyzer & Slide Chart Generator")
    parser.add_argument("--data-dir", default=str(ROOT / "data"), help="Folder containing the 3 local CSV files")
    parser.add_argument("--out-dir", default=str(ROOT / "slides_out"), help="Output folder for 300-DPI PNGs & brief")
    parser.add_argument("--denim-regex", default=r"\b(?:denim|jean|jeans|jegging)\b", help="Regex for Denim subclasses")
    parser.add_argument("--demo", action="store_true", help="Run on synthetic schema-accurate mock data")
    sys.exit(run_cli(parser.parse_args()))
