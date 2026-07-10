# New-GPU Data / GPU-26-Years.csv

Detailed dataset of **consumer desktop discrete GPUs** spanning ~26 years (2000 – 2025/2026 launches).

## Contents
- `GPU-26-Years.csv` — 118 curated rows of major + popular consumer models.
- `GPU-26-Years.csv.sources.txt` — Provenance and sources used.
- `generate_gpu_26_years.py` — Python generator script (static DATA + yfinance stock lookup).

## Scope
- **Consumer desktop discrete only**: GeForce (GT/GTX/RTX), Radeon (HD/R/RX), and Intel Arc Alchemist desktop cards.
- Includes flagship, Ti, Super, XT, GRE, and high-volume mid-range SKUs across generations.
- Starts ~2000 (GeForce 2 / early Radeon) to cover the "last 26 years" from 2026.
- **Excludes**: mobile, integrated, professional (Quadro/RTX A / FirePro / Radeon Pro), server/datacenter, pre-3D accelerators.

## Columns (29 total, as detailed as practical)
Released_Year, Released_Month, Manufacturer, OEM, MSRP_USD, GPU_Name, Architecture, Codename,
Memory_GB, Memory_Type, Memory_Bus_Width, Memory_Bandwidth_GBs,
Base_Clock_MHz, Boost_Clock_MHz,
CUDA_Cores, Stream_Processors, Tensor_Cores, RT_Cores,
TMUs, ROPs, TDP_W, Process_nm, Transistors_M, Die_Size_mm2, TFLOPS_FP32, PCIe,
Stock_Price, Stock_Date, Notes

Many fields are blank/N/A for pre-2006/2008 cards where the concept did not exist (Tensor/RT cores, TFLOPS, etc.).

## Data Sources (see .sources.txt for full)
- Wikipedia "List of Nvidia graphics processing units" + "List of AMD graphics processing units" + dedicated RTX 50 / RX 9000 pages (primary for dates, arch, core counts, memory config, clocks, transistors, die size).
- NVIDIA / AMD official product pages and spec sheets (MSRP, power, latest Blackwell / RDNA 4).
- TechPowerUp GPU Database (cross-validation).
- Historical reviews / launch articles for older MSRPs.

Stock prices: Yahoo Finance via yfinance at generation time (split-adjusted close on/near mid-month release target).

## How to Regenerate
```powershell
cd "New-GPU Data"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r ../GPU\ History/requirements.txt   # or: pip install yfinance pandas
python generate_gpu_26_years.py
```

Edit the `DATA` list in the script to add new 2026+ releases or missed models, then re-run.

## Notes / Limitations
- MSRP = manufacturer launch suggested retail (Reference / Founders Edition where distinguished). Actual street prices and AIB partner pricing varied.
- Not exhaustive of every SKU ever sold (hundreds of partner variants exist for each core model).
- Memory values normalized to GB (decimal).
- Early cards have approximate or mid-month dates for stock correlation.
- TFLOPS and some derived numbers are theoretical peak FP32.
- Intel Arc entries included as the primary 3rd-party consumer desktop discrete competitor post-2022.

Use for historical trend analysis, visualization, ML feature engineering, etc.
