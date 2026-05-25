---
name: visualization
description: Publication-quality plots for causal inference — coefficient forests, event study, balance Love plots, DAG graphs.
workflow_stage: communication
compatibility:
  - claude-code
author: Causal Agent System
version: 1.0.0
tags:
  - python
  - visualization
  - matplotlib
  - seaborn
  - plots
---

# Visualization

## Purpose

Create publication-quality visualizations for causal inference results. Supports Chinese fonts for enterprise reports. Each plot type is tailored to a specific causal method.

## When to Use

- Presenting causal analysis results to stakeholders
- Creating diagnostic plots for model validation
- Generating figures for reports and presentations
- Need Chinese-language labels in plots

## Instructions

### Step 1: Choose Plot Type

| Method | Plot | Purpose |
|--------|------|---------|
| PSM | Propensity score distribution + Love plot | Show matching quality and balance improvement |
| DiD | Coefficient plot with CIs | Show treatment effect and pre-trend coefficients |
| Panel | Coefficient forest plot | Show all regression coefficients with significance |
| RDD | Scatter with fitted lines | Show discontinuity at threshold |
| DAG | Network graph | Show causal structure |
| DML | HTE histogram + Feature importance | Show effect heterogeneity |

### Step 2: Generate Plot

```python
from src.visualization import coefficient_forest, balance_love

# Coefficient forest
coefficient_forest(
    coefs={"marketing": 0.05, "training": 0.03},
    ci_lower={"marketing": 0.02, "training": 0.01},
    ci_upper={"marketing": 0.08, "training": 0.05},
    pvalues={"marketing": 0.001, "training": 0.04},
    title="Factors Affecting Renewal Rate",
    output_path="./output/graphs/coefficients.png",
)

# Balance Love plot (PSM)
balance_love(
    smd_before={"x1": 0.25, "x2": 0.18},
    smd_after={"x1": 0.05, "x2": 0.03},
    output_path="./output/graphs/balance_love.png",
)
```

### Step 3: Style

All plots use:
- Whitegrid seaborn style
- Chinese font support (Microsoft YaHei / SimHei)
- 150 DPI for crisp rendering
- Consistent color palette: green for significant, gray for not

## Requirements

- Python 3.10+
- `matplotlib`, `seaborn`, `numpy`
- Optional: Chinese fonts (Microsoft YaHei or SimHei) for Chinese labels

## Best Practices

1. Use consistent color coding: green=significant, red=baseline, gray=insignificant
2. Always include confidence intervals
3. Add significance stars or p-values directly on plots
4. Use vector format (SVG/PDF) for publication, PNG for reports

## References

- [matplotlib documentation](https://matplotlib.org/)
- [seaborn documentation](https://seaborn.pydata.org/)

## Changelog

### v1.0.0
- Initial release: coefficient forest, event study, balance Love plot, DAG graph
