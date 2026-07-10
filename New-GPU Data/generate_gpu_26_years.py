#!/usr/bin/env python3
"""
generate_gpu_26_years.py

Generates GPU-26-Years.csv with detailed data for consumer desktop discrete GPUs
(NVIDIA GeForce, AMD Radeon, Intel Arc where applicable) spanning the last ~26 years (2000-2026).

Scope:
- Consumer desktop discrete GPUs only (add-in board / retail gaming/professional-adjacent consumer cards).
- All major models + significant variants (Ti, Super, XT, GRE, etc.) from each generation.
- Detailed specs where available from Wikipedia, TechPowerUp, official announcements, reviews.
- MSRP: launch MSRPs (primarily reference/FE where distinguished; typical AIB launch often similar or slightly higher).
- Not every single AIB partner SKU (e.g. no 50 variants of "ASUS Strix RTX 4090").

Data compiled via web research (Wikipedia List of Nvidia/AMD GPUs, GeForce RTX 50 / Radeon RX 9000 wiki pages,
TechPowerUp GPU Database references, official NVIDIA/AMD announcements, contemporaneous reviews).
Stock prices via yfinance (split-adjusted).

Columns are designed to be rich for analysis:
- Includes legacy fields + modern ones (Tensor/RT cores, bandwidth, transistors, TFLOPS, etc.)
- Pre-unified shader eras have N/A or blank for advanced fields.
- Memory_GB normalized to decimal GB.

Usage:
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  python generate_gpu_26_years.py [--output GPU-26-Years.csv]

Output: GPU-26-Years.csv + GPU-26-Years.csv.sources.txt
"""

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

# =============================================================================
# COMPREHENSIVE DATA - Consumer Desktop GPUs ~2000 to mid-2026
# Focused on GeForce (GT/GTX/RTX), Radeon (Radeon HD/R/RX), and key Intel Arc desktop.
# One entry per distinct consumer model/SKU family (major variants included).
# Sources used for research: Wikipedia (primary specs/dates/arch), TechPowerUp,
# NVIDIA/AMD launch pages, historical reviews (Anandtech, Tom's Hardware, etc.),
# Internet Archive for older MSRPs where needed.
# All data statically entered after searches; no runtime scraping.
# =============================================================================

# Data dict keys (flexible):
# year, month, manufacturer, gpu_name, architecture, codename (opt),
# memory_gb, memory_type, memory_bus_width (str e.g. "384-bit" or 384),
# boost_clock_mhz, base_clock_mhz (opt), tdp_w, process_nm,
# msrp, oem="Reference",
# cuda_cores (NVIDIA), stream_processors (AMD), compute_units (opt),
# tensor_cores, rt_cores,
# tmus, rops,
# memory_bandwidth_gbs, transistors_m, die_size_mm2, tflops_fp32,
# pcie (opt), notes (opt)

