---
name: panel-data
description: Panel data analysis with fixed effects, random effects, and Hausman test. For enterprise panel data with entity and time dimensions.
workflow_stage: analysis
compatibility:
  - claude-code
author: Causal Agent System
version: 1.0.0
tags:
  - python
  - panel-data
  - fixed-effects
  - linearmodels
---

# Panel Data Analysis

## Purpose

Run panel data regressions for causal inference when data has both entity (company, individual) and time (year, month) dimensions. Supports fixed effects and random effects models with clustered standard errors.

## When to Use

- Data has entity ID + time columns (panel structure)
- Want to control for unobserved entity-level heterogeneity
- Estimating within-entity treatment effects over time
- Need to choose between FE and RE via Hausman test

## Instructions

### Step 1: Identify Panel Structure

Ask the user or auto-detect:
- Which column identifies entities? (company_id, firm_code, etc.)
- Which column identifies time periods? (year, date, etc.)
- Is the panel balanced or unbalanced?

### Step 2: Run Panel Regression

```python
from src.causal_models import PanelRegression

model = PanelRegression(
    data=df_clean,
    effect="revenue",
    treatment="marketing_spend",
    causes=["employee_count", "training_hours", "region"],
)
result = model.run()
```

The model automatically:
1. Detects entity and time columns
2. Sets MultiIndex for panel structure
3. Runs Fixed Effects (PanelOLS) with entity-clustered SE
4. Runs Random Effects for Hausman comparison
5. Falls back to OLS with entity dummies if linearmodels unavailable

### Step 3: Interpret Results

- **Hausman preference**: If FE is preferred, entity-specific effects are important
- **R-squared (within)**: How much variation within entities is explained
- **Coefficient**: The within-entity effect of treatment on outcome

## Requirements

- Python 3.10+
- `pandas`, `statsmodels`, `numpy`
- Optional: `linearmodels` (for more efficient panel estimation; falls back to statsmodels OLS if unavailable)

## Best Practices

1. Always cluster standard errors at the entity level
2. Run Hausman test to justify FE vs RE choice
3. Check for balanced vs unbalanced panel
4. Be cautious with time-varying treatments in FE models

## Common Pitfalls

- Forgetting to set proper panel index
- Using pooled OLS when fixed effects are needed
- Interpreting coefficients as cross-sectional rather than within-entity effects

## References

- [linearmodels documentation](https://bashtage.github.io/linearmodels/)
- Wooldridge (2010) Econometric Analysis of Cross Section and Panel Data

## Changelog

### v1.0.0
- Initial release: PanelOLS, RandomEffects, Hausman test, OLS fallback
