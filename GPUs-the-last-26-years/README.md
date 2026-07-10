# GPUs the last 26 years

A comprehensive Data Science project analyzing consumer desktop GPU pricing affordability over ~26 years (2000–2025), with a strong focus on **inflation-adjusted price analysis**.

## Project Goal
Determine historical affordability of GPUs:
- Which year was the **most expensive** to buy a GPU (inflation-adjusted)?
- Which year was the **most affordable**?
- Broader trends in value, performance-per-dollar, manufacturer pricing, and more.

## Dataset
- Source: Curated `GPU-26-Years.csv` (118 major consumer desktop discrete GPU launches: NVIDIA GeForce, AMD Radeon, Intel Arc).
- Includes MSRP (launch), detailed specs (memory, cores, TDP, process node, TFLOPS where applicable), stock prices at launch, etc.
- Data covers 2000 to 2025.

See `data/GPU-26-Years.csv` and original generation notes in sibling folders for provenance.

## Key Analyses & KPIs Included
- **Inflation Adjustment**: All prices normalized to 2025 USD using US CPI-U annual averages (BLS via Minneapolis Fed).
- Median / Mean / Flagship real prices by year → identify cheapest & most expensive years.
- Price per GB VRAM trends.
- Performance-per-dollar (TFLOPS / adjusted price) for modern era.
- Manufacturer pricing analysis (NVIDIA premium vs AMD).
- Real price CAGR, YoY changes.
- Value segments, outliers, EDA visualizations.
- Simple predictive modeling (price from specs).
- Actionable insights & recommendations.

## How to Run
```powershell
cd "GPUs-the-last-26-years"

# Create venv (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# Launch Jupyter
jupyter notebook GPUs_the_last_26_years.ipynb
# or: jupyter lab
```

## Requirements
See `requirements.txt` (pandas, numpy, matplotlib, seaborn, jupyter, scikit-learn, etc.)

## Interactive HUD website
Polished **Modern HUD** presentation (filters, charts, Q&A) lives at:

```text
docs/gpu-26-years/index.html
```

Double-click to open via `file://` (classic scripts; dataset embedded in `js/gpu-dataset.js`).  
Regenerate web data after CSV changes:

```powershell
python GPUs-the-last-26-years/export_web_data.py
python GPUs-the-last-26-years/tests/test_gpu_logic.py
```

## Structure
- `GPUs_the_last_26_years.ipynb` — Full end-to-end Data Science notebook (EDA → Inflation KPIs → Modeling → Conclusions)
- `data/GPU-26-Years.csv` — Analysis dataset
- `export_web_data.py` — Export JSON + file://-safe `gpu-dataset.js` for the HUD site
- `tests/test_gpu_logic.py` — Unit tests against shipped `docs/gpu-26-years/js/gpu-logic.js`
- `README.md` / `requirements.txt`

## Notes / Limitations
- MSRP = manufacturer launch reference pricing (not street/used/partner pricing).
- Not every SKU; curated representative models per generation.
- Early years (pre ~2010) have limited "performance" metrics (no TFLOPS, Tensor/RT cores etc.).
- Inflation uses annual average CPI; for precision one could use monthly but yearly is appropriate here.
- 2026 data partial (as of mid-2026).

## License / Attribution
Dataset compiled from public sources (Wikipedia GPU lists, TechPowerUp, NVIDIA/AMD announcements, historical reviews). For educational / analysis use.

---

**Run the notebook to see full tables, charts, and the definitive "most expensive / affordable" years!**