DATA = [
    # ===================== 2000-2004: GeForce 2/3/4 + early Radeon =====================
    # GeForce 2 (2000)
    {"year": 2000, "month": 4, "manufacturer": "NVIDIA", "gpu_name": "GeForce 2 GTS", "architecture": "NV15", "codename": "NV15",
     "memory_gb": 0.032, "memory_type": "DDR", "memory_bus_width": "128-bit", "base_clock_mhz": 200, "boost_clock_mhz": 200,
     "tdp_w": 25, "process_nm": 180, "msrp": 349, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 8, "rops": 4, "memory_bandwidth_gbs": 6.4, "transistors_m": 25, "die_size_mm2": 88, "tflops_fp32": None, "pcie": "AGP 4x"},
    {"year": 2000, "month": 6, "manufacturer": "NVIDIA", "gpu_name": "GeForce 2 Ultra", "architecture": "NV15", "codename": "NV15",
     "memory_gb": 0.064, "memory_type": "DDR", "memory_bus_width": "128-bit", "base_clock_mhz": 250, "boost_clock_mhz": 250,
     "tdp_w": 30, "process_nm": 180, "msrp": 499, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 8, "rops": 4, "memory_bandwidth_gbs": 8.0, "transistors_m": 25, "die_size_mm2": 88, "tflops_fp32": None, "pcie": "AGP 4x"},
    {"year": 2000, "month": 6, "manufacturer": "NVIDIA", "gpu_name": "GeForce 2 MX", "architecture": "NV11", "codename": "NV11",
     "memory_gb": 0.032, "memory_type": "SDR", "memory_bus_width": "64-bit", "base_clock_mhz": 175, "boost_clock_mhz": 175,
     "tdp_w": 10, "process_nm": 180, "msrp": 99, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 4, "rops": 2, "memory_bandwidth_gbs": 2.8, "transistors_m": 20, "die_size_mm2": 65, "tflops_fp32": None, "pcie": "AGP 4x"},
    {"year": 2000, "month": 10, "manufacturer": "NVIDIA", "gpu_name": "GeForce 2 MX400", "architecture": "NV11", "codename": "NV11",
     "memory_gb": 0.064, "memory_type": "DDR", "memory_bus_width": "64-bit", "base_clock_mhz": 200, "boost_clock_mhz": 200,
     "tdp_w": 12, "process_nm": 180, "msrp": 129, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 4, "rops": 2, "memory_bandwidth_gbs": 3.2, "transistors_m": 20, "die_size_mm2": 65, "tflops_fp32": None, "pcie": "AGP 4x"},

    # GeForce 3 (2001)
    {"year": 2001, "month": 2, "manufacturer": "NVIDIA", "gpu_name": "GeForce 3", "architecture": "NV20", "codename": "NV20",
     "memory_gb": 0.064, "memory_type": "DDR", "memory_bus_width": "128-bit", "base_clock_mhz": 200, "boost_clock_mhz": 200,
     "tdp_w": 30, "process_nm": 150, "msrp": 449, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 8, "rops": 4, "memory_bandwidth_gbs": 6.4, "transistors_m": 57, "die_size_mm2": 128, "tflops_fp32": None, "pcie": "AGP 4x"},
    {"year": 2001, "month": 10, "manufacturer": "NVIDIA", "gpu_name": "GeForce 3 Ti 200", "architecture": "NV20", "codename": "NV20",
     "memory_gb": 0.064, "memory_type": "DDR", "memory_bus_width": "128-bit", "base_clock_mhz": 175, "boost_clock_mhz": 175,
     "tdp_w": 28, "process_nm": 150, "msrp": 299, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 8, "rops": 4, "memory_bandwidth_gbs": 5.6, "transistors_m": 57, "die_size_mm2": 128, "tflops_fp32": None, "pcie": "AGP 4x"},
    {"year": 2001, "month": 10, "manufacturer": "NVIDIA", "gpu_name": "GeForce 3 Ti 500", "architecture": "NV20", "codename": "NV20",
     "memory_gb": 0.064, "memory_type": "DDR", "memory_bus_width": "128-bit", "base_clock_mhz": 240, "boost_clock_mhz": 240,
     "tdp_w": 32, "process_nm": 150, "msrp": 399, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 8, "rops": 4, "memory_bandwidth_gbs": 7.7, "transistors_m": 57, "die_size_mm2": 128, "tflops_fp32": None, "pcie": "AGP 4x"},

    # Radeon 8500 / 9000 (2001-2002) - AMD/ATI
    {"year": 2001, "month": 8, "manufacturer": "AMD", "gpu_name": "Radeon 8500", "architecture": "R200", "codename": "R200",
     "memory_gb": 0.064, "memory_type": "DDR", "memory_bus_width": "128-bit", "base_clock_mhz": 275, "boost_clock_mhz": 275,
     "tdp_w": 35, "process_nm": 150, "msrp": 399, "oem": "Reference", "cuda_cores": None, "stream_processors": 4,  # pixel pipes approx
     "tmus": 8, "rops": 4, "memory_bandwidth_gbs": 8.8, "transistors_m": 60, "die_size_mm2": 120, "tflops_fp32": None, "pcie": "AGP 4x"},
    {"year": 2002, "month": 3, "manufacturer": "AMD", "gpu_name": "Radeon 9000 Pro", "architecture": "RV250", "codename": "RV250",
     "memory_gb": 0.064, "memory_type": "DDR", "memory_bus_width": "128-bit", "base_clock_mhz": 275, "boost_clock_mhz": 275,
     "tdp_w": 28, "process_nm": 150, "msrp": 199, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 4, "rops": 4, "memory_bandwidth_gbs": 8.8, "transistors_m": 36, "die_size_mm2": 84, "tflops_fp32": None, "pcie": "AGP 4x"},

    # GeForce 4 (2002)
    {"year": 2002, "month": 2, "manufacturer": "NVIDIA", "gpu_name": "GeForce 4 Ti 4600", "architecture": "NV25", "codename": "NV25",
     "memory_gb": 0.128, "memory_type": "DDR", "memory_bus_width": "128-bit", "base_clock_mhz": 300, "boost_clock_mhz": 300,
     "tdp_w": 50, "process_nm": 150, "msrp": 399, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 8, "rops": 4, "memory_bandwidth_gbs": 9.6, "transistors_m": 63, "die_size_mm2": 140, "tflops_fp32": None, "pcie": "AGP 4x"},
    {"year": 2002, "month": 2, "manufacturer": "NVIDIA", "gpu_name": "GeForce 4 Ti 4400", "architecture": "NV25", "codename": "NV25",
     "memory_gb": 0.128, "memory_type": "DDR", "memory_bus_width": "128-bit", "base_clock_mhz": 275, "boost_clock_mhz": 275,
     "tdp_w": 45, "process_nm": 150, "msrp": 299, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 8, "rops": 4, "memory_bandwidth_gbs": 8.8, "transistors_m": 63, "die_size_mm2": 140, "tflops_fp32": None, "pcie": "AGP 4x"},
    {"year": 2002, "month": 9, "manufacturer": "NVIDIA", "gpu_name": "GeForce 4 Ti 4200", "architecture": "NV25", "codename": "NV25",
     "memory_gb": 0.128, "memory_type": "DDR", "memory_bus_width": "128-bit", "base_clock_mhz": 250, "boost_clock_mhz": 250,
     "tdp_w": 40, "process_nm": 150, "msrp": 199, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 8, "rops": 4, "memory_bandwidth_gbs": 8.0, "transistors_m": 63, "die_size_mm2": 140, "tflops_fp32": None, "pcie": "AGP 4x"},
    {"year": 2002, "month": 10, "manufacturer": "NVIDIA", "gpu_name": "GeForce 4 MX 440", "architecture": "NV17", "codename": "NV17",
     "memory_gb": 0.064, "memory_type": "DDR", "memory_bus_width": "64-bit", "base_clock_mhz": 275, "boost_clock_mhz": 275,
     "tdp_w": 20, "process_nm": 150, "msrp": 99, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 4, "rops": 2, "memory_bandwidth_gbs": 4.4, "transistors_m": 29, "die_size_mm2": 65, "tflops_fp32": None, "pcie": "AGP 4x"},

    # Radeon 9700 (2002) - breakthrough
    {"year": 2002, "month": 7, "manufacturer": "AMD", "gpu_name": "Radeon 9700 Pro", "architecture": "R300", "codename": "R300",
     "memory_gb": 0.128, "memory_type": "DDR", "memory_bus_width": "256-bit", "base_clock_mhz": 325, "boost_clock_mhz": 325,
     "tdp_w": 50, "process_nm": 150, "msrp": 399, "oem": "Reference", "cuda_cores": None, "stream_processors": 8,
     "tmus": 8, "rops": 8, "memory_bandwidth_gbs": 20.8, "transistors_m": 110, "die_size_mm2": 219, "tflops_fp32": None, "pcie": "AGP 8x"},

    # GeForce FX (2003-2004) - 5xxx
    {"year": 2003, "month": 1, "manufacturer": "NVIDIA", "gpu_name": "GeForce FX 5800 Ultra", "architecture": "NV30", "codename": "NV30",
     "memory_gb": 0.256, "memory_type": "DDR2", "memory_bus_width": "128-bit", "base_clock_mhz": 500, "boost_clock_mhz": 500,
     "tdp_w": 65, "process_nm": 130, "msrp": 499, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 8, "rops": 4, "memory_bandwidth_gbs": 16.0, "transistors_m": 125, "die_size_mm2": 200, "tflops_fp32": None, "pcie": "AGP 8x"},
    {"year": 2003, "month": 3, "manufacturer": "NVIDIA", "gpu_name": "GeForce FX 5600 Ultra", "architecture": "NV31", "codename": "NV31",
     "memory_gb": 0.128, "memory_type": "DDR", "memory_bus_width": "128-bit", "base_clock_mhz": 400, "boost_clock_mhz": 400,
     "tdp_w": 45, "process_nm": 130, "msrp": 299, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 4, "rops": 4, "memory_bandwidth_gbs": 12.8, "transistors_m": 80, "die_size_mm2": 150, "tflops_fp32": None, "pcie": "AGP 8x"},
    {"year": 2004, "month": 3, "manufacturer": "NVIDIA", "gpu_name": "GeForce FX 5950 Ultra", "architecture": "NV35", "codename": "NV35",
     "memory_gb": 0.256, "memory_type": "DDR2", "memory_bus_width": "256-bit", "base_clock_mhz": 475, "boost_clock_mhz": 475,
     "tdp_w": 70, "process_nm": 130, "msrp": 499, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 8, "rops": 4, "memory_bandwidth_gbs": 30.4, "transistors_m": 130, "die_size_mm2": 200, "tflops_fp32": None, "pcie": "AGP 8x"},

    # Radeon 9800 / X series start (2003)
    {"year": 2003, "month": 3, "manufacturer": "AMD", "gpu_name": "Radeon 9800 Pro", "architecture": "R350", "codename": "R350",
     "memory_gb": 0.128, "memory_type": "DDR", "memory_bus_width": "256-bit", "base_clock_mhz": 380, "boost_clock_mhz": 380,
     "tdp_w": 55, "process_nm": 150, "msrp": 399, "oem": "Reference", "cuda_cores": None, "stream_processors": 8,
     "tmus": 8, "rops": 8, "memory_bandwidth_gbs": 24.3, "transistors_m": 117, "die_size_mm2": 206, "tflops_fp32": None, "pcie": "AGP 8x"},
    {"year": 2003, "month": 9, "manufacturer": "AMD", "gpu_name": "Radeon 9800 XT", "architecture": "R350", "codename": "R360",
     "memory_gb": 0.256, "memory_type": "DDR", "memory_bus_width": "256-bit", "base_clock_mhz": 412, "boost_clock_mhz": 412,
     "tdp_w": 60, "process_nm": 150, "msrp": 499, "oem": "Reference", "cuda_cores": None, "stream_processors": 8,
     "tmus": 8, "rops": 8, "memory_bandwidth_gbs": 26.4, "transistors_m": 117, "die_size_mm2": 206, "tflops_fp32": None, "pcie": "AGP 8x"},

    # ===================== 2004-2006: GeForce 6/7 + Radeon X =====================
    {"year": 2004, "month": 6, "manufacturer": "NVIDIA", "gpu_name": "GeForce 6800 Ultra", "architecture": "NV40", "codename": "NV40",
     "memory_gb": 0.256, "memory_type": "GDDR3", "memory_bus_width": "256-bit", "base_clock_mhz": 400, "boost_clock_mhz": 400,
     "tdp_w": 110, "process_nm": 130, "msrp": 499, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 16, "rops": 16, "memory_bandwidth_gbs": 25.6, "transistors_m": 222, "die_size_mm2": 287, "tflops_fp32": None, "pcie": "PCIe 1.0 x16"},
    {"year": 2004, "month": 11, "manufacturer": "NVIDIA", "gpu_name": "GeForce 6800 GT", "architecture": "NV40", "codename": "NV40",
     "memory_gb": 0.256, "memory_type": "GDDR3", "memory_bus_width": "256-bit", "base_clock_mhz": 350, "boost_clock_mhz": 350,
     "tdp_w": 90, "process_nm": 130, "msrp": 399, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 16, "rops": 16, "memory_bandwidth_gbs": 22.4, "transistors_m": 222, "die_size_mm2": 287, "tflops_fp32": None, "pcie": "PCIe 1.0 x16"},
    {"year": 2005, "month": 6, "manufacturer": "NVIDIA", "gpu_name": "GeForce 7800 GTX", "architecture": "G70", "codename": "G70",
     "memory_gb": 0.256, "memory_type": "GDDR3", "memory_bus_width": "256-bit", "base_clock_mhz": 430, "boost_clock_mhz": 430,
     "tdp_w": 86, "process_nm": 110, "msrp": 599, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 24, "rops": 16, "memory_bandwidth_gbs": 27.5, "transistors_m": 302, "die_size_mm2": 333, "tflops_fp32": None, "pcie": "PCIe 1.0 x16"},
    {"year": 2005, "month": 11, "manufacturer": "NVIDIA", "gpu_name": "GeForce 7800 GT", "architecture": "G70", "codename": "G70",
     "memory_gb": 0.256, "memory_type": "GDDR3", "memory_bus_width": "256-bit", "base_clock_mhz": 400, "boost_clock_mhz": 400,
     "tdp_w": 65, "process_nm": 110, "msrp": 349, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 20, "rops": 16, "memory_bandwidth_gbs": 25.6, "transistors_m": 302, "die_size_mm2": 333, "tflops_fp32": None, "pcie": "PCIe 1.0 x16"},
    {"year": 2006, "month": 3, "manufacturer": "NVIDIA", "gpu_name": "GeForce 7900 GTX", "architecture": "G71", "codename": "G71",
     "memory_gb": 0.512, "memory_type": "GDDR3", "memory_bus_width": "256-bit", "base_clock_mhz": 650, "boost_clock_mhz": 650,
     "tdp_w": 84, "process_nm": 90, "msrp": 599, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 24, "rops": 16, "memory_bandwidth_gbs": 41.6, "transistors_m": 278, "die_size_mm2": 196, "tflops_fp32": None, "pcie": "PCIe 1.0 x16"},
    {"year": 2006, "month": 5, "manufacturer": "NVIDIA", "gpu_name": "GeForce 7900 GT", "architecture": "G71", "codename": "G71",
     "memory_gb": 0.256, "memory_type": "GDDR3", "memory_bus_width": "256-bit", "base_clock_mhz": 450, "boost_clock_mhz": 450,
     "tdp_w": 48, "process_nm": 90, "msrp": 299, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 24, "rops": 16, "memory_bandwidth_gbs": 28.8, "transistors_m": 278, "die_size_mm2": 196, "tflops_fp32": None, "pcie": "PCIe 1.0 x16"},

    # Radeon X800 / X1800 / X1900 (2004-2006)
    {"year": 2004, "month": 5, "manufacturer": "AMD", "gpu_name": "Radeon X800 XT PE", "architecture": "R420", "codename": "R420",
     "memory_gb": 0.256, "memory_type": "GDDR3", "memory_bus_width": "256-bit", "base_clock_mhz": 520, "boost_clock_mhz": 520,
     "tdp_w": 70, "process_nm": 130, "msrp": 499, "oem": "Reference", "cuda_cores": None, "stream_processors": 16,
     "tmus": 16, "rops": 16, "memory_bandwidth_gbs": 33.3, "transistors_m": 160, "die_size_mm2": 281, "tflops_fp32": None, "pcie": "PCIe 1.0 x16"},
    {"year": 2005, "month": 10, "manufacturer": "AMD", "gpu_name": "Radeon X1800 XT", "architecture": "R520", "codename": "R520",
     "memory_gb": 0.512, "memory_type": "GDDR3", "memory_bus_width": "256-bit", "base_clock_mhz": 625, "boost_clock_mhz": 625,
     "tdp_w": 110, "process_nm": 90, "msrp": 549, "oem": "Reference", "cuda_cores": None, "stream_processors": 16,
     "tmus": 16, "rops": 16, "memory_bandwidth_gbs": 40.0, "transistors_m": 321, "die_size_mm2": 352, "tflops_fp32": None, "pcie": "PCIe 1.0 x16"},
    {"year": 2006, "month": 1, "manufacturer": "AMD", "gpu_name": "Radeon X1900 XTX", "architecture": "R580", "codename": "R580",
     "memory_gb": 0.512, "memory_type": "GDDR3", "memory_bus_width": "256-bit", "base_clock_mhz": 650, "boost_clock_mhz": 650,
     "tdp_w": 130, "process_nm": 90, "msrp": 649, "oem": "Reference", "cuda_cores": None, "stream_processors": 48,
     "tmus": 16, "rops": 16, "memory_bandwidth_gbs": 41.6, "transistors_m": 384, "die_size_mm2": 352, "tflops_fp32": None, "pcie": "PCIe 1.0 x16"},

    # ===================== 2006-2009: GeForce 8/9/200 + Radeon HD 2/3/4 =====================
    # GeForce 8 (G80 first unified + Tesla)
    {"year": 2006, "month": 11, "manufacturer": "NVIDIA", "gpu_name": "GeForce 8800 GTX", "architecture": "G80 (Tesla)", "codename": "G80",
     "memory_gb": 0.768, "memory_type": "GDDR3", "memory_bus_width": "384-bit", "base_clock_mhz": 575, "boost_clock_mhz": 575,
     "tdp_w": 155, "process_nm": 90, "msrp": 599, "oem": "Reference", "cuda_cores": 128, "stream_processors": None,
     "tmus": 64, "rops": 24, "memory_bandwidth_gbs": 86.4, "transistors_m": 681, "die_size_mm2": 484, "tflops_fp32": 0.3456, "pcie": "PCIe 1.0 x16"},
    {"year": 2006, "month": 11, "manufacturer": "NVIDIA", "gpu_name": "GeForce 8800 GTS 640", "architecture": "G80 (Tesla)", "codename": "G80",
     "memory_gb": 0.640, "memory_type": "GDDR3", "memory_bus_width": "320-bit", "base_clock_mhz": 500, "boost_clock_mhz": 500,
     "tdp_w": 108, "process_nm": 90, "msrp": 449, "oem": "Reference", "cuda_cores": 96, "stream_processors": None,
     "tmus": 48, "rops": 20, "memory_bandwidth_gbs": 64.0, "transistors_m": 681, "die_size_mm2": 484, "tflops_fp32": 0.2304, "pcie": "PCIe 1.0 x16"},
    {"year": 2007, "month": 4, "manufacturer": "NVIDIA", "gpu_name": "GeForce 8800 Ultra", "architecture": "G80 (Tesla)", "codename": "G80",
     "memory_gb": 0.768, "memory_type": "GDDR3", "memory_bus_width": "384-bit", "base_clock_mhz": 612, "boost_clock_mhz": 612,
     "tdp_w": 175, "process_nm": 90, "msrp": 829, "oem": "Reference", "cuda_cores": 128, "stream_processors": None,
     "tmus": 64, "rops": 24, "memory_bandwidth_gbs": 103.7, "transistors_m": 681, "die_size_mm2": 484, "tflops_fp32": 0.3686, "pcie": "PCIe 1.0 x16"},

    # GeForce 9 (2008)
    {"year": 2008, "month": 2, "manufacturer": "NVIDIA", "gpu_name": "GeForce 9600 GT", "architecture": "G94", "codename": "G94",
     "memory_gb": 0.512, "memory_type": "GDDR3", "memory_bus_width": "256-bit", "base_clock_mhz": 650, "boost_clock_mhz": 650,
     "tdp_w": 95, "process_nm": 65, "msrp": 179, "oem": "Reference", "cuda_cores": 64, "stream_processors": None,
     "tmus": 32, "rops": 16, "memory_bandwidth_gbs": 41.6, "transistors_m": 505, "die_size_mm2": 196, "tflops_fp32": 0.208, "pcie": "PCIe 2.0 x16"},
    {"year": 2008, "month": 6, "manufacturer": "NVIDIA", "gpu_name": "GeForce 9800 GTX", "architecture": "G92", "codename": "G92",
     "memory_gb": 0.512, "memory_type": "GDDR3", "memory_bus_width": "256-bit", "base_clock_mhz": 675, "boost_clock_mhz": 675,
     "tdp_w": 140, "process_nm": 65, "msrp": 329, "oem": "Reference", "cuda_cores": 128, "stream_processors": None,
     "tmus": 64, "rops": 16, "memory_bandwidth_gbs": 70.4, "transistors_m": 754, "die_size_mm2": 324, "tflops_fp32": 0.432, "pcie": "PCIe 2.0 x16"},
    {"year": 2009, "month": 3, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 285", "architecture": "GT200b", "codename": "GT200",
     "memory_gb": 1.0, "memory_type": "GDDR3", "memory_bus_width": "512-bit", "base_clock_mhz": 648, "boost_clock_mhz": 648,
     "tdp_w": 204, "process_nm": 55, "msrp": 359, "oem": "Reference", "cuda_cores": 240, "stream_processors": None,
     "tmus": 80, "rops": 32, "memory_bandwidth_gbs": 159.0, "transistors_m": 1400, "die_size_mm2": 470, "tflops_fp32": 0.7085, "pcie": "PCIe 2.0 x16"},
    {"year": 2008, "month": 6, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 280", "architecture": "GT200", "codename": "GT200",
     "memory_gb": 1.0, "memory_type": "GDDR3", "memory_bus_width": "512-bit", "base_clock_mhz": 602, "boost_clock_mhz": 648,
     "tdp_w": 236, "process_nm": 65, "msrp": 649, "oem": "Reference", "cuda_cores": 240, "stream_processors": None,
     "tmus": 80, "rops": 32, "memory_bandwidth_gbs": 141.7, "transistors_m": 1400, "die_size_mm2": 576, "tflops_fp32": 0.622, "pcie": "PCIe 2.0 x16"},

    # Radeon HD 2000/3000/4000 (2007-2008)
    {"year": 2007, "month": 5, "manufacturer": "AMD", "gpu_name": "Radeon HD 2900 XT", "architecture": "R600 (TeraScale)", "codename": "R600",
     "memory_gb": 0.512, "memory_type": "GDDR3", "memory_bus_width": "512-bit", "base_clock_mhz": 743, "boost_clock_mhz": 743,
     "tdp_w": 215, "process_nm": 80, "msrp": 399, "oem": "Reference", "cuda_cores": None, "stream_processors": 320,
     "tmus": 16, "rops": 16, "memory_bandwidth_gbs": 106.0, "transistors_m": 720, "die_size_mm2": 420, "tflops_fp32": 0.475, "pcie": "PCIe 1.0 x16"},
    {"year": 2008, "month": 6, "manufacturer": "AMD", "gpu_name": "Radeon HD 4870", "architecture": "RV770 (TeraScale)", "codename": "RV770",
     "memory_gb": 0.512, "memory_type": "GDDR5", "memory_bus_width": "256-bit", "base_clock_mhz": 750, "boost_clock_mhz": 750,
     "tdp_w": 160, "process_nm": 55, "msrp": 299, "oem": "Reference", "cuda_cores": None, "stream_processors": 800,
     "tmus": 40, "rops": 16, "memory_bandwidth_gbs": 115.2, "transistors_m": 956, "die_size_mm2": 256, "tflops_fp32": 1.2, "pcie": "PCIe 2.0 x16"},
    {"year": 2008, "month": 1, "manufacturer": "AMD", "gpu_name": "Radeon HD 3870", "architecture": "RV670 (TeraScale)", "codename": "RV670",
     "memory_gb": 0.512, "memory_type": "GDDR4", "memory_bus_width": "256-bit", "base_clock_mhz": 775, "boost_clock_mhz": 775,
     "tdp_w": 106, "process_nm": 55, "msrp": 269, "oem": "Reference", "cuda_cores": None, "stream_processors": 320,
     "tmus": 16, "rops": 16, "memory_bandwidth_gbs": 72.0, "transistors_m": 666, "die_size_mm2": 192, "tflops_fp32": 0.496, "pcie": "PCIe 2.0 x16"},

    # Radeon HD 5000 / 6000 (Evergreen / Northern Islands)
    {"year": 2009, "month": 9, "manufacturer": "AMD", "gpu_name": "Radeon HD 5870", "architecture": "Cypress (Evergreen)", "codename": "Cypress",
     "memory_gb": 1.0, "memory_type": "GDDR5", "memory_bus_width": "256-bit", "base_clock_mhz": 850, "boost_clock_mhz": 850,
     "tdp_w": 188, "process_nm": 40, "msrp": 379, "oem": "Reference", "cuda_cores": None, "stream_processors": 1600,
     "tmus": 80, "rops": 32, "memory_bandwidth_gbs": 153.6, "transistors_m": 2154, "die_size_mm2": 334, "tflops_fp32": 2.72, "pcie": "PCIe 2.0 x16"},
    {"year": 2009, "month": 10, "manufacturer": "AMD", "gpu_name": "Radeon HD 5850", "architecture": "Cypress (Evergreen)", "codename": "Cypress",
     "memory_gb": 1.0, "memory_type": "GDDR5", "memory_bus_width": "256-bit", "base_clock_mhz": 725, "boost_clock_mhz": 725,
     "tdp_w": 151, "process_nm": 40, "msrp": 299, "oem": "Reference", "cuda_cores": None, "stream_processors": 1440,
     "tmus": 72, "rops": 32, "memory_bandwidth_gbs": 128.0, "transistors_m": 2154, "die_size_mm2": 334, "tflops_fp32": 2.09, "pcie": "PCIe 2.0 x16"},
    {"year": 2010, "month": 10, "manufacturer": "AMD", "gpu_name": "Radeon HD 6970", "architecture": "Cayman (Northern Islands)", "codename": "Cayman",
     "memory_gb": 2.0, "memory_type": "GDDR5", "memory_bus_width": "256-bit", "base_clock_mhz": 880, "boost_clock_mhz": 880,
     "tdp_w": 250, "process_nm": 40, "msrp": 369, "oem": "Reference", "cuda_cores": None, "stream_processors": 1536,
     "tmus": 96, "rops": 32, "memory_bandwidth_gbs": 176.0, "transistors_m": 2640, "die_size_mm2": 389, "tflops_fp32": 2.70, "pcie": "PCIe 2.1 x16"},
    {"year": 2010, "month": 12, "manufacturer": "AMD", "gpu_name": "Radeon HD 6950", "architecture": "Cayman (Northern Islands)", "codename": "Cayman",
     "memory_gb": 2.0, "memory_type": "GDDR5", "memory_bus_width": "256-bit", "base_clock_mhz": 800, "boost_clock_mhz": 800,
     "tdp_w": 200, "process_nm": 40, "msrp": 299, "oem": "Reference", "cuda_cores": None, "stream_processors": 1408,
     "tmus": 88, "rops": 32, "memory_bandwidth_gbs": 160.0, "transistors_m": 2640, "die_size_mm2": 389, "tflops_fp32": 2.25, "pcie": "PCIe 2.1 x16"},

    # ===================== 2010-2012: Fermi / Kepler early + Radeon HD 7000 =====================
    {"year": 2010, "month": 3, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 480", "architecture": "GF100 (Fermi)", "codename": "GF100",
     "memory_gb": 1.5, "memory_type": "GDDR5", "memory_bus_width": "384-bit", "base_clock_mhz": 700, "boost_clock_mhz": 700,
     "tdp_w": 250, "process_nm": 40, "msrp": 499, "oem": "Reference", "cuda_cores": 480, "stream_processors": None,
     "tmus": 60, "rops": 48, "memory_bandwidth_gbs": 177.4, "transistors_m": 3000, "die_size_mm2": 529, "tflops_fp32": 1.345, "pcie": "PCIe 2.0 x16"},
    {"year": 2010, "month": 4, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 470", "architecture": "GF100 (Fermi)", "codename": "GF100",
     "memory_gb": 1.25, "memory_type": "GDDR5", "memory_bus_width": "320-bit", "base_clock_mhz": 607, "boost_clock_mhz": 607,
     "tdp_w": 215, "process_nm": 40, "msrp": 349, "oem": "Reference", "cuda_cores": 448, "stream_processors": None,
     "tmus": 56, "rops": 40, "memory_bandwidth_gbs": 133.9, "transistors_m": 3000, "die_size_mm2": 529, "tflops_fp32": 1.09, "pcie": "PCIe 2.0 x16"},
    {"year": 2010, "month": 11, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 580", "architecture": "GF110 (Fermi)", "codename": "GF110",
     "memory_gb": 1.5, "memory_type": "GDDR5", "memory_bus_width": "384-bit", "base_clock_mhz": 772, "boost_clock_mhz": 772,
     "tdp_w": 244, "process_nm": 40, "msrp": 499, "oem": "Reference", "cuda_cores": 512, "stream_processors": None,
     "tmus": 64, "rops": 48, "memory_bandwidth_gbs": 192.0, "transistors_m": 3000, "die_size_mm2": 520, "tflops_fp32": 1.58, "pcie": "PCIe 2.0 x16"},
    {"year": 2011, "month": 5, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 560 Ti", "architecture": "GF114 (Fermi)", "codename": "GF114",
     "memory_gb": 1.0, "memory_type": "GDDR5", "memory_bus_width": "256-bit", "base_clock_mhz": 822, "boost_clock_mhz": 822,
     "tdp_w": 170, "process_nm": 40, "msrp": 249, "oem": "Reference", "cuda_cores": 384, "stream_processors": None,
     "tmus": 64, "rops": 32, "memory_bandwidth_gbs": 128.3, "transistors_m": 1950, "die_size_mm2": 332, "tflops_fp32": 1.26, "pcie": "PCIe 2.0 x16"},

    # Kepler
    {"year": 2012, "month": 3, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 680", "architecture": "GK104 (Kepler)", "codename": "GK104",
     "memory_gb": 2.0, "memory_type": "GDDR5", "memory_bus_width": "256-bit", "base_clock_mhz": 1006, "boost_clock_mhz": 1058,
     "tdp_w": 195, "process_nm": 28, "msrp": 499, "oem": "Reference", "cuda_cores": 1536, "stream_processors": None,
     "tmus": 128, "rops": 32, "memory_bandwidth_gbs": 192.3, "transistors_m": 3540, "die_size_mm2": 294, "tflops_fp32": 3.25, "pcie": "PCIe 3.0 x16"},
    {"year": 2012, "month": 8, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 670", "architecture": "GK104 (Kepler)", "codename": "GK104",
     "memory_gb": 2.0, "memory_type": "GDDR5", "memory_bus_width": "256-bit", "base_clock_mhz": 915, "boost_clock_mhz": 980,
     "tdp_w": 170, "process_nm": 28, "msrp": 399, "oem": "Reference", "cuda_cores": 1344, "stream_processors": None,
     "tmus": 112, "rops": 32, "memory_bandwidth_gbs": 192.3, "transistors_m": 3540, "die_size_mm2": 294, "tflops_fp32": 2.63, "pcie": "PCIe 3.0 x16"},
    {"year": 2013, "month": 2, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX Titan", "architecture": "GK110 (Kepler)", "codename": "GK110",
     "memory_gb": 6.0, "memory_type": "GDDR5", "memory_bus_width": "384-bit", "base_clock_mhz": 837, "boost_clock_mhz": 876,
     "tdp_w": 250, "process_nm": 28, "msrp": 999, "oem": "Reference", "cuda_cores": 2688, "stream_processors": None,
     "tmus": 224, "rops": 48, "memory_bandwidth_gbs": 288.4, "transistors_m": 7080, "die_size_mm2": 561, "tflops_fp32": 4.5, "pcie": "PCIe 3.0 x16"},

    # Radeon HD 7000 / 8000 (Southern Islands / Sea Islands)
    {"year": 2012, "month": 1, "manufacturer": "AMD", "gpu_name": "Radeon HD 7970", "architecture": "Tahiti (Southern Islands)", "codename": "Tahiti XT",
     "memory_gb": 3.0, "memory_type": "GDDR5", "memory_bus_width": "384-bit", "base_clock_mhz": 925, "boost_clock_mhz": 925,
     "tdp_w": 250, "process_nm": 28, "msrp": 549, "oem": "Reference", "cuda_cores": None, "stream_processors": 2048,
     "tmus": 128, "rops": 32, "memory_bandwidth_gbs": 264.0, "transistors_m": 4313, "die_size_mm2": 352, "tflops_fp32": 3.79, "pcie": "PCIe 3.0 x16"},
    {"year": 2012, "month": 6, "manufacturer": "AMD", "gpu_name": "Radeon HD 7950", "architecture": "Tahiti (Southern Islands)", "codename": "Tahiti Pro",
     "memory_gb": 3.0, "memory_type": "GDDR5", "memory_bus_width": "384-bit", "base_clock_mhz": 800, "boost_clock_mhz": 800,
     "tdp_w": 200, "process_nm": 28, "msrp": 449, "oem": "Reference", "cuda_cores": None, "stream_processors": 1792,
     "tmus": 112, "rops": 32, "memory_bandwidth_gbs": 240.0, "transistors_m": 4313, "die_size_mm2": 352, "tflops_fp32": 2.87, "pcie": "PCIe 3.0 x16"},
    {"year": 2013, "month": 10, "manufacturer": "AMD", "gpu_name": "Radeon R9 290X", "architecture": "Hawaii (Sea Islands)", "codename": "Hawaii XT",
     "memory_gb": 4.0, "memory_type": "GDDR5", "memory_bus_width": "512-bit", "base_clock_mhz": 1000, "boost_clock_mhz": 1000,
     "tdp_w": 250, "process_nm": 28, "msrp": 549, "oem": "Reference", "cuda_cores": None, "stream_processors": 2816,
     "tmus": 176, "rops": 64, "memory_bandwidth_gbs": 320.0, "transistors_m": 6200, "die_size_mm2": 438, "tflops_fp32": 5.63, "pcie": "PCIe 3.0 x16"},

    # ===================== 2013-2015: Maxwell + R9 200/300 =====================
    {"year": 2014, "month": 2, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 750 Ti", "architecture": "GM107 (Maxwell)", "codename": "GM107",
     "memory_gb": 2.0, "memory_type": "GDDR5", "memory_bus_width": "128-bit", "base_clock_mhz": 1020, "boost_clock_mhz": 1085,
     "tdp_w": 60, "process_nm": 28, "msrp": 149, "oem": "Reference", "cuda_cores": 640, "stream_processors": None,
     "tmus": 40, "rops": 16, "memory_bandwidth_gbs": 86.4, "transistors_m": 1870, "die_size_mm2": 148, "tflops_fp32": 1.39, "pcie": "PCIe 3.0 x16"},
    {"year": 2014, "month": 9, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 980", "architecture": "GM204 (Maxwell)", "codename": "GM204",
     "memory_gb": 4.0, "memory_type": "GDDR5", "memory_bus_width": "256-bit", "base_clock_mhz": 1126, "boost_clock_mhz": 1216,
     "tdp_w": 165, "process_nm": 28, "msrp": 549, "oem": "Reference", "cuda_cores": 2048, "stream_processors": None,
     "tmus": 128, "rops": 64, "memory_bandwidth_gbs": 224.0, "transistors_m": 5200, "die_size_mm2": 398, "tflops_fp32": 4.98, "pcie": "PCIe 3.0 x16"},
    {"year": 2015, "month": 6, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 980 Ti", "architecture": "GM200 (Maxwell)", "codename": "GM200",
     "memory_gb": 6.0, "memory_type": "GDDR5", "memory_bus_width": "384-bit", "base_clock_mhz": 1000, "boost_clock_mhz": 1075,
     "tdp_w": 250, "process_nm": 28, "msrp": 649, "oem": "Reference", "cuda_cores": 2816, "stream_processors": None,
     "tmus": 176, "rops": 96, "memory_bandwidth_gbs": 336.5, "transistors_m": 8000, "die_size_mm2": 601, "tflops_fp32": 6.06, "pcie": "PCIe 3.0 x16"},
    {"year": 2015, "month": 8, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 950", "architecture": "GM206 (Maxwell)", "codename": "GM206",
     "memory_gb": 2.0, "memory_type": "GDDR5", "memory_bus_width": "128-bit", "base_clock_mhz": 1024, "boost_clock_mhz": 1188,
     "tdp_w": 90, "process_nm": 28, "msrp": 159, "oem": "Reference", "cuda_cores": 768, "stream_processors": None,
     "tmus": 48, "rops": 32, "memory_bandwidth_gbs": 105.6, "transistors_m": 2940, "die_size_mm2": 227, "tflops_fp32": 1.83, "pcie": "PCIe 3.0 x16"},

    # R9 200 / 300 / Fury
    {"year": 2014, "month": 10, "manufacturer": "AMD", "gpu_name": "Radeon R9 290", "architecture": "Hawaii", "codename": "Hawaii Pro",
     "memory_gb": 4.0, "memory_type": "GDDR5", "memory_bus_width": "512-bit", "base_clock_mhz": 947, "boost_clock_mhz": 947,
     "tdp_w": 250, "process_nm": 28, "msrp": 399, "oem": "Reference", "cuda_cores": None, "stream_processors": 2560,
     "tmus": 160, "rops": 64, "memory_bandwidth_gbs": 320.0, "transistors_m": 6200, "die_size_mm2": 438, "tflops_fp32": 4.85, "pcie": "PCIe 3.0 x16"},
    {"year": 2015, "month": 6, "manufacturer": "AMD", "gpu_name": "Radeon R9 Fury X", "architecture": "Fiji", "codename": "Fiji XT",
     "memory_gb": 4.0, "memory_type": "HBM", "memory_bus_width": "4096-bit", "base_clock_mhz": 1050, "boost_clock_mhz": 1050,
     "tdp_w": 275, "process_nm": 28, "msrp": 649, "oem": "Reference", "cuda_cores": None, "stream_processors": 4096,
     "tmus": 256, "rops": 64, "memory_bandwidth_gbs": 512.0, "transistors_m": 8900, "die_size_mm2": 596, "tflops_fp32": 8.6, "pcie": "PCIe 3.0 x16"},
    {"year": 2015, "month": 6, "manufacturer": "AMD", "gpu_name": "Radeon R9 Fury", "architecture": "Fiji", "codename": "Fiji Pro",
     "memory_gb": 4.0, "memory_type": "HBM", "memory_bus_width": "4096-bit", "base_clock_mhz": 1000, "boost_clock_mhz": 1000,
     "tdp_w": 275, "process_nm": 28, "msrp": 549, "oem": "Reference", "cuda_cores": None, "stream_processors": 3584,
     "tmus": 224, "rops": 64, "memory_bandwidth_gbs": 512.0, "transistors_m": 8900, "die_size_mm2": 596, "tflops_fp32": 7.2, "pcie": "PCIe 3.0 x16"},

    # ===================== 2016-2017: Pascal / Polaris / Vega =====================
    {"year": 2016, "month": 5, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 1080", "architecture": "GP104 (Pascal)", "codename": "GP104",
     "memory_gb": 8.0, "memory_type": "GDDR5X", "memory_bus_width": "256-bit", "base_clock_mhz": 1607, "boost_clock_mhz": 1733,
     "tdp_w": 180, "process_nm": 16, "msrp": 599, "oem": "Reference", "cuda_cores": 2560, "stream_processors": None,
     "tmus": 160, "rops": 64, "memory_bandwidth_gbs": 320.0, "transistors_m": 7200, "die_size_mm2": 314, "tflops_fp32": 8.87, "pcie": "PCIe 3.0 x16"},
    {"year": 2016, "month": 6, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 1070", "architecture": "GP104 (Pascal)", "codename": "GP104",
     "memory_gb": 8.0, "memory_type": "GDDR5", "memory_bus_width": "256-bit", "base_clock_mhz": 1506, "boost_clock_mhz": 1683,
     "tdp_w": 150, "process_nm": 16, "msrp": 379, "oem": "Reference", "cuda_cores": 1920, "stream_processors": None,
     "tmus": 120, "rops": 64, "memory_bandwidth_gbs": 256.3, "transistors_m": 7200, "die_size_mm2": 314, "tflops_fp32": 6.46, "pcie": "PCIe 3.0 x16"},
    {"year": 2016, "month": 8, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 1080 Ti", "architecture": "GP102 (Pascal)", "codename": "GP102",
     "memory_gb": 11.0, "memory_type": "GDDR5X", "memory_bus_width": "352-bit", "base_clock_mhz": 1480, "boost_clock_mhz": 1582,
     "tdp_w": 250, "process_nm": 16, "msrp": 699, "oem": "Reference", "cuda_cores": 3584, "stream_processors": None,
     "tmus": 224, "rops": 88, "memory_bandwidth_gbs": 484.4, "transistors_m": 11800, "die_size_mm2": 471, "tflops_fp32": 11.34, "pcie": "PCIe 3.0 x16"},
    {"year": 2016, "month": 6, "manufacturer": "AMD", "gpu_name": "Radeon RX 480", "architecture": "Polaris 10 (GCN 4)", "codename": "Ellesmere",
     "memory_gb": 8.0, "memory_type": "GDDR5", "memory_bus_width": "256-bit", "base_clock_mhz": 1120, "boost_clock_mhz": 1266,
     "tdp_w": 150, "process_nm": 14, "msrp": 239, "oem": "Reference", "cuda_cores": None, "stream_processors": 2304,
     "tmus": 144, "rops": 32, "memory_bandwidth_gbs": 256.0, "transistors_m": 5700, "die_size_mm2": 232, "tflops_fp32": 5.83, "pcie": "PCIe 3.0 x16"},
    {"year": 2016, "month": 6, "manufacturer": "AMD", "gpu_name": "Radeon RX 470", "architecture": "Polaris 10 (GCN 4)", "codename": "Ellesmere",
     "memory_gb": 4.0, "memory_type": "GDDR5", "memory_bus_width": "256-bit", "base_clock_mhz": 926, "boost_clock_mhz": 1206,
     "tdp_w": 120, "process_nm": 14, "msrp": 179, "oem": "Reference", "cuda_cores": None, "stream_processors": 2048,
     "tmus": 128, "rops": 32, "memory_bandwidth_gbs": 211.0, "transistors_m": 5700, "die_size_mm2": 232, "tflops_fp32": 4.94, "pcie": "PCIe 3.0 x16"},
    {"year": 2017, "month": 6, "manufacturer": "AMD", "gpu_name": "Radeon RX Vega 64", "architecture": "Vega 10", "codename": "Vega 10 XT",
     "memory_gb": 8.0, "memory_type": "HBM2", "memory_bus_width": "2048-bit", "base_clock_mhz": 1247, "boost_clock_mhz": 1546,
     "tdp_w": 295, "process_nm": 14, "msrp": 499, "oem": "Reference", "cuda_cores": None, "stream_processors": 4096,
     "tmus": 256, "rops": 64, "memory_bandwidth_gbs": 483.8, "transistors_m": 12500, "die_size_mm2": 495, "tflops_fp32": 12.66, "pcie": "PCIe 3.0 x16"},
    {"year": 2017, "month": 6, "manufacturer": "AMD", "gpu_name": "Radeon RX Vega 56", "architecture": "Vega 10", "codename": "Vega 10",
     "memory_gb": 8.0, "memory_type": "HBM2", "memory_bus_width": "2048-bit", "base_clock_mhz": 1156, "boost_clock_mhz": 1471,
     "tdp_w": 210, "process_nm": 14, "msrp": 399, "oem": "Reference", "cuda_cores": None, "stream_processors": 3584,
     "tmus": 224, "rops": 64, "memory_bandwidth_gbs": 410.0, "transistors_m": 12500, "die_size_mm2": 495, "tflops_fp32": 10.54, "pcie": "PCIe 3.0 x16"},

    # ===================== 2018-2019: Turing / Navi (RDNA) =====================
    {"year": 2018, "month": 9, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 2080 Ti", "architecture": "TU102 (Turing)", "codename": "TU102",
     "memory_gb": 11.0, "memory_type": "GDDR6", "memory_bus_width": "352-bit", "base_clock_mhz": 1350, "boost_clock_mhz": 1635,
     "tdp_w": 260, "process_nm": 12, "msrp": 1199, "oem": "Reference", "cuda_cores": 4352, "stream_processors": None,
     "tensor_cores": 544, "rt_cores": 68, "tmus": 272, "rops": 88, "memory_bandwidth_gbs": 616.0, "transistors_m": 18600, "die_size_mm2": 754, "tflops_fp32": 14.23, "pcie": "PCIe 3.0 x16"},
    {"year": 2018, "month": 9, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 2080", "architecture": "TU104 (Turing)", "codename": "TU104",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 1515, "boost_clock_mhz": 1710,
     "tdp_w": 215, "process_nm": 12, "msrp": 799, "oem": "Reference", "cuda_cores": 2944, "stream_processors": None,
     "tensor_cores": 368, "rt_cores": 46, "tmus": 184, "rops": 64, "memory_bandwidth_gbs": 448.0, "transistors_m": 13600, "die_size_mm2": 545, "tflops_fp32": 10.07, "pcie": "PCIe 3.0 x16"},
    {"year": 2018, "month": 9, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 2070", "architecture": "TU106 (Turing)", "codename": "TU106",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 1410, "boost_clock_mhz": 1620,
     "tdp_w": 175, "process_nm": 12, "msrp": 499, "oem": "Reference", "cuda_cores": 2304, "stream_processors": None,
     "tensor_cores": 288, "rt_cores": 36, "tmus": 144, "rops": 64, "memory_bandwidth_gbs": 448.0, "transistors_m": 10800, "die_size_mm2": 445, "tflops_fp32": 7.46, "pcie": "PCIe 3.0 x16"},
    {"year": 2019, "month": 7, "manufacturer": "AMD", "gpu_name": "Radeon RX 5700 XT", "architecture": "Navi 10 (RDNA)", "codename": "Navi 10 XT",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 1605, "boost_clock_mhz": 1905,
     "tdp_w": 225, "process_nm": 7, "msrp": 399, "oem": "Reference", "cuda_cores": None, "stream_processors": 2560,
     "tmus": 160, "rops": 64, "memory_bandwidth_gbs": 448.0, "transistors_m": 10300, "die_size_mm2": 251, "tflops_fp32": 9.75, "pcie": "PCIe 4.0 x16"},
    {"year": 2019, "month": 7, "manufacturer": "AMD", "gpu_name": "Radeon RX 5700", "architecture": "Navi 10 (RDNA)", "codename": "Navi 10",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 1465, "boost_clock_mhz": 1725,
     "tdp_w": 180, "process_nm": 7, "msrp": 349, "oem": "Reference", "cuda_cores": None, "stream_processors": 2304,
     "tmus": 144, "rops": 64, "memory_bandwidth_gbs": 448.0, "transistors_m": 10300, "die_size_mm2": 251, "tflops_fp32": 7.95, "pcie": "PCIe 4.0 x16"},

    # ===================== 2020-2021: Ampere / RDNA 2 =====================
    {"year": 2020, "month": 9, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 3080", "architecture": "GA102 (Ampere)", "codename": "GA102",
     "memory_gb": 10.0, "memory_type": "GDDR6X", "memory_bus_width": "320-bit", "base_clock_mhz": 1440, "boost_clock_mhz": 1710,
     "tdp_w": 320, "process_nm": 8, "msrp": 699, "oem": "Reference", "cuda_cores": 8704, "stream_processors": None,
     "tensor_cores": 272, "rt_cores": 68, "tmus": 272, "rops": 96, "memory_bandwidth_gbs": 760.3, "transistors_m": 28300, "die_size_mm2": 628, "tflops_fp32": 29.77, "pcie": "PCIe 4.0 x16"},
    {"year": 2020, "month": 9, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 3090", "architecture": "GA102 (Ampere)", "codename": "GA102",
     "memory_gb": 24.0, "memory_type": "GDDR6X", "memory_bus_width": "384-bit", "base_clock_mhz": 1395, "boost_clock_mhz": 1695,
     "tdp_w": 350, "process_nm": 8, "msrp": 1499, "oem": "Reference", "cuda_cores": 10496, "stream_processors": None,
     "tensor_cores": 328, "rt_cores": 82, "tmus": 328, "rops": 112, "memory_bandwidth_gbs": 936.2, "transistors_m": 28300, "die_size_mm2": 628, "tflops_fp32": 35.58, "pcie": "PCIe 4.0 x16"},
    {"year": 2020, "month": 10, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 3070", "architecture": "GA104 (Ampere)", "codename": "GA104",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 1500, "boost_clock_mhz": 1725,
     "tdp_w": 220, "process_nm": 8, "msrp": 499, "oem": "Reference", "cuda_cores": 5888, "stream_processors": None,
     "tensor_cores": 184, "rt_cores": 46, "tmus": 184, "rops": 96, "memory_bandwidth_gbs": 448.0, "transistors_m": 17400, "die_size_mm2": 392, "tflops_fp32": 20.31, "pcie": "PCIe 4.0 x16"},
    {"year": 2021, "month": 6, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 3080 Ti", "architecture": "GA102 (Ampere)", "codename": "GA102",
     "memory_gb": 12.0, "memory_type": "GDDR6X", "memory_bus_width": "384-bit", "base_clock_mhz": 1365, "boost_clock_mhz": 1665,
     "tdp_w": 350, "process_nm": 8, "msrp": 1199, "oem": "Reference", "cuda_cores": 10240, "stream_processors": None,
     "tensor_cores": 320, "rt_cores": 80, "tmus": 320, "rops": 112, "memory_bandwidth_gbs": 912.0, "transistors_m": 28300, "die_size_mm2": 628, "tflops_fp32": 34.1, "pcie": "PCIe 4.0 x16"},
    {"year": 2021, "month": 1, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 3060 Ti", "architecture": "GA104 (Ampere)", "codename": "GA104",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 1410, "boost_clock_mhz": 1665,
     "tdp_w": 200, "process_nm": 8, "msrp": 399, "oem": "Reference", "cuda_cores": 4864, "stream_processors": None,
     "tensor_cores": 152, "rt_cores": 38, "tmus": 152, "rops": 80, "memory_bandwidth_gbs": 448.0, "transistors_m": 17400, "die_size_mm2": 392, "tflops_fp32": 16.2, "pcie": "PCIe 4.0 x16"},
    {"year": 2020, "month": 11, "manufacturer": "AMD", "gpu_name": "Radeon RX 6800 XT", "architecture": "Navi 21 (RDNA 2)", "codename": "Navi 21",
     "memory_gb": 16.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 1825, "boost_clock_mhz": 2250,
     "tdp_w": 300, "process_nm": 7, "msrp": 649, "oem": "Reference", "cuda_cores": None, "stream_processors": 4608,
     "tmus": 288, "rops": 128, "memory_bandwidth_gbs": 512.0, "transistors_m": 26800, "die_size_mm2": 520, "tflops_fp32": 20.74, "pcie": "PCIe 4.0 x16"},
    {"year": 2020, "month": 11, "manufacturer": "AMD", "gpu_name": "Radeon RX 6900 XT", "architecture": "Navi 21 (RDNA 2)", "codename": "Navi 21",
     "memory_gb": 16.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 1825, "boost_clock_mhz": 2250,
     "tdp_w": 300, "process_nm": 7, "msrp": 999, "oem": "Reference", "cuda_cores": None, "stream_processors": 5120,
     "tmus": 320, "rops": 128, "memory_bandwidth_gbs": 512.0, "transistors_m": 26800, "die_size_mm2": 520, "tflops_fp32": 23.04, "pcie": "PCIe 4.0 x16"},
    {"year": 2021, "month": 3, "manufacturer": "AMD", "gpu_name": "Radeon RX 6700 XT", "architecture": "Navi 22 (RDNA 2)", "codename": "Navi 22",
     "memory_gb": 12.0, "memory_type": "GDDR6", "memory_bus_width": "192-bit", "base_clock_mhz": 2321, "boost_clock_mhz": 2581,
     "tdp_w": 230, "process_nm": 7, "msrp": 479, "oem": "Reference", "cuda_cores": None, "stream_processors": 2560,
     "tmus": 160, "rops": 64, "memory_bandwidth_gbs": 384.0, "transistors_m": 17200, "die_size_mm2": 335, "tflops_fp32": 13.21, "pcie": "PCIe 4.0 x16"},

    # ===================== 2022-2024: Ada Lovelace / RDNA 3 =====================
    {"year": 2022, "month": 10, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 4090", "architecture": "AD102 (Ada Lovelace)", "codename": "AD102",
     "memory_gb": 24.0, "memory_type": "GDDR6X", "memory_bus_width": "384-bit", "base_clock_mhz": 2230, "boost_clock_mhz": 2520,
     "tdp_w": 450, "process_nm": 4, "msrp": 1599, "oem": "Reference", "cuda_cores": 16384, "stream_processors": None,
     "tensor_cores": 512, "rt_cores": 128, "tmus": 512, "rops": 176, "memory_bandwidth_gbs": 1008.0, "transistors_m": 76300, "die_size_mm2": 609, "tflops_fp32": 82.58, "pcie": "PCIe 4.0 x16"},
    {"year": 2022, "month": 11, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 4080", "architecture": "AD103 (Ada Lovelace)", "codename": "AD103",
     "memory_gb": 16.0, "memory_type": "GDDR6X", "memory_bus_width": "256-bit", "base_clock_mhz": 2205, "boost_clock_mhz": 2505,
     "tdp_w": 320, "process_nm": 4, "msrp": 1199, "oem": "Reference", "cuda_cores": 9728, "stream_processors": None,
     "tensor_cores": 304, "rt_cores": 76, "tmus": 304, "rops": 112, "memory_bandwidth_gbs": 716.8, "transistors_m": 45900, "die_size_mm2": 379, "tflops_fp32": 48.74, "pcie": "PCIe 4.0 x16"},
    {"year": 2023, "month": 4, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 4070 Ti", "architecture": "AD104 (Ada Lovelace)", "codename": "AD104",
     "memory_gb": 12.0, "memory_type": "GDDR6X", "memory_bus_width": "192-bit", "base_clock_mhz": 2310, "boost_clock_mhz": 2610,
     "tdp_w": 285, "process_nm": 4, "msrp": 799, "oem": "Reference", "cuda_cores": 7680, "stream_processors": None,
     "tensor_cores": 240, "rt_cores": 60, "tmus": 240, "rops": 80, "memory_bandwidth_gbs": 504.0, "transistors_m": 35800, "die_size_mm2": 294, "tflops_fp32": 40.09, "pcie": "PCIe 4.0 x16"},
    {"year": 2023, "month": 4, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 4070", "architecture": "AD104 (Ada Lovelace)", "codename": "AD104",
     "memory_gb": 12.0, "memory_type": "GDDR6", "memory_bus_width": "192-bit", "base_clock_mhz": 1920, "boost_clock_mhz": 2475,
     "tdp_w": 200, "process_nm": 4, "msrp": 599, "oem": "Reference", "cuda_cores": 5888, "stream_processors": None,
     "tensor_cores": 184, "rt_cores": 46, "tmus": 184, "rops": 64, "memory_bandwidth_gbs": 504.0, "transistors_m": 35800, "die_size_mm2": 294, "tflops_fp32": 29.15, "pcie": "PCIe 4.0 x16"},
    {"year": 2023, "month": 1, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 4070 Ti Super", "architecture": "AD103 (Ada Lovelace)", "codename": "AD103",
     "memory_gb": 16.0, "memory_type": "GDDR6X", "memory_bus_width": "256-bit", "base_clock_mhz": 2340, "boost_clock_mhz": 2610,
     "tdp_w": 285, "process_nm": 4, "msrp": 799, "oem": "Reference", "cuda_cores": 8448, "stream_processors": None,
     "tensor_cores": 264, "rt_cores": 66, "tmus": 264, "rops": 96, "memory_bandwidth_gbs": 672.0, "transistors_m": 45900, "die_size_mm2": 379, "tflops_fp32": 44.1, "pcie": "PCIe 4.0 x16"},
    {"year": 2024, "month": 1, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 4080 Super", "architecture": "AD103 (Ada Lovelace)", "codename": "AD103",
     "memory_gb": 16.0, "memory_type": "GDDR6X", "memory_bus_width": "256-bit", "base_clock_mhz": 2295, "boost_clock_mhz": 2550,
     "tdp_w": 320, "process_nm": 4, "msrp": 999, "oem": "Reference", "cuda_cores": 10240, "stream_processors": None,
     "tensor_cores": 320, "rt_cores": 80, "tmus": 320, "rops": 112, "memory_bandwidth_gbs": 736.0, "transistors_m": 45900, "die_size_mm2": 379, "tflops_fp32": 52.22, "pcie": "PCIe 4.0 x16"},
    {"year": 2023, "month": 9, "manufacturer": "AMD", "gpu_name": "Radeon RX 7800 XT", "architecture": "Navi 32 (RDNA 3)", "codename": "Navi 32",
     "memory_gb": 16.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 2124, "boost_clock_mhz": 2430,
     "tdp_w": 263, "process_nm": 5, "msrp": 499, "oem": "Reference", "cuda_cores": None, "stream_processors": 3840,
     "tmus": 240, "rops": 96, "memory_bandwidth_gbs": 624.0, "transistors_m": 28100, "die_size_mm2": 346, "tflops_fp32": 18.66, "pcie": "PCIe 4.0 x16"},
    {"year": 2022, "month": 12, "manufacturer": "AMD", "gpu_name": "Radeon RX 7900 XTX", "architecture": "Navi 31 (RDNA 3)", "codename": "Navi 31",
     "memory_gb": 24.0, "memory_type": "GDDR6", "memory_bus_width": "384-bit", "base_clock_mhz": 1900, "boost_clock_mhz": 2500,
     "tdp_w": 355, "process_nm": 5, "msrp": 999, "oem": "Reference", "cuda_cores": None, "stream_processors": 6144,
     "tmus": 384, "rops": 192, "memory_bandwidth_gbs": 960.0, "transistors_m": 57700, "die_size_mm2": 529, "tflops_fp32": 30.72, "pcie": "PCIe 4.0 x16"},
    {"year": 2022, "month": 12, "manufacturer": "AMD", "gpu_name": "Radeon RX 7900 XT", "architecture": "Navi 31 (RDNA 3)", "codename": "Navi 31",
     "memory_gb": 20.0, "memory_type": "GDDR6", "memory_bus_width": "320-bit", "base_clock_mhz": 1500, "boost_clock_mhz": 2400,
     "tdp_w": 300, "process_nm": 5, "msrp": 899, "oem": "Reference", "cuda_cores": None, "stream_processors": 5376,
     "tmus": 336, "rops": 192, "memory_bandwidth_gbs": 800.0, "transistors_m": 57700, "die_size_mm2": 529, "tflops_fp32": 25.8, "pcie": "PCIe 4.0 x16"},
    {"year": 2024, "month": 8, "manufacturer": "AMD", "gpu_name": "Radeon RX 7900 GRE", "architecture": "Navi 31 (RDNA 3)", "codename": "Navi 31",
     "memory_gb": 16.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 1270, "boost_clock_mhz": 2395,
     "tdp_w": 260, "process_nm": 5, "msrp": 649, "oem": "Reference", "cuda_cores": None, "stream_processors": 5120,
     "tmus": 320, "rops": 160, "memory_bandwidth_gbs": 576.0, "transistors_m": 57700, "die_size_mm2": 529, "tflops_fp32": 24.5, "pcie": "PCIe 4.0 x16"},

    # ===================== 2025-2026: RTX 50 (Blackwell) + RX 9000 (RDNA 4) =====================
    # From wiki + NVIDIA/AMD pages (CES 2025 launches)
    {"year": 2025, "month": 1, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 5090", "architecture": "Blackwell (GB202)", "codename": "GB202",
     "memory_gb": 32.0, "memory_type": "GDDR7", "memory_bus_width": "512-bit", "base_clock_mhz": 2017, "boost_clock_mhz": 2410,  # approx from typical
     "tdp_w": 575, "process_nm": 4, "msrp": 1999, "oem": "Reference", "cuda_cores": 21760, "stream_processors": None,
     "tensor_cores": 680, "rt_cores": 170, "tmus": 680, "rops": 176, "memory_bandwidth_gbs": 1792.0, "transistors_m": 92200, "die_size_mm2": 750, "tflops_fp32": 104.9, "pcie": "PCIe 5.0 x16", "notes": "Flagship Blackwell consumer"},
    {"year": 2025, "month": 1, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 5080", "architecture": "Blackwell (GB203)", "codename": "GB203",
     "memory_gb": 16.0, "memory_type": "GDDR7", "memory_bus_width": "256-bit", "base_clock_mhz": 2295, "boost_clock_mhz": 2610,
     "tdp_w": 320, "process_nm": 4, "msrp": 999, "oem": "Reference", "cuda_cores": 10752, "stream_processors": None,
     "tensor_cores": 336, "rt_cores": 84, "tmus": 336, "rops": 112, "memory_bandwidth_gbs": 896.0, "transistors_m": 45600, "die_size_mm2": 378, "tflops_fp32": 56.1, "pcie": "PCIe 5.0 x16"},
    {"year": 2025, "month": 2, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 5070 Ti", "architecture": "Blackwell (GB203)", "codename": "GB203",
     "memory_gb": 16.0, "memory_type": "GDDR7", "memory_bus_width": "256-bit", "base_clock_mhz": 2160, "boost_clock_mhz": 2452,
     "tdp_w": 285, "process_nm": 4, "msrp": 749, "oem": "Reference", "cuda_cores": 8960, "stream_processors": None,
     "tensor_cores": 280, "rt_cores": 70, "tmus": 280, "rops": 96, "memory_bandwidth_gbs": 672.0, "transistors_m": 45600, "die_size_mm2": 378, "tflops_fp32": 43.9, "pcie": "PCIe 5.0 x16"},
    {"year": 2025, "month": 3, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 5070", "architecture": "Blackwell (GB205)", "codename": "GB205",
     "memory_gb": 12.0, "memory_type": "GDDR7", "memory_bus_width": "192-bit", "base_clock_mhz": 2160, "boost_clock_mhz": 2452,
     "tdp_w": 220, "process_nm": 4, "msrp": 549, "oem": "Reference", "cuda_cores": 6144, "stream_processors": None,
     "tensor_cores": 192, "rt_cores": 48, "tmus": 192, "rops": 80, "memory_bandwidth_gbs": 504.0, "transistors_m": 31100, "die_size_mm2": 263, "tflops_fp32": 30.1, "pcie": "PCIe 5.0 x16"},
    {"year": 2025, "month": 4, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 5060 Ti 16GB", "architecture": "Blackwell (GB206)", "codename": "GB206",
     "memory_gb": 16.0, "memory_type": "GDDR7", "memory_bus_width": "128-bit", "base_clock_mhz": 2280, "boost_clock_mhz": 2580,
     "tdp_w": 180, "process_nm": 4, "msrp": 429, "oem": "Reference", "cuda_cores": 4608, "stream_processors": None,
     "tensor_cores": 144, "rt_cores": 36, "tmus": 144, "rops": 64, "memory_bandwidth_gbs": 448.0, "transistors_m": 21900, "die_size_mm2": 181, "tflops_fp32": 23.8, "pcie": "PCIe 5.0 x16"},
    {"year": 2025, "month": 4, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 5060 Ti 8GB", "architecture": "Blackwell (GB206)", "codename": "GB206",
     "memory_gb": 8.0, "memory_type": "GDDR7", "memory_bus_width": "128-bit", "base_clock_mhz": 2280, "boost_clock_mhz": 2580,
     "tdp_w": 160, "process_nm": 4, "msrp": 379, "oem": "Reference", "cuda_cores": 4608, "stream_processors": None,
     "tensor_cores": 144, "rt_cores": 36, "tmus": 144, "rops": 64, "memory_bandwidth_gbs": 288.0, "transistors_m": 21900, "die_size_mm2": 181, "tflops_fp32": 23.8, "pcie": "PCIe 5.0 x16"},
    {"year": 2025, "month": 5, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 5060", "architecture": "Blackwell (GB206)", "codename": "GB206",
     "memory_gb": 8.0, "memory_type": "GDDR7", "memory_bus_width": "128-bit", "base_clock_mhz": 2280, "boost_clock_mhz": 2497,
     "tdp_w": 145, "process_nm": 4, "msrp": 299, "oem": "Reference", "cuda_cores": 3840, "stream_processors": None,
     "tensor_cores": 120, "rt_cores": 30, "tmus": 120, "rops": 48, "memory_bandwidth_gbs": 288.0, "transistors_m": 21900, "die_size_mm2": 181, "tflops_fp32": 19.2, "pcie": "PCIe 5.0 x16"},
    {"year": 2025, "month": 7, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 5050", "architecture": "Blackwell (GB207)", "codename": "GB207",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "128-bit", "base_clock_mhz": 2310, "boost_clock_mhz": 2505,
     "tdp_w": 130, "process_nm": 4, "msrp": 249, "oem": "Reference", "cuda_cores": 2560, "stream_processors": None,
     "tensor_cores": 80, "rt_cores": 20, "tmus": 80, "rops": 48, "memory_bandwidth_gbs": 224.0, "transistors_m": 16900, "die_size_mm2": 149, "tflops_fp32": 12.8, "pcie": "PCIe 5.0 x16"},

    # AMD RX 9000 RDNA 4 (2025)
    {"year": 2025, "month": 3, "manufacturer": "AMD", "gpu_name": "Radeon RX 9070 XT", "architecture": "RDNA 4 (Navi 48)", "codename": "Navi 48",
     "memory_gb": 16.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 2070, "boost_clock_mhz": 2970,
     "tdp_w": 304, "process_nm": 4, "msrp": 599, "oem": "Reference", "cuda_cores": None, "stream_processors": 4096,
     "tmus": 256, "rops": 128, "memory_bandwidth_gbs": 640.0, "transistors_m": 53900, "die_size_mm2": 356.5, "tflops_fp32": 48.7, "pcie": "PCIe 5.0 x16", "notes": "High-end RDNA 4"},
    {"year": 2025, "month": 3, "manufacturer": "AMD", "gpu_name": "Radeon RX 9070", "architecture": "RDNA 4 (Navi 48)", "codename": "Navi 48",
     "memory_gb": 16.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 2070, "boost_clock_mhz": 2520,
     "tdp_w": 220, "process_nm": 4, "msrp": 549, "oem": "Reference", "cuda_cores": None, "stream_processors": 3584,
     "tmus": 224, "rops": 128, "memory_bandwidth_gbs": 640.0, "transistors_m": 53900, "die_size_mm2": 356.5, "tflops_fp32": 36.1, "pcie": "PCIe 5.0 x16"},
    {"year": 2025, "month": 6, "manufacturer": "AMD", "gpu_name": "Radeon RX 9070 GRE", "architecture": "RDNA 4 (Navi 48)", "codename": "Navi 48",
     "memory_gb": 12.0, "memory_type": "GDDR6", "memory_bus_width": "192-bit", "base_clock_mhz": 2220, "boost_clock_mhz": 2790,
     "tdp_w": 220, "process_nm": 4, "msrp": 549, "oem": "Reference", "cuda_cores": None, "stream_processors": 3072,
     "tmus": 192, "rops": 96, "memory_bandwidth_gbs": 432.0, "transistors_m": 53900, "die_size_mm2": 356.5, "tflops_fp32": 34.3, "pcie": "PCIe 5.0 x16"},
    {"year": 2025, "month": 6, "manufacturer": "AMD", "gpu_name": "Radeon RX 9060 XT 16GB", "architecture": "RDNA 4 (Navi 44/48)", "codename": "Navi 44",
     "memory_gb": 16.0, "memory_type": "GDDR6", "memory_bus_width": "128-bit", "base_clock_mhz": 2530, "boost_clock_mhz": 3130,
     "tdp_w": 160, "process_nm": 4, "msrp": 349, "oem": "Reference", "cuda_cores": None, "stream_processors": 2048,
     "tmus": 128, "rops": 64, "memory_bandwidth_gbs": 320.0, "transistors_m": 29700, "die_size_mm2": 199, "tflops_fp32": 25.6, "pcie": "PCIe 5.0 x16"},
    {"year": 2025, "month": 8, "manufacturer": "AMD", "gpu_name": "Radeon RX 9060", "architecture": "RDNA 4 (Navi 44)", "codename": "Navi 44",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "128-bit", "base_clock_mhz": 2400, "boost_clock_mhz": 2990,
     "tdp_w": 132, "process_nm": 4, "msrp": 299, "oem": "Reference", "cuda_cores": None, "stream_processors": 1792,
     "tmus": 112, "rops": 64, "memory_bandwidth_gbs": 288.0, "transistors_m": 29700, "die_size_mm2": 199, "tflops_fp32": 21.4, "pcie": "PCIe 5.0 x16"},

    # Intel Arc (Alchemist desktop discrete consumer, 2022+)
    {"year": 2022, "month": 10, "manufacturer": "Intel", "gpu_name": "Arc A770", "architecture": "Alchemist (Xe-HPG)", "codename": "ACM-G10",
     "memory_gb": 16.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 2100, "boost_clock_mhz": 2400,
     "tdp_w": 225, "process_nm": 6, "msrp": 349, "oem": "Reference", "cuda_cores": None, "stream_processors": 4096,  # Xe cores / vector engines
     "tmus": 256, "rops": 128, "memory_bandwidth_gbs": 512.0, "transistors_m": 21700, "die_size_mm2": 406, "tflops_fp32": 19.7, "pcie": "PCIe 4.0 x16", "notes": "Intel first gen discrete desktop Arc"},
    {"year": 2022, "month": 10, "manufacturer": "Intel", "gpu_name": "Arc A750", "architecture": "Alchemist (Xe-HPG)", "codename": "ACM-G10",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 2050, "boost_clock_mhz": 2350,
     "tdp_w": 225, "process_nm": 6, "msrp": 289, "oem": "Reference", "cuda_cores": None, "stream_processors": 3584,
     "tmus": 224, "rops": 128, "memory_bandwidth_gbs": 512.0, "transistors_m": 21700, "die_size_mm2": 406, "tflops_fp32": 17.0, "pcie": "PCIe 4.0 x16"},
    {"year": 2022, "month": 10, "manufacturer": "Intel", "gpu_name": "Arc A580", "architecture": "Alchemist (Xe-HPG)", "codename": "ACM-G10",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 1700, "boost_clock_mhz": 1700,
     "tdp_w": 175, "process_nm": 6, "msrp": 179, "oem": "Reference", "cuda_cores": None, "stream_processors": 3072,
     "tmus": 192, "rops": 96, "memory_bandwidth_gbs": 384.0, "transistors_m": 21700, "die_size_mm2": 406, "tflops_fp32": 10.5, "pcie": "PCIe 4.0 x16"},

    # ===================== Additional popular consumer models for completeness (mid-range + more variants) =====================
    # GeForce 6/7 more
    {"year": 2004, "month": 9, "manufacturer": "NVIDIA", "gpu_name": "GeForce 6600 GT", "architecture": "NV43", "codename": "NV43",
     "memory_gb": 0.128, "memory_type": "GDDR3", "memory_bus_width": "128-bit", "base_clock_mhz": 500, "boost_clock_mhz": 500,
     "tdp_w": 50, "process_nm": 130, "msrp": 199, "oem": "Reference", "cuda_cores": None, "stream_processors": None,
     "tmus": 8, "rops": 8, "memory_bandwidth_gbs": 16.0, "transistors_m": 146, "die_size_mm2": 150, "tflops_fp32": None, "pcie": "PCIe 1.0 x16"},
    # Pascal mid
    {"year": 2016, "month": 7, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 1060 6GB", "architecture": "GP106 (Pascal)", "codename": "GP106",
     "memory_gb": 6.0, "memory_type": "GDDR5", "memory_bus_width": "192-bit", "base_clock_mhz": 1506, "boost_clock_mhz": 1709,
     "tdp_w": 120, "process_nm": 16, "msrp": 249, "oem": "Reference", "cuda_cores": 1280, "stream_processors": None,
     "tmus": 80, "rops": 48, "memory_bandwidth_gbs": 192.2, "transistors_m": 4400, "die_size_mm2": 200, "tflops_fp32": 4.38, "pcie": "PCIe 3.0 x16"},
    {"year": 2016, "month": 7, "manufacturer": "NVIDIA", "gpu_name": "GeForce GTX 1060 3GB", "architecture": "GP106 (Pascal)", "codename": "GP106",
     "memory_gb": 3.0, "memory_type": "GDDR5", "memory_bus_width": "192-bit", "base_clock_mhz": 1506, "boost_clock_mhz": 1709,
     "tdp_w": 120, "process_nm": 16, "msrp": 199, "oem": "Reference", "cuda_cores": 1152, "stream_processors": None,
     "tmus": 72, "rops": 48, "memory_bandwidth_gbs": 192.2, "transistors_m": 4400, "die_size_mm2": 200, "tflops_fp32": 3.94, "pcie": "PCIe 3.0 x16"},
    # Turing
    {"year": 2019, "month": 1, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 2060", "architecture": "TU106 (Turing)", "codename": "TU106",
     "memory_gb": 6.0, "memory_type": "GDDR6", "memory_bus_width": "192-bit", "base_clock_mhz": 1365, "boost_clock_mhz": 1680,
     "tdp_w": 160, "process_nm": 12, "msrp": 349, "oem": "Reference", "cuda_cores": 1920, "stream_processors": None,
     "tensor_cores": 240, "rt_cores": 30, "tmus": 120, "rops": 48, "memory_bandwidth_gbs": 336.0, "transistors_m": 10800, "die_size_mm2": 445, "tflops_fp32": 6.45, "pcie": "PCIe 3.0 x16"},
    {"year": 2019, "month": 7, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 2060 Super", "architecture": "TU106 (Turing)", "codename": "TU106",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 1470, "boost_clock_mhz": 1650,
     "tdp_w": 175, "process_nm": 12, "msrp": 399, "oem": "Reference", "cuda_cores": 2176, "stream_processors": None,
     "tensor_cores": 272, "rt_cores": 34, "tmus": 136, "rops": 64, "memory_bandwidth_gbs": 448.0, "transistors_m": 10800, "die_size_mm2": 445, "tflops_fp32": 7.18, "pcie": "PCIe 3.0 x16"},
    # Ampere popular
    {"year": 2021, "month": 2, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 3060", "architecture": "GA106 (Ampere)", "codename": "GA106",
     "memory_gb": 12.0, "memory_type": "GDDR6", "memory_bus_width": "192-bit", "base_clock_mhz": 1320, "boost_clock_mhz": 1777,
     "tdp_w": 170, "process_nm": 8, "msrp": 329, "oem": "Reference", "cuda_cores": 3584, "stream_processors": None,
     "tensor_cores": 112, "rt_cores": 28, "tmus": 112, "rops": 48, "memory_bandwidth_gbs": 360.0, "transistors_m": 13200, "die_size_mm2": 276, "tflops_fp32": 12.74, "pcie": "PCIe 4.0 x16"},
    {"year": 2021, "month": 9, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 3060 Ti", "architecture": "GA104 (Ampere)", "codename": "GA104",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "256-bit", "base_clock_mhz": 1410, "boost_clock_mhz": 1665,
     "tdp_w": 200, "process_nm": 8, "msrp": 399, "oem": "Reference", "cuda_cores": 4864, "stream_processors": None,
     "tensor_cores": 152, "rt_cores": 38, "tmus": 152, "rops": 80, "memory_bandwidth_gbs": 448.0, "transistors_m": 17400, "die_size_mm2": 392, "tflops_fp32": 16.2, "pcie": "PCIe 4.0 x16"},
    # Ada more
    {"year": 2023, "month": 6, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 4060 Ti", "architecture": "AD106 (Ada Lovelace)", "codename": "AD106",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "128-bit", "base_clock_mhz": 2310, "boost_clock_mhz": 2535,
     "tdp_w": 160, "process_nm": 4, "msrp": 399, "oem": "Reference", "cuda_cores": 4352, "stream_processors": None,
     "tensor_cores": 136, "rt_cores": 34, "tmus": 136, "rops": 48, "memory_bandwidth_gbs": 288.0, "transistors_m": 22900, "die_size_mm2": 187, "tflops_fp32": 22.06, "pcie": "PCIe 4.0 x16"},
    {"year": 2023, "month": 6, "manufacturer": "NVIDIA", "gpu_name": "GeForce RTX 4060", "architecture": "AD107 (Ada Lovelace)", "codename": "AD107",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "128-bit", "base_clock_mhz": 1830, "boost_clock_mhz": 2460,
     "tdp_w": 115, "process_nm": 4, "msrp": 299, "oem": "Reference", "cuda_cores": 3072, "stream_processors": None,
     "tensor_cores": 96, "rt_cores": 24, "tmus": 96, "rops": 48, "memory_bandwidth_gbs": 272.0, "transistors_m": 18900, "die_size_mm2": 159, "tflops_fp32": 15.11, "pcie": "PCIe 4.0 x16"},
    # RDNA2 mid
    {"year": 2021, "month": 8, "manufacturer": "AMD", "gpu_name": "Radeon RX 6600 XT", "architecture": "Navi 23 (RDNA 2)", "codename": "Navi 23",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "128-bit", "base_clock_mhz": 1968, "boost_clock_mhz": 2589,
     "tdp_w": 160, "process_nm": 7, "msrp": 379, "oem": "Reference", "cuda_cores": None, "stream_processors": 2048,
     "tmus": 128, "rops": 64, "memory_bandwidth_gbs": 256.0, "transistors_m": 11000, "die_size_mm2": 237, "tflops_fp32": 10.6, "pcie": "PCIe 4.0 x16"},
    {"year": 2021, "month": 10, "manufacturer": "AMD", "gpu_name": "Radeon RX 6600", "architecture": "Navi 23 (RDNA 2)", "codename": "Navi 23",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "128-bit", "base_clock_mhz": 1626, "boost_clock_mhz": 2491,
     "tdp_w": 132, "process_nm": 7, "msrp": 329, "oem": "Reference", "cuda_cores": None, "stream_processors": 1792,
     "tmus": 112, "rops": 64, "memory_bandwidth_gbs": 224.0, "transistors_m": 11000, "die_size_mm2": 237, "tflops_fp32": 8.93, "pcie": "PCIe 4.0 x16"},
    # RDNA3 mid
    {"year": 2023, "month": 5, "manufacturer": "AMD", "gpu_name": "Radeon RX 7600", "architecture": "Navi 33 (RDNA 3)", "codename": "Navi 33",
     "memory_gb": 8.0, "memory_type": "GDDR6", "memory_bus_width": "128-bit", "base_clock_mhz": 1720, "boost_clock_mhz": 2655,
     "tdp_w": 165, "process_nm": 6, "msrp": 269, "oem": "Reference", "cuda_cores": None, "stream_processors": 2048,
     "tmus": 128, "rops": 64, "memory_bandwidth_gbs": 288.0, "transistors_m": 13300, "die_size_mm2": 204, "tflops_fp32": 10.9, "pcie": "PCIe 4.0 x16"},
    {"year": 2023, "month": 9, "manufacturer": "AMD", "gpu_name": "Radeon RX 7700 XT", "architecture": "Navi 32 (RDNA 3)", "codename": "Navi 32",
     "memory_gb": 12.0, "memory_type": "GDDR6", "memory_bus_width": "192-bit", "base_clock_mhz": 2171, "boost_clock_mhz": 2544,
     "tdp_w": 245, "process_nm": 5, "msrp": 449, "oem": "Reference", "cuda_cores": None, "stream_processors": 3456,
     "tmus": 216, "rops": 96, "memory_bandwidth_gbs": 432.0, "transistors_m": 28100, "die_size_mm2": 346, "tflops_fp32": 17.6, "pcie": "PCIe 4.0 x16"},
]

