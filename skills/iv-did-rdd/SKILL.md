---
name: iv-did-rdd
description: Instrumental Variables, Difference-in-Differences, and Regression Discontinuity Design for causal inference with quasi-experimental variation.
workflow_stage: analysis
compatibility:
  - claude-code
author: Causal Agent System
version: 1.0.0
tags:
  - python
  - iv
  - did
  - rdd
  - causal-inference
  - econometrics
---

# IV, DiD, and RDD

## Purpose

Implement the three most common quasi-experimental causal inference methods:
- **IV (2SLS)**: When treatment is endogenous but a valid instrument exists
- **DiD**: When there are pre/post time periods and treatment/control groups
- **RDD**: When treatment assignment has a sharp cutoff/threshold

## When to Use

### Instrumental Variables
- Suspected endogeneity in treatment variable
- Have a variable that affects treatment but not outcome directly
- Key diagnostic: First-stage F-statistic > 10

### Difference-in-Differences
- Panel data with pre-treatment and post-treatment periods
- Some entities receive treatment, others don't
- Key diagnostic: Parallel trends test (pre-treatment coefficients not significant)

### Regression Discontinuity
- Treatment assigned based on a threshold (score, age, distance)
- Running variable is continuous around the cutoff
- Key diagnostic: McCrary density test (no manipulation at threshold)

## Instructions

### Step 1: Choose Method Based on Data Structure

Ask the user or auto-detect:
- **For DiD**: "Does the data have time periods before and after an intervention?"
- **For IV**: "Is there a variable that affects the treatment but not the outcome?"
- **For RDD**: "Is treatment assigned based on a cutoff value?"

### Step 2: Run Analysis

```python
from src.causal_models import DifferenceInDifferences, InstrumentalVariable, RegressionDiscontinuity

# DiD
did = DifferenceInDifferences(data=df, effect="outcome", treatment="treated", causes=confounders)
result_did = did.run()

# IV
iv = InstrumentalVariable(data=df, effect="outcome", treatment="endog_var", causes=confounders)
result_iv = iv.fit(instrument="policy_change").run()

# RDD
rdd = RegressionDiscontinuity(data=df, effect="outcome", treatment="treatment", causes=confounders)
result_rdd = rdd.fit(running_variable="score", threshold=60).run()
```

### Step 3: Interpret Diagnostics

- **DiD**: Check `parallel_trends_concern` — if True, pre-trends differ
- **IV**: Check `first_stage_f` — if < 10, weak instrument problem
- **RDD**: Check `mccrary_concern` — if True, possible manipulation at threshold

## Requirements

- Python 3.10+
- `pandas`, `statsmodels`, `numpy`, `scipy`
- Optional: `linearmodels` (for more efficient IV estimation)

## Best Practices

1. **DiD**: Always show event study plot; test parallel trends
2. **IV**: Report first-stage F-statistic; use LIML if weak instruments
3. **RDD**: Use optimal bandwidth (IK); test density at cutoff
4. Report robustness checks for all methods

## Common Pitfalls

- DiD with staggered treatment timing (use modern DiD estimators)
- IV with weak instruments (F < 10)
- RDD with too-wide bandwidth (bias) or too-narrow (variance)

## References

- Cunningham (2021) Causal Inference: The Mixtape
- Angrist & Pischke (2009) Mostly Harmless Econometrics

## Changelog

### v1.0.0
- Initial release: DiD, IV (2SLS), Sharp RDD with diagnostics
