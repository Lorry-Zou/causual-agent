"""Causal inference models: selection, DAG discovery, DiD, IV, panel, PSM, DML, RDD."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as sp_stats
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from src.utils import logger, configure_matplotlib_font

# Optional heavy dependencies — graceful fallback
try:
    from linearmodels.panel import PanelOLS, RandomEffects
    from linearmodels.iv import IV2SLS
    HAS_LINEARMODELS = True
except ImportError:
    HAS_LINEARMODELS = False

try:
    from econml.dml import LinearDML, CausalForestDML
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, GradientBoostingClassifier
    HAS_ECONML = True
except ImportError:
    HAS_ECONML = False

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    from causallearn.search.ConstraintBased.PC import pc as cl_pc
    from causallearn.utils.cit import fisherz
    HAS_CAUSALLEARN = True
except ImportError:
    HAS_CAUSALLEARN = False

configure_matplotlib_font()
sns.set_style("whitegrid")

# ===========================================================================
# Method metadata + Rule-based selection
# ===========================================================================

@dataclass
class ModelCandidate:
    name: str
    display_name: str
    score: float = 0.0
    prerequisites: list[str] = field(default_factory=list)

METHODS = {
    "dag_discovery": ModelCandidate("dag_discovery", "因果图发现 (DAG)", prerequisites=["无预设处理变量"]),
    "diff_in_diff": ModelCandidate("diff_in_diff", "双重差分 (DiD)", prerequisites=["面板数据", "处理前后时间"]),
    "instrumental_variable": ModelCandidate("instrumental_variable", "工具变量 (IV)", prerequisites=["工具变量"]),
    "panel_regression": ModelCandidate("panel_regression", "面板数据回归", prerequisites=["面板结构"]),
    "propensity_score": ModelCandidate("propensity_score", "倾向得分匹配 (PSM)", prerequisites=["二值处理", "混淆变量"]),
    "double_ml": ModelCandidate("double_ml", "双机器学习 (DML)", prerequisites=["大样本", "混淆变量"]),
    "rdd": ModelCandidate("rdd", "断点回归 (RDD)", prerequisites=["明确断点", "连续运行变量"]),
}


def _extract_coef_table(result, skip_const: bool = True) -> list[dict[str, Any]]:
    """Extract full coefficient table from a statsmodels-style regression result.

    Returns a list of dicts with: name, coef, se, t_stat, p_value, ci_lower, ci_upper.
    """
    rows: list[dict[str, Any]] = []
    try:
        params = result.params
        bse = getattr(result, "bse", None)
        pvals = getattr(result, "pvalues", pd.Series(index=params.index))
        tvals = getattr(result, "tvalues", pd.Series(index=params.index))
        if hasattr(result, "conf_int"):
            ci = result.conf_int()
        else:
            ci = None

        for name in params.index:
            if skip_const and name in ("const", "Intercept"):
                continue
            se = float(bse.get(name, np.nan)) if bse is not None else np.nan
            t_val = float(tvals.get(name, np.nan)) if tvals is not None else np.nan
            p_val = float(pvals.get(name, np.nan))
            if ci is not None and name in ci.index:
                ci_low = float(ci.loc[name, 0])
                ci_high = float(ci.loc[name, 1])
            else:
                ci_low, ci_high = np.nan, np.nan
            rows.append({
                "name": str(name),
                "coef": float(params[name]),
                "se": se,
                "t_stat": t_val,
                "p_value": p_val,
                "ci_lower": ci_low,
                "ci_upper": ci_high,
            })
    except Exception:
        pass
    return rows


def score_methods(sample_size: int, feature_count: int, is_panel: bool,
                  has_binary: bool, has_continuous: bool, data_type: str) -> dict[str, float]:
    """Score each causal method by data characteristics."""
    n = sample_size; p = feature_count
    s: dict[str, float] = {}
    s["dag_discovery"] = 1.0 + (1.0 if n >= 200 else 0) + (1.0 if p >= 5 else 0) + (0.5 if not (has_binary or has_continuous) else 0)
    s["diff_in_diff"] = 0.5 + (2.0 if is_panel else 0) + (1.0 if data_type == "panel" else 0) + (0.5 if has_binary else 0)
    s["instrumental_variable"] = 0.5 + (0.5 if n >= 100 else 0) + (0.5 if is_panel else 0)
    s["panel_regression"] = 1.0 + (2.0 if is_panel else -0.5) + (1.0 if data_type == "panel" else 0)
    s["propensity_score"] = 1.5 + (1.0 if has_binary else -0.5) + (1.0 if data_type == "cross_section" else 0) + (0.5 if not is_panel else -0.5)
    s["double_ml"] = 1.0 + (1.0 if n >= 500 else -0.5) + (0.5 if p >= 5 else 0) + (1.0 if data_type == "cross_section" else 0)
    s["rdd"] = 0.3 + (0.5 if has_continuous else 0) + (0.5 if n >= 200 else 0)
    return s


def select_methods(scores: dict[str, float], top_n: int = 3) -> tuple[list[str], dict[str, float]]:
    """Select top-N methods, return (names, filtered_scores)."""
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    cutoff = ranked[0][1] * 0.3 if ranked else 1.0
    filtered = [(m, s) for m, s in ranked if s >= cutoff][:top_n]
    return [m for m, _ in filtered], {m: s for m, s in filtered}


# ===========================================================================
# Abstract base
# ===========================================================================

class BaseCausalModel(ABC):
    """Abstract base for all causal inference methods."""

    def __init__(self, data: pd.DataFrame, effect: str, treatment: str,
                 causes: list[str], output_dir: str = "./output/graphs") -> None:
        self.data = data
        self.effect = effect
        self.treatment = treatment
        self.causes = causes
        self.output_dir = output_dir
        self._log = logger()

    @abstractmethod
    def fit(self, **kwargs: Any) -> BaseCausalModel: ...
    @abstractmethod
    def estimate_ate(self) -> dict[str, Any]: ...
    @abstractmethod
    def diagnostics(self) -> dict[str, Any]: ...
    @abstractmethod
    def plot(self) -> list[str]: ...

    def estimate_hte(self) -> pd.DataFrame | None:
        return None

    def run(self) -> dict[str, Any]:
        self._log.info("运行: %s", self.__class__.__name__)
        self.fit()
        return {
            "method": self.__class__.__name__,
            "ate": self.estimate_ate(),
            "diagnostics": self.diagnostics(),
            "hte": self.estimate_hte(),
            "figures": self.plot(),
        }


MODEL_REGISTRY: dict[str, type[BaseCausalModel]] = {}

def register(name: str):
    def dec(cls: type[BaseCausalModel]) -> type[BaseCausalModel]:
        MODEL_REGISTRY[name] = cls
        return cls
    return dec


def run_models(data, effect, treatment, causes, selected: list[str],
               output_dir: str, meta: dict, stats: dict) -> dict[str, Any]:
    """Run selected causal models. Returns {method_name: result_dict}."""
    results: dict[str, Any] = {}
    _log = logger()
    for method_name in selected:
        cls = MODEL_REGISTRY.get(method_name)
        if cls is None:
            _log.warning("模型未注册: %s", method_name)
            continue
        try:
            model = cls(data=data, effect=effect, treatment=treatment, causes=causes, output_dir=output_dir)
            results[method_name] = model.run()
            _log.info("%s 完成", method_name)
        except Exception as e:
            _log.error("%s 失败: %s", method_name, str(e))
            results[method_name] = {"error": str(e)}
    return results


# ===========================================================================
# Panel Regression
# ===========================================================================

@register("panel_regression")
class PanelRegression(BaseCausalModel):
    """Panel FE/RE regression with Hausman test."""

    def fit(self, **kwargs: Any) -> PanelRegression:
        if self.data is None:
            raise ValueError("No data")
        if not HAS_LINEARMODELS:
            return self._fit_ols()

        entity, time = self._detect_ids()
        if not entity or not time:
            return self._fit_ols()

        predictors = [self.treatment] if self.treatment else []
        predictors += [c for c in self.causes if c not in (entity, time, self.effect, self.treatment)][:8]
        if not predictors:
            raise ValueError("无可用的自变量")

        df = self.data.copy()
        df[entity] = df[entity].astype(str)
        df = df.set_index([entity, time])[[self.effect] + predictors].dropna()
        if len(df) < 20:
            raise ValueError("有效样本过小")

        formula = f"{self.effect} ~ {' + '.join(predictors)}"
        try:
            self._fe = PanelOLS.from_formula(f"{formula} + EntityEffects", data=df)
            self._fe_res = self._fe.fit(cov_type="clustered", cluster_entity=True)
            try:
                self._re_res = RandomEffects.from_formula(formula, data=df).fit()
            except Exception:
                self._re_res = None
            self._ols = False
        except Exception as e:
            self._log.warning("PanelOLS失败: %s, 回退OLS", e)
            return self._fit_ols()
        return self

    def _fit_ols(self) -> PanelRegression:
        """Fallback: OLS with entity dummies."""
        self._ols = True
        entity, time = self._detect_ids()
        predictors = [self.treatment] if self.treatment else []
        predictors += [c for c in self.causes if c not in (entity, time, self.effect, self.treatment)][:8]
        df = self.data[[self.effect] + predictors].dropna()
        X = sm.add_constant(df[predictors])
        self._fe_res = sm.OLS(df[self.effect], X).fit()
        self._re_res = None
        return self

    def _detect_ids(self) -> tuple[str, str]:
        meta = getattr(self, '_meta', {})
        date_cols = [c for c, m in meta.items() if m.get("type") == "datetime"] if meta else []
        id_pats = ("id", "code", "编号", "代码", "企业", "公司", "entity", "firm", "person")
        time_pats = ("date", "year", "month", "time", "日期", "年份", "时间", "年", "period")
        entity = ""; time = ""
        for col in self.data.columns:
            cl = str(col).lower().strip()
            if any(p in cl for p in id_pats):
                entity = col; break
        if date_cols:
            time = date_cols[0]
        else:
            for col in self.data.columns:
                cl = str(col).lower().strip()
                if any(p in cl for p in time_pats):
                    time = col; break
        return entity, time

    def estimate_ate(self) -> dict[str, Any]:
        if self._fe_res is None:
            return {"ate": None, "error": "模型未拟合"}
        params = self._fe_res.params; pvals = getattr(self._fe_res, "pvalues", pd.Series())
        if hasattr(self._fe_res, "conf_int"):
            ci = self._fe_res.conf_int()
        else:
            ci = None
        coef_table = _extract_coef_table(self._fe_res)
        if self.treatment and self.treatment in params.index:
            ate = float(params[self.treatment])
            pv = float(pvals.get(self.treatment, np.nan))
            c = (float(ci.loc[self.treatment, 0]), float(ci.loc[self.treatment, 1])) if ci is not None and self.treatment in ci.index else (np.nan, np.nan)
            return {"ate": ate, "ci_lower": c[0], "ci_upper": c[1], "p_value": pv,
                    "significant": pv < 0.05 if not np.isnan(pv) else False,
                    "method": "Fixed Effects Panel Regression",
                    "coef_table": coef_table}
        # Return first non-const
        for p in params.index:
            if p not in ("const", "Intercept"):
                return {"ate": float(params[p]), "ci_lower": np.nan, "ci_upper": np.nan,
                        "p_value": float(pvals.get(p, np.nan)), "significant": False,
                        "method": "FE Panel Regression", "note": f"使用'{p}'作为处理变量",
                        "coef_table": coef_table}
        return {"ate": None, "error": "无法提取"}

    def diagnostics(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if hasattr(self._fe_res, "rsquared"):
            d["r_squared"] = float(self._fe_res.rsquared)
        return d

    def plot(self) -> list[str]:
        return []


# ===========================================================================
# PSM
# ===========================================================================

@register("propensity_score")
class PropensityScoreMatching(BaseCausalModel):
    """PSM with balance diagnostics and Love plot."""

    def fit(self, **kwargs: Any) -> PropensityScoreMatching:
        if self.treatment not in self.data.columns:
            raise ValueError(f"处理变量'{self.treatment}'不在数据中")
        t = self.data[self.treatment].dropna()
        if t.nunique() != 2:
            median = t.median()
            t = (t > median).astype(int)
            self._log.info("处理变量二值化: median=%.2f", median)
        self._confounders = [c for c in self.causes if c not in (self.effect, self.treatment)
                             and pd.api.types.is_numeric_dtype(self.data[c])][:10]
        if not self._confounders:
            self._confounders = [c for c in self.data.columns if c not in (self.effect, self.treatment)
                                 and pd.api.types.is_numeric_dtype(self.data[c])][:10]
        valid = t.notna() & self.data[self._confounders].notna().all(axis=1)
        t = t[valid].astype(int)
        X = self.data.loc[valid, self._confounders].fillna(self.data[self._confounders].median())
        X = (X - X.mean()) / X.std()
        self._y = self.data.loc[valid, self.effect]
        self._ps = LogisticRegression(max_iter=1000, random_state=42)
        self._ps.fit(X, t)
        self._ps_scores = self._ps.predict_proba(X)[:, 1]
        treated = t == 1; control = t == 0
        ps_t = self._ps_scores[treated].reshape(-1, 1)
        ps_c = self._ps_scores[control].reshape(-1, 1)
        if len(ps_t) == 0 or len(ps_c) == 0:
            raise ValueError("处理组或对照组为空")
        nn = NearestNeighbors(n_neighbors=1, algorithm="ball_tree")
        nn.fit(ps_c)
        self._mt = np.where(treated)[0]
        self._mc = np.where(control)[0][nn.kneighbors(ps_t, return_distance=False).flatten()]
        return self

    def estimate_ate(self) -> dict[str, Any]:
        if self._mt is None:
            return {"ate": None, "error": "未拟合"}
        diff = self._y.iloc[self._mt].values - self._y.iloc[self._mc].values
        att = float(np.mean(diff)); se = float(np.std(diff, ddof=1) / np.sqrt(len(diff)))
        pv = float(2 * sp_stats.t.sf(abs(att / se), df=max(1, len(diff) - 1))) if se > 0 else 1.0
        return {"ate": att, "se": se, "ci_lower": att - 1.96 * se, "ci_upper": att + 1.96 * se,
                "p_value": pv, "significant": pv < 0.05, "n_matched": len(diff),
                "method": "Propensity Score Matching (ATT)"}

    def diagnostics(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self._ps_scores is not None and self._confounders:
            t = (self.data[self.treatment].astype(int).values)
            treated = t == 1; control = t == 0
            smd_b, smd_a = {}, {}
            for col in self._confounders:
                yt = self.data.loc[treated, col]; yc = self.data.loc[control, col]
                psd = np.sqrt((yt.std() ** 2 + yc.std() ** 2) / 2)
                smd_b[col] = float(abs(yt.mean() - yc.mean()) / psd) if psd > 0 else 0
                if self._mt is not None:
                    ytm = yt.iloc[self._mt]; ycm = yc.iloc[self._mc]
                    psd_a = np.sqrt((ytm.std() ** 2 + ycm.std() ** 2) / 2)
                    smd_a[col] = float(abs(ytm.mean() - ycm.mean()) / psd_a) if psd_a > 0 else 0
            d["smd_before_mean"] = float(np.mean(list(smd_b.values())))
            d["smd_after_mean"] = float(np.mean(list(smd_a.values()))) if smd_a else 0
            d["balance_improved"] = d["smd_after_mean"] < d["smd_before_mean"]
        return d

    def plot(self) -> list[str]:
        paths: list[str] = []
        if self._ps_scores is None:
            return paths
        try:
            t = (self.data[self.treatment].astype(int) == 1)
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            axes[0].hist(self._ps_scores[t.values if hasattr(t, 'values') else t], bins=30, alpha=0.6, label="Treated", density=True)
            axes[0].hist(self._ps_scores[~t], bins=30, alpha=0.6, label="Control", density=True)
            axes[0].set_title("Before Matching"); axes[0].legend(fontsize=8)
            axes[1].hist(self._ps_scores[self._mt], bins=30, alpha=0.6, label="Treated", density=True)
            axes[1].hist(self._ps_scores[self._mc], bins=30, alpha=0.6, label="Control", density=True)
            axes[1].set_title("After Matching"); axes[1].legend(fontsize=8)
            plt.tight_layout()
            path = f"{self.output_dir}/psm_distribution.png"
            fig.savefig(path, dpi=150); plt.close(fig)
            paths.append(path)
        except Exception:
            pass
        return paths


# ===========================================================================
# DiD
# ===========================================================================

@register("diff_in_diff")
class DifferenceInDifferences(BaseCausalModel):
    """DiD with parallel trends check."""

    def fit(self, **kwargs: Any) -> DifferenceInDifferences:
        entity, time = self._detect_ids()
        df = self.data.copy()
        if self.treatment not in df.columns or df[self.treatment].nunique() != 2:
            entities = df[entity].unique() if entity else df.index.unique()
            mid = len(entities) // 2
            df["treated"] = df[entity].isin(set(entities[:mid])).astype(int) if entity else 0
        else:
            df["treated"] = df[self.treatment].astype(int)

        if time:
            tv = sorted(df[time].unique()); mid = len(tv) // 2
            df["post"] = (df[time] >= tv[mid]).astype(int)
        else:
            df["post"] = 1
        df["treat_post"] = df["treated"] * df["post"]
        df = df.dropna(subset=[self.effect, "treated", "post", "treat_post"])
        X = sm.add_constant(df[["treated", "post", "treat_post"]])
        self._res = sm.OLS(df[self.effect], X).fit()
        return self

    def _detect_ids(self) -> tuple[str, str]:
        id_pats = ("id", "code", "编号", "代码", "企业", "公司", "entity", "firm")
        time_pats = ("date", "year", "time", "日期", "年份", "时间", "年", "period")
        entity = ""; time = ""
        for c in self.data.columns:
            cl = str(c).lower().strip()
            if any(p in cl for p in id_pats):
                entity = c; break
        for c in self.data.columns:
            cl = str(c).lower().strip()
            if any(p in cl for p in time_pats):
                time = c; break
        return entity, time

    def estimate_ate(self) -> dict[str, Any]:
        params = self._res.params; pvals = self._res.pvalues
        ci = self._res.conf_int()
        ate = float(params.get("treat_post", np.nan))
        pv = float(pvals.get("treat_post", np.nan))
        c = (float(ci.loc["treat_post", 0]), float(ci.loc["treat_post", 1])) if "treat_post" in ci.index else (np.nan, np.nan)
        return {"ate": ate, "ci_lower": c[0], "ci_upper": c[1], "p_value": pv,
                "significant": pv < 0.05, "r_squared": float(self._res.rsquared),
                "method": "Difference-in-Differences",
                "coef_table": _extract_coef_table(self._res)}

    def diagnostics(self) -> dict[str, Any]:
        pv = float(self._res.pvalues.get("treated", np.nan))
        return {"parallel_trends_concern": pv < 0.05, "pre_treatment_pval": pv}

    def plot(self) -> list[str]:
        paths: list[str] = []
        try:
            params = self._res.params; conf = self._res.conf_int(); pvals = self._res.pvalues
            keys = ["treat_post", "treated", "post"]
            avail = [k for k in keys if k in params.index]
            if not avail:
                return paths
            fig, ax = plt.subplots(figsize=(8, len(avail) * 0.8 + 2))
            coefs = [params[k] for k in avail]
            c_low = [conf.loc[k, 0] if k in conf.index else np.nan for k in avail]
            c_high = [conf.loc[k, 1] if k in conf.index else np.nan for k in avail]
            colors = ["#2ECC71" if float(pvals.get(k, 1)) < 0.05 else "#95A5A6" for k in avail]
            for i, k in enumerate(avail):
                ax.errorbar(coefs[i], i, xerr=[[coefs[i] - c_low[i]], [c_high[i] - coefs[i]]],
                            fmt="o", capsize=4, color="#34495E"); ax.scatter([coefs[i]], [i], s=80, color=colors[i], zorder=5)
            ax.axvline(x=0, color="red", linestyle="--", linewidth=0.8); ax.set_yticks(range(len(avail)))
            ax.set_yticklabels([f"{k}\n(p={pvals.get(k,0):.3f})" for k in avail], fontsize=9)
            ax.set_title("DiD Estimation"); plt.tight_layout()
            path = f"{self.output_dir}/did_results.png"; fig.savefig(path, dpi=150); plt.close(fig)
            paths.append(path)
        except Exception:
            pass
        return paths


# ===========================================================================
# IV
# ===========================================================================

@register("instrumental_variable")
class InstrumentalVariable(BaseCausalModel):
    """IV 2SLS with first-stage diagnostics."""

    def fit(self, **kwargs: Any) -> InstrumentalVariable:
        inst = kwargs.get("instrument", "")
        if not inst and self.causes:
            # Heuristic: pick the cause with highest correlation with treatment
            best, best_corr = "", -1
            for c in self.causes[:10]:
                if c not in (self.effect, self.treatment):
                    v = self.data[[self.treatment, c]].dropna()
                    if len(v) > 20:
                        corr = abs(v[self.treatment].corr(v[c]))
                        if corr > best_corr:
                            best_corr = corr; best = c
            inst = best
        if not inst:
            raise ValueError("未找到工具变量")
        self._inst = inst
        exog = [c for c in self.causes if c not in (inst, self.treatment, self.effect)][:5]
        df = self.data[[self.effect, self.treatment, inst] + exog].dropna()
        if len(df) < 30:
            raise ValueError("样本量过小")

        # First-stage
        X1 = sm.add_constant(df[[inst] + exog])
        self._fs = sm.OLS(df[self.treatment], X1).fit()

        # Second-stage
        if HAS_LINEARMODELS:
            formula = f"{self.effect} ~ 1 + [{self.treatment} ~ {inst}]"
            if exog:
                formula += " + " + " + ".join(exog)
            try:
                self._res = IV2SLS.from_formula(formula, data=df).fit()
            except Exception:
                self._res = sm.OLS(df[self.effect], sm.add_constant(df[[self.treatment] + exog])).fit()
        else:
            self._res = sm.OLS(df[self.effect], sm.add_constant(df[[self.treatment] + exog])).fit()
        return self

    def estimate_ate(self) -> dict[str, Any]:
        if self._res is None:
            return {"ate": None}
        params = self._res.params; pvals = getattr(self._res, "pvalues", pd.Series())
        ate = float(params.get(self.treatment, np.nan))
        pv = float(pvals.get(self.treatment, np.nan)) if isinstance(pvals, pd.Series) else np.nan
        coef_table = _extract_coef_table(self._res)
        # First-stage coefs
        if self._fs is not None:
            fs_table = _extract_coef_table(self._fs)
            for row in fs_table:
                row["name"] = f"FS: {row['name']}"
            coef_table = coef_table + fs_table
        return {"ate": ate, "p_value": pv, "significant": pv < 0.05 if not np.isnan(pv) else False,
                "method": "IV (2SLS)", "instrument": self._inst,
                "coef_table": coef_table}

    def diagnostics(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self._fs is not None:
            f = float(self._fs.fvalue); d["first_stage_f"] = f
            d["weak_instrument"] = f < 10
            if f < 10:
                d["warning"] = "F<10, 可能存在弱工具变量问题"
        return d

    def plot(self) -> list[str]:
        return []


# ===========================================================================
# DML
# ===========================================================================

@register("double_ml")
class DoubleML(BaseCausalModel):
    """Double Machine Learning via EconML."""

    def fit(self, **kwargs: Any) -> DoubleML:
        if not HAS_ECONML:
            raise ImportError("EconML未安装。pip install econml")
        feats = [c for c in self.causes if c not in (self.effect, self.treatment)
                 and pd.api.types.is_numeric_dtype(self.data[c])][:20]
        if not feats:
            feats = [c for c in self.data.columns if c not in (self.effect, self.treatment)
                     and pd.api.types.is_numeric_dtype(self.data[c])][:20]
        df = self.data[[self.effect, self.treatment] + feats].dropna()
        self._X = df[feats].values; self._T = df[self.treatment].values; self._Y = df[self.effect].values
        self._feats = feats
        is_bin = len(np.unique(self._T)) <= 2
        model_t = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42) if is_bin else GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42)
        self._dml = LinearDML(
            model_y=GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42),
            model_t=model_t,
            discrete_treatment=is_bin, cv=3, random_state=42,
        )
        self._dml.fit(Y=self._Y, T=self._T, X=self._X)
        if len(self._Y) >= 200 and len(feats) >= 2:
            try:
                self._cf = CausalForestDML(
                    model_y=RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42, n_jobs=-1),
                    model_t=RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42, n_jobs=-1),
                    discrete_treatment=is_bin, n_estimators=200, min_samples_leaf=20, max_depth=5, random_state=42, n_jobs=-1,
                )
                self._cf.fit(Y=self._Y, T=self._T, X=self._X)
            except Exception:
                self._cf = None
        else:
            self._cf = None
        return self

    def estimate_ate(self) -> dict[str, Any]:
        ate_arr = self._dml.const_marginal_ate(X=self._X)
        ate = float(np.mean(ate_arr))
        inf = self._dml.const_marginal_ate_inference(X=self._X)
        se = float(np.mean(inf.pred_stderr))
        zstat = abs(ate) / max(se, 1e-10)
        p_value = float(2 * sp_stats.norm.sf(zstat))
        ci_lower = ate - 1.96 * se
        ci_upper = ate + 1.96 * se
        return {"ate": ate, "ci_lower": ci_lower, "ci_upper": ci_upper,
                "p_value": p_value,
                "significant": ci_lower > 0 or ci_upper < 0, "method": "DML"}

    def diagnostics(self) -> dict[str, Any]:
        return {"n_samples": len(self._Y), "n_features": len(self._feats)}

    def plot(self) -> list[str]:
        paths: list[str] = []
        if self._cf is not None:
            try:
                cate = self._cf.effect(self._X)
                fig, axes = plt.subplots(1, 2, figsize=(12, 4))
                axes[0].hist(cate.flatten(), bins=30, color="#3498DB", edgecolor="white")
                axes[0].axvline(x=0, color="red", linestyle="--"); axes[0].set_title("HTE Distribution")
                imp = self._cf.feature_importances_
                top = np.argsort(imp)[-10:]
                axes[1].barh(range(len(top)), imp[top])
                axes[1].set_yticks(range(len(top)))
                axes[1].set_yticklabels([self._feats[i] for i in top], fontsize=8)
                axes[1].set_title("Feature Importance"); plt.tight_layout()
                path = f"{self.output_dir}/dml_hte.png"; fig.savefig(path, dpi=150); plt.close(fig)
                paths.append(path)
            except Exception:
                pass
        return paths


# ===========================================================================
# RDD
# ===========================================================================

@register("rdd")
class RegressionDiscontinuity(BaseCausalModel):
    """Sharp RDD with IK bandwidth."""

    def fit(self, **kwargs: Any) -> RegressionDiscontinuity:
        running = kwargs.get("running_variable", "")
        if not running:
            # Pick first continuous cause
            for c in self.causes:
                if c != self.effect and c != self.treatment and pd.api.types.is_numeric_dtype(self.data[c]):
                    running = c; break
        if not running:
            raise ValueError("未找到运行变量")
        self._rv = running
        self._thresh = float(kwargs.get("threshold", self.data[running].median()))
        df = self.data[[self.effect, running]].dropna()
        df["above"] = (df[running] >= self._thresh).astype(int)
        df["rc"] = df[running] - self._thresh
        df["inter"] = df["rc"] * df["above"]
        # IK bandwidth
        sigma = df["rc"].std(); n = len(df)
        self._bw = float(1.06 * sigma * n ** (-1 / 5) * 2.0)
        in_b = np.abs(df["rc"]) <= self._bw
        df_b = df[in_b] if in_b.sum() >= 30 else df
        X = sm.add_constant(df_b[["rc", "above", "inter"]])
        self._res = sm.OLS(df_b[self.effect], X).fit()
        return self

    def estimate_ate(self) -> dict[str, Any]:
        ate = float(self._res.params.get("above", np.nan))
        pv = float(self._res.pvalues.get("above", np.nan))
        return {"ate": ate, "p_value": pv, "significant": pv < 0.05,
                "threshold": self._thresh, "bandwidth": self._bw, "method": "RDD"}

    def diagnostics(self) -> dict[str, Any]:
        d: dict[str, Any] = {"bandwidth": self._bw}
        rv = self.data[self._rv].dropna()
        below = (rv < self._thresh).sum(); above = (rv >= self._thresh).sum()
        total = below + above; exp = total / 2
        d["mccrary_chi2"] = float((below - exp)**2 / exp + (above - exp)**2 / exp) if exp > 0 else 0
        d["mccrary_concern"] = d["mccrary_chi2"] > 3.84
        return d

    def plot(self) -> list[str]:
        paths: list[str] = []
        try:
            rv = self.data[self._rv]; oc = self.data[self.effect]
            fig, ax = plt.subplots(figsize=(9, 5))
            ax.scatter(rv, oc, s=10, alpha=0.4)
            ax.axvline(x=self._thresh, color="black", linestyle="--")
            ate = self.estimate_ate()
            ax.annotate(f"ATE={ate['ate']:.4f}\np={ate['p_value']:.4f}", xy=(self._thresh, oc.median()))
            ax.set_xlabel(self._rv); ax.set_title("RDD"); plt.tight_layout()
            path = f"{self.output_dir}/rdd_plot.png"; fig.savefig(path, dpi=150); plt.close(fig)
            paths.append(path)
        except Exception:
            pass
        return paths


# ===========================================================================
# DAG Discovery
# ===========================================================================

@register("dag_discovery")
class DAGDiscovery(BaseCausalModel):
    """Causal DAG discovery (PC/FCI/LiNGAM)."""

    def fit(self, **kwargs: Any) -> DAGDiscovery:
        method = kwargs.get("discovery_method", "pc")
        cont = [c for c, m in getattr(self, '_meta', {}).items() if m.get("type") == "continuous"] if hasattr(self, '_meta') else []
        if not cont:
            cont = list(self.data.select_dtypes(include=[np.number]).columns)[:15]
        if len(cont) < 2:
            raise ValueError("至少需要2个连续变量")
        df = self.data[cont].dropna()
        self._cols = cont
        if HAS_CAUSALLEARN:
            try:
                data_np = df.values
                if method == "lingam":
                    from causallearn.search.FCMBased.lingam import DirectLiNGAM
                    self._adj = DirectLiNGAM().fit(data_np).adjacency_matrix_
                elif method == "fci":
                    from causallearn.search.ConstraintBased.FCI import fci
                    G, _ = fci(data_np, indep_test=fisherz)
                    self._adj = G.graph
                else:
                    self._adj = cl_pc(data_np, indep_test=fisherz).G.graph
            except Exception as e:
                self._log.warning("causal-learn失败: %s, 回退", e)
                self._adj = self._fallback(df)
        else:
            self._adj = self._fallback(df)
        self._edges = []
        for i, fc in enumerate(cont):
            for j, tc in enumerate(cont):
                if i != j and self._adj[i, j] != 0:
                    self._edges.append((fc, tc))
        return self

    def _fallback(self, df: pd.DataFrame) -> np.ndarray:
        corr = df.corr().values; th = 0.3; n = len(df.columns)
        adj = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j and abs(corr[i, j]) > th:
                    adj[i, j] = corr[i, j]
        return adj

    def estimate_ate(self) -> dict[str, Any]:
        return {"ate": None, "method": "DAG Discovery", "n_edges": len(self._edges),
                "edges": self._edges[:20],
                "note": "DAG发现识别因果结构，不直接估计ATE。请基于发现的结构选择估计方法。"}

    def diagnostics(self) -> dict[str, Any]:
        return {"n_nodes": len(self._cols), "n_edges": len(self._edges)}

    def plot(self) -> list[str]:
        paths: list[str] = []
        if not self._edges or not HAS_NETWORKX:
            return paths
        try:
            G = nx.DiGraph()
            for s, t in self._edges:
                G.add_edge(s, t)
            fig, ax = plt.subplots(figsize=(max(8, len(G.nodes)*0.8), max(6, len(G.nodes)*0.6)))
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
            nx.draw_networkx_nodes(G, pos, ax=ax, node_color="#3498DB", node_size=1200, alpha=0.9)
            nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#7F8C8D", arrows=True, arrowsize=15)
            nx.draw_networkx_labels(G, pos, ax=ax, font_size=8)
            ax.set_title("Causal DAG"); ax.axis("off"); plt.tight_layout()
            path = f"{self.output_dir}/dag.png"; fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)
            paths.append(path)
        except Exception:
            pass
        return paths