TICKER_MAP = {
    "NVIDIA": "NVDA",
    "AMD": "AMD",
    "Intel": "INTC",  # For completeness
}

SOURCES = [
    "1. Wikipedia - List of Nvidia graphics processing units (detailed tables for specs, launch dates, architecture, memory, clocks, transistors)",
    "2. Wikipedia - List of AMD graphics processing units (and Radeon RX 9000 series, GeForce RTX 50 series dedicated pages)",
    "3. NVIDIA official GeForce RTX 50 series pages and compare tools (MSRP, key specs for 5090/5080/5070 etc.)",
    "4. AMD official Radeon RX 9000 series pages (RDNA 4 specs, MSRPs, release dates)",
    "5. TechPowerUp GPU Database (cross-reference for core counts, bandwidth, process, die size, TDP)",
    "6. Contemporaneous reviews and launch coverage (Tom's Hardware, AnandTech archives, Hardware Unboxed) for MSRP validation and additional details",
    "Additional: Internet Archive snapshots for pre-2015 MSRPs where public wiki data was limited; official press releases."
]

def emit_sources_provenance(out_path: Path):
    prov = out_path.with_suffix(out_path.suffix + ".sources.txt")
    with open(prov, "w", encoding="utf-8") as f:
        f.write("GPU-26-Years.csv data gathered/validated from:\n")
        for s in SOURCES:
            f.write(f"- {s}\n")
        f.write("\n26-year span (approx 2000-2026). Consumer desktop discrete GPUs (GeForce, Radeon RX/HD, key Arc).\n")
        f.write("Detailed fields included where publicly documented. MSRP are launch reference prices.\n")
        f.write("Stock prices fetched at generation time via yfinance (split-adjusted).\n")
    print(f"Sources provenance written to {prov}")

