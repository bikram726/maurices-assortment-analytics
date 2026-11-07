# maurices Assortment & "Liv" (35–44) Growth Analytics Studio

100% **Local Offline** Python + PowerPoint + Streamlit analytics suite built specifically around the **3-file maurices Case Competition schema** (`product_file_masked.csv`, `time_file.csv`, `dept_class_subclass_age.csv`) and all 10 data dictionary caveats.

> **Competition Rule Compliance (`ZERO AI Upload`):**
> - Runs **100% locally offline** on your laptop (`127.0.0.1`). Zero network requests, zero cloud APIs, and Streamlit usage telemetry disabled in [`.streamlit/config.toml`](.streamlit/config.toml).
> - [`.gitignore`](.gitignore) blocks `*.csv`, `*.pptx`, `*.pdf`, `*.docx`, `data/`, and `slides_out/` so competition files can never accidentally be committed to Git.
> - Remember to delete all competition CSVs and generated outputs from personal devices once Saturday presentations conclude.

---

## 60-Second Quickstart (For Your Local Machine)

```bash
git clone https://github.com/bikram726/maurices-assortment-analytics.git
cd maurices-assortment-analytics
pip install -r requirements.txt
```

### Step 1: Point to Your 3 Local CSVs (or Drop into `./data/`)
Place the three files in `./data/` (or leave them in `~/Downloads` — `app.py` auto-detects them locally):
- `product_file_masked.csv`
- `time_file.csv`
- `dept_class_subclass_age.csv`

*(Want to test with synthetic mock data? Run `python app.py --demo`.)*

### Step 2A: Generate the Complete 12-Slide `.pptx` Deck + 7 Widescreen Charts + Scorecards
```bash
python app.py --data-dir ./data --out-dir ./slides_out/live_case
```
Outputs written locally to `slides_out/live_case/`:
1. **`maurices_Assortment_Strategy_Deck.pptx`** — **Complete 12-Slide Editable 16:9 PowerPoint Deck** (KPI cards, embedded 240-DPI charts, native subclass action table, CMO/CRM activation funnel, Enterprise A/B test roadmap, and full **Presenter Speaker Notes** on all 12 slides)
2. `01_over_vs_under_assorted_matrix.png` — **Class Over-Assorted Bloat vs. Under-Invested Winners**
3. `02_dual_mandate_scorecard.png` — **Success Criteria #1 & #2 Subclass Quadrant**
4. `03_liv_vs_protect_age_bridge.png` — **Winning "Liv" (35–44) Without Losing "Protect" (45+)**
5. `04_denim_bet_deep_dive.png` — **Testing the Denim Bet** (Productivity, `NTF <51 %`, and `Online Omnichannel Share %`)
6. `05_store_inventory_velocity.png` — **Store Sell-Through vs. Depth per Choice** (`STORE` only, flagging `>100%` mid-week restock velocity)
7. `06_fiscal_seasonality_omnichannel.png` — **4-5-4 Fiscal Quarter Seasonality (`Q1 Aug–Oct` to `Q4 May–Jul`) & YoY Growth by Action Tier**
8. `07_otb_reallocation_blueprint.png` — **OTB Style Share vs. Sales Share Reallocation Blueprint**
9. `assortment_recommendations_indexed.csv` & `department_scorecard_indexed.csv` — Masked-safe ranked scorecards (`Index` & `% Share` only—never raw masked dollars)
10. `slide_narrative_brief.md` — Ready-to-present talking points tailored for CMO, Marketing Analytics, CRM, and Enterprise Analytics judges

### Step 2B: Launch the Interactive Local Browser Studio
```bash
streamlit run app.py
```
Opens on `http://127.0.0.1:8501` with 1-click `.pptx` download, Department/Tier filters, Denim Bet deep-dive, Judge Presenter Script, and an optional offline **[PyGWalker](https://github.com/Kanaries/pygwalker)** Tableau-style drag-and-drop tab (`pip install pygwalker`).

---

## Every Data Dictionary Caveat Handled Automatically (`engine.py`)

| Schema Trap in Brief | How `engine.py` Solves It |
|---|---|
| **Composite Join & Type Mismatch** | Normalizes zero-padded text IDs (`"004"`) and integer IDs (`4`) across `dept_idnt`, `class_idnt`, `sbclass_idnt` and joins strictly on `(dept, class, subclass)`. |
| **Duplicate Subclass Names** | Keys every aggregation on composite IDs so shared names (e.g., two `"FASHION CARDI"` subclasses) never merge, appending `[#ID]` on charts. |
| **48 Text Percentage Age Columns** | Strips `"%"` across all `TOTAL`, `NTF`, and `EXISTING` age bands (`18`–`95`), guards blank rows, and maps cohorts (`<51`, `<40`, `Liv 35–44`, `Protect 45+`). |
| **Unweighted Age Average Trap** | Weights all age rollups strictly by positive `net_sales_units` (`np.average(..., weights=units)`). |
| **Weekly SOH Snapshot Trap** | Averages `soh_units` across active `STORE` weeks only (never sums across weeks or channels; isolates `~14%` seasonal null SOH rows). |
| **Store-Only Sell-Through & `>100%` Restocks** | Restricts sell-through and `depth_per_choice` to `STORE` rows, using **median sell-through** + `% of weeks >100%` fast-turn signal. |
| **No Cost/Margin & Masked Dollars** | Measures profitability via **Assortment Productivity** (`Sales/Style-Week Index = 100`, `Sell-Through`, `Depth/Choice`) and reports `% Share` & `Index`. |
