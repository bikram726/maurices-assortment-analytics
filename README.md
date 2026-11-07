# maurices Assortment & "Liv" (35–44) Growth Analytics Studio

100% **Local Offline** Python + Streamlit analytics & 300-DPI slide visual generator built specifically around the **3-file maurices Case Competition schema** and all 10 data dictionary caveats.

> **Competition Rule Compliance (`ZERO AI Upload`):**
> - Runs **100% locally offline** on your laptop (`127.0.0.1`). Zero network requests, zero cloud APIs, and Streamlit usage telemetry disabled in [`.streamlit/config.toml`](.streamlit/config.toml).
> - [`.gitignore`](.gitignore) blocks `*.csv`, `data/`, and `slides_out/` so competition files can never accidentally be committed to Git.
> - Remember to delete all competition CSVs and generated outputs from personal devices once Saturday presentations conclude.

---

## 60-Second Quickstart (For Your Local Machine)

```bash
git clone https://github.com/bikram726/maurices-assortment-analytics.git
cd maurices-assortment-analytics
pip install -r requirements.txt
```

### Step 1: Drop the 3 Local CSVs into `./data/`
Create a `data/` folder inside the repo and place the three files locally:
- `data/product_file_masked.csv`
- `data/time_file.csv`
- `data/dept_class_subclass_age.csv`

*(Want to test before copying the files? Run `python app.py --demo` to generate synthetic schema-accurate mock data.)*

### Step 2A: Generate All 6 Widescreen (300-DPI) Slide Charts + Scorecard in One Command
```bash
python app.py --data-dir ./data --out-dir ./slides_out
```
Outputs written to `slides_out/`:
1. `01_over_vs_under_assorted_matrix.png` — **Over-Assorted Bloat vs. Under-Invested Winners** (`Style Share %` vs. `$/Style Productivity Index = 100`)
2. `02_dual_mandate_scorecard.png` — **Success Criteria #1 & #2 Quadrant** (`Volume + $/Style` vs. `Younger <51 NTF Acquisition`)
3. `03_liv_vs_protect_age_bridge.png` — **Winning "Liv" (35–44) Without Losing "Protect" (45+)** (unit-volume-weighted NTF vs. Existing age mix)
4. `04_denim_bet_deep_dive.png` — **Testing the Denim Bet** (Denim subclass productivity, `NTF <51 %`, and `Online Omnichannel Share %`)
5. `05_store_inventory_velocity.png` — **Store Sell-Through vs. Depth per Choice** (`STORE` only, flagging `>100%` mid-week restock velocity)
6. `06_fiscal_seasonality_omnichannel.png` — **4-5-4 Fiscal Quarter Seasonality (`Q1 Aug–Oct` to `Q4 May–Jul`) & YoY Growth by Action Tier**
7. `assortment_recommendations_indexed.csv` — Masked-safe ranked table of all subclasses (`Index` & `% Share` only—never raw masked dollars)
8. `slide_narrative_brief.md` — Ready-to-present talking points tailored for CMO, Marketing Analytics, CRM, and Enterprise Analytics judges

### Step 2B: Launch the Interactive Local Browser Dashboard
```bash
streamlit run app.py
```
Opens on `http://127.0.0.1:8501` with Department filters, Denim Bet deep-dive, Subclass Action Matrix, Judge Brief, and an optional offline **[PyGWalker](https://github.com/Kanaries/pygwalker)** Tableau-style drag-and-drop tab (`pip install pygwalker`).

---

## Every Data Dictionary Caveat Handled Automatically (`engine.py`)

| Schema Trap in Brief | How `engine.py` Solves It |
|---|---|
| **Composite Join & Type Mismatch** | Normalizes zero-padded text IDs (`"004"`) and integer IDs (`4`) and joins strictly on `(dept, class, subclass)`. |
| **Duplicate Subclass Names** | Keys every aggregation on composite IDs so shared names (e.g., two `"FASHION CARDI"` subclasses) never merge, appending `[#ID]` on charts. |
| **48 Text Percentage Age Columns** | Strips `"%"` across all `TOTAL`, `NTF`, and `EXISTING` age bands (`18`–`95`) and maps cohorts (`<51`, `<40`, `Liv 35–44`, `Protect 45+`). |
| **Unweighted Age Average Trap** | Weights all age rollups strictly by `net_sales_units` (`np.average(..., weights=units)`). |
| **Weekly SOH Snapshot Trap** | Averages `soh_units` across active `STORE` weeks only (never sums across weeks or channels; isolates `~14%` seasonal null SOH rows). |
| **Store-Only Sell-Through & `>100%` Restocks** | Restricts sell-through and `depth_per_choice` to `STORE` rows, using **median sell-through** + `% of weeks >100%` fast-turn signal. |
| **No Cost/Margin & Masked Dollars** | Measures profitability via **Assortment Productivity** (`$/Style Index`, `Sell-Through`, `Depth/Choice`) and reports `% Share` & `Index = 100`. |

---

## Companion Open-Source Local Visualization Repos (100% Offline)
- **[Kanaries/pygwalker](https://github.com/Kanaries/pygwalker)** — Turns the exported `assortment_recommendations_indexed.csv` into an offline Tableau-like drag-and-drop UI (`use_kernel_calc=True`, built into Tab 5 of `app.py`).
- **[man-group/dtale](https://github.com/man-group/dtale)** — Local browser GUI for ad-hoc Pandas pivoting and correlation checks (`dtale.show(df)`).
- **[marimo-team/marimo](https://github.com/marimo-team/marimo)** — Reactive local SQL + Python notebook if you want custom DuckDB queries over the 3 CSVs.