def get_stock_close(ticker: str, year: int, month: int) -> tuple:
    """Return (price, used_date_str) using the Close on or before mid-month target."""
    if ticker not in ("NVDA", "AMD", "INTC"):
        return "N/A", f"{year}-{month:02d}-15"

    target = datetime(year, month, 15)
    start = (target - timedelta(days=12)).strftime("%Y-%m-%d")
    end = (target + timedelta(days=7)).strftime("%Y-%m-%d")

    try:
        hist = yf.download(
            ticker,
            start=start,
            end=end,
            progress=False,
            auto_adjust=False,
            threads=False,
        )
    except Exception:
        return "N/A", target.strftime("%Y-%m-%d")

    if hist.empty:
        return "N/A", target.strftime("%Y-%m-%d")

    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)

    hist = hist.sort_index(ascending=False)

    close_col = "Close" if "Close" in hist.columns else "Adj Close"
    for idx in hist.index:
        if idx.date() <= target.date():
            val = hist.loc[idx, close_col]
            try:
                close = float(val)
            except Exception:
                close = float(val.iloc[0]) if hasattr(val, "iloc") else 0.0
            return round(close, 2), idx.strftime("%Y-%m-%d")

    val = hist.iloc[-1][close_col]
    try:
        close = float(val)
    except Exception:
        close = float(val.iloc[0]) if hasattr(val, "iloc") else 0.0
    return round(close, 2), hist.index[-1].strftime("%Y-%m-%d")

