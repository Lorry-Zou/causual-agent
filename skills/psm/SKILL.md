---
name: psm
description: Propensity Score Matching for causal inference with observational data. Includes nearest-neighbor matching, balance diagnostics, and Love plots.
workflow_stage: analysis
compatibility:
  - claude-code
author: Causal Agent System
version: 1.0.0
tags:
  - python
  - psm
  - propensity-score
  - matching
  - causal-inference
---

# Propensity Score Matching

## Purpose

Estimate causal effects from observational data by matching treated and control units with similar propensity scores. Reduces selection bias by balancing observed confounders between groups.

## When to Use

- Cross-sectional (or pooled) data, not panel
- Binary treatment variable (treated vs not treated)
- Observable confounders exist that affect both treatment and outcome
- No clear instrument or natural experiment available

## Instructions

### Step 1: Prepare Data

Ensure:
- Treatment variable is binary (will be binarized at median if continuous)
- Confounders are numeric (continuous or binary)
- Outcome is continuous
- Sample size > 100 (more is better for matching)

### Step 2: Run PSM

```python
from src.causal_models import PropensityScoreMatching

psm = PropensityScoreMatching(
    data=df_clean,
    effect="outcome",
    treatment="treatment",
    causes=confounders,
)
result = psm.run()
```

The model automatically:
1. Estimates propensity scores via logistic regression
2. Performs 1:1 nearest-neighbor matching (no replacement)
3. Computes ATT (Average Treatment effect on the Treated)
4. Generates balance diagnostics (SMD before/after)
5. Plots propensity score distributions

### Step 3: Evaluate Balance

Key diagnostic: **SMD after matching should be < 0.1** for all confounders.
- `smd_before_mean` vs `smd_after_mean`: should decrease after matching
- `balance_improved`: should be True
- Love plot visualizes reduction in SMD per variable

## Requirements

- Python 3.10+
- `pandas`, `numpy`, `scipy`, `scikit-learn`, `matplotlib`

## Best Practices

1. Check common support (overlap in propensity scores)
2. Use caliper matching for better balance
3. Report SMD for all confounders before and after
4. Combine with sensitivity analysis (Rosenbaum bounds)

## Common Pitfalls

- Matching on too many confounders (curse of dimensionality)
- Poor overlap in propensity scores (extrapolation)
- Ignoring unobserved confounders
- Using PSM on panel data without accounting for time

## References

- Rosenbaum & Rubin (1983) The Central Role of the Propensity Score
- Caliendo & Kopeinig (2008) Some Practical Guidance for PSM

## Changelog

### v1.0.0
- Initial release: logistic PS, 1:1 NN matching, ATT estimation, SMD diagnostics, Love plot
