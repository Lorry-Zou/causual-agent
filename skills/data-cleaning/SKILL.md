---
name: data-cleaning
description: Clean and prepare enterprise data for causal analysis. Handles missing values, outliers, type inference, and encoding.
workflow_stage: data
compatibility:
  - claude-code
author: Causal Agent System
version: 1.0.0
tags:
  - python
  - pandas
  - data-cleaning
  - preprocessing
---

# Data Cleaning

## Purpose

Clean enterprise datasets for causal inference analysis. Real-world business data is often messy — missing values, outliers, mixed types, encoding issues. This skill provides a systematic cleaning workflow.

## When to Use

- Loading CSV, Excel, JSON, Stata, or Parquet data files
- Data has missing values that need imputation
- Outliers need detection and treatment
- Variable types need to be inferred (continuous vs categorical vs binary vs datetime)
- Need EDA visualizations (missingness heatmap, correlation matrix)

## Instructions

### Step 1: Load and Inspect

Use `src/data_processing.py`:
```python
from src.data_processing import DataLoader, TypeInference

loader = DataLoader()
df = loader.load("data.csv")  # auto-detects format, encoding, delimiter

ti = TypeInference()
meta = ti.infer(df)  # classifies each column
```

### Step 2: Clean

```python
from src.data_processing import DataCleaner

cleaner = DataCleaner(config)
df_clean, meta, stats = cleaner.run("data.csv")
```

This automatically:
1. Removes duplicate rows
2. Drops columns with >50% missing values
3. Imputes remaining missing values (median for continuous, mode for categorical)
4. Winsorizes outliers (IQR method, 1.5x)
5. Parses datetime columns
6. Generates EDA plots

### Step 3: Verify

Check the cleaning report:
- How many missing values were imputed and by what method
- Which columns had outliers and how many values were winsorized
- Pre/post shape comparison

## Requirements

- Python 3.10+
- Packages: `pandas`, `numpy`, `scipy`, `scikit-learn`, `matplotlib`, `seaborn`

## Common Pitfalls

- Chinese-encoded CSV files (GBK/GB2312) — the loader auto-detects encoding
- Datetime columns stored as strings — type inference handles conversion
- Categorical columns with too many unique values — check the `categorical_max_unique` threshold

## References

- [pandas documentation](https://pandas.pydata.org/docs/)
- [scikit-learn imputation](https://scikit-learn.org/stable/modules/impute.html)

## Changelog

### v1.0.0
- Initial release: loading, cleaning, imputation, outlier handling, type inference, EDA