def main():
    parser = argparse.ArgumentParser(description="Generate detailed 26-year consumer GPU CSV")
    parser.add_argument(
        "--output", "-o", default="GPU-26-Years.csv",
        help="Output CSV filename (default: GPU-26-Years.csv)"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limit number of rows (for testing)"
    )
    args = parser.parse_args()

    out_path = Path(args.output)

    data_to_use = DATA[: args.limit] if args.limit > 0 else DATA

    rows = []
    for item in data_to_use:
        ticker = TICKER_MAP.get(item["manufacturer"], "N/A")
        price, used_date = get_stock_close(ticker, item["year"], item["month"])

        msrp = item.get("msrp")
        cuda = item.get("cuda_cores")
        sp = item.get("stream_processors")
        tc = item.get("tensor_cores")
        rtc = item.get("rt_cores")
        base = item.get("base_clock_mhz", item.get("boost_clock_mhz"))
        notes = item.get("notes", "")

        rows.append({
            "Released_Year": item["year"],
            "Released_Month": item["month"],
            "Manufacturer": item["manufacturer"],
            "OEM": item.get("oem", "Reference"),
            "MSRP_USD": msrp if msrp is not None else "",
            "GPU_Name": item["gpu_name"],
            "Architecture": item["architecture"],
            "Codename": item.get("codename", ""),
            "Memory_GB": item["memory_gb"],
            "Memory_Type": item["memory_type"],
            "Memory_Bus_Width": item.get("memory_bus_width", ""),
            "Memory_Bandwidth_GBs": item.get("memory_bandwidth_gbs", ""),
            "Base_Clock_MHz": base if base is not None else "",
            "Boost_Clock_MHz": item["boost_clock_mhz"],
            "CUDA_Cores": cuda if cuda is not None else "",
            "Stream_Processors": sp if sp is not None else "",
            "Tensor_Cores": tc if tc is not None else "",
            "RT_Cores": rtc if rtc is not None else "",
            "TMUs": item.get("tmus", ""),
            "ROPs": item.get("rops", ""),
            "TDP_W": item["tdp_w"],
            "Process_nm": item["process_nm"],
            "Transistors_M": item.get("transistors_m", ""),
            "Die_Size_mm2": item.get("die_size_mm2", ""),
            "TFLOPS_FP32": item.get("tflops_fp32", ""),
            "PCIe": item.get("pcie", ""),
            "Stock_Price": price,
            "Stock_Date": used_date,
            "Notes": notes,
        })

    emit_sources_provenance(out_path)

    # Sort by date then manufacturer
    rows.sort(key=lambda r: (r["Released_Year"], r["Released_Month"], r["Manufacturer"], r["GPU_Name"]))

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    first_year = rows[0]["Released_Year"]
    last_year = rows[-1]["Released_Year"]
    print(f"Wrote {len(rows)} rows to {out_path.resolve()}")
    print(f"Date range: {first_year} – {last_year}")
    print("Columns: " + ", ".join(rows[0].keys()))

if __name__ == "__main__":
    main()
