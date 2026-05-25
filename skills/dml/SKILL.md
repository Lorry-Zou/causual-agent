---
name: dml
description: Double Machine Learning for robust causal estimation with high-dimensional confounders. Uses EconML for ATE/HTE estimation.
workflow_stage: analysis
compatibility:
  - claude-code
author: Causal Agent System
version: 1.0.0
tags:
  - python
  - dml
  - double-ml
  - econml
  - causal-inference
---

# Double Machine Learning

## Purpose

Use Double/Debiased Machine Learning (DML) for causal effect estimation when there are many potential confounders. DML uses ML models to flexibly control for confounding while maintaining valid inference.

## When to Use

- Large sample size (N > 500 recommended)
- Many potential confounders (5+ features)
- Suspected non-linear confounding relationships
- Both binary and continuous treatments supported
- Want heterogeneous treatment effects (HTE) via CausalForest

## Instructions

### Step 1: Check Prerequisites

```python
from src.causal_models import HAS_ECONML
if not HAS_ECONML:
    print("Install: pip install econml")
```

### Step 2: Run DML

```python
from src.causal_models import DoubleML

dml = DoubleML(
    data=df_clean,
    effect="outcome",
    treatment="treatment",
    causes=confounders,
)
result = dml.run()
```

The model:
1. Uses GradientBoosting for nuisance functions (Y ~ X and T ~ X)
2. Estimates ATE with valid confidence intervals
3. Optionally fits CausalForestDML for HTE estimation
4. Produces feature importance plot for heterogeneity drivers

### Step 3: Interpret

- **ATE**: Average causal effect, interpreted same as regression coefficient
- **HTE**: Which subgroups have larger/smaller effects?
- **Feature importance**: Which variables drive treatment effect heterogeneity?

## Requirements

- Python 3.10+
- `econml`, `scikit-learn`, `pandas`, `numpy`

## Best Practices

1. Use cross-fitting (3-fold default) to avoid overfitting bias
2. Compare LinearDML (assumes linear treatment effect) with CausalForestDML
3. Check that nuisance models have reasonable predictive performance
4. For binary treatments, set `discrete_treatment=True`

## Common Pitfalls

- Using DML with too few observations (high variance)
- Over-interpreting feature importance from CausalForest
- Not checking overlap/positivity assumption

## References

- Chernozhukov et al. (2018) Double/Debiased Machine Learning
- [EconML documentation](https://econml.azurewebsites.net/)

## Changelog

### v1.0.0
- Initial release: LinearDML, CausalForestDML, ATE/HTE estimation
