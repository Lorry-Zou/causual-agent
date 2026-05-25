---
name: dag-discovery
description: Causal graph discovery using PC, FCI, and LiNGAM algorithms. Identifies causal structure from observational data without pre-specified treatment.
workflow_stage: analysis
compatibility:
  - claude-code
author: Causal Agent System
version: 1.0.0
tags:
  - python
  - dag
  - causal-discovery
  - pc-algorithm
  - lingam
---

# DAG Discovery

## Purpose

Discover causal relationships from observational data when there is no pre-specified treatment variable. Uses constraint-based (PC, FCI) and functional causal model (LiNGAM) algorithms to learn the causal graph structure.

## When to Use

- Exploratory analysis: "What factors affect my outcome?"
- No clear treatment variable specified by user
- Want to identify potential confounders and mediators
- Data has multiple continuous variables with unknown causal ordering

## Instructions

### Step 1: Prepare Variables

Select continuous variables for discovery:
- Recommended: 5-15 variables
- Sample size > 200 for reliable results
- Variables should be roughly linear and (for LiNGAM) non-Gaussian

### Step 2: Choose Algorithm

- **PC**: Fast, constraint-based. Assumes no latent confounders. Good default.
- **FCI**: Handles latent confounders. Slower but more robust.
- **LiNGAM**: Assumes linear non-Gaussian data. Produces directed edges.

```python
from src.causal_models import DAGDiscovery

dag = DAGDiscovery(
    data=df_clean,
    effect="outcome",
    treatment="",
    causes=all_variables,
)
result = dag.fit(discovery_method="pc").run()
```

### Step 3: Interpret Graph

- **Directed edge (A→B)**: A causes B
- **Undirected edge (A—B)**: Association, direction uncertain
- **Bidirected edge (A↔B)**: Latent confounder (FCI only)
- Use graph to identify: confounders, mediators, colliders

### Step 4: Follow-up Analysis

Based on discovered DAG:
1. Identify treatment → outcome paths
2. Select confounders to control for
3. Choose estimation method (PSM, DML, IV, etc.)

## Requirements

- Python 3.10+
- Optional: `causal-learn` (for advanced algorithms; falls back to correlation threshold)
- Optional: `networkx` (for graph visualization)

## Best Practices

1. Use multiple algorithms and compare results
2. Triangulate with domain knowledge
3. DAG discovery is exploratory — follow with targeted estimation
4. Report edge stability (bootstrap)

## References

- Spirtes, Glymour & Scheines (2000) Causation, Prediction, and Search
- Shimizu et al. (2006) A Linear Non-Gaussian Acyclic Model for Causal Discovery

## Changelog

### v1.0.0
- Initial release: PC, FCI, LiNGAM via causal-learn; correlation fallback; DAG visualization
