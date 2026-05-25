"""Data processing: loading, cleaning, imputation, outlier handling, type inference, EDA, stats."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from sklearn.experimental import enable_iterative_imputer  # noqa: must come before IterativeImputer
from sklearn.impute import SimpleImputer, IterativeImputer

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from src.utils import logger, configure_matplotlib_font

configure_matplotlib_font()
sns.set_style("whitegrid")


# ===========================================================================
# Data Loader
# ===========================================================================

class DataLoader:
    """Load CSV/Excel/JSON/Stata/Parquet with auto-detection."""

    SUPPORTED = {".csv", ".xlsx", ".xls", ".json", ".dta", ".parquet"}

    def __init__(self) -> None:
        self._log = logger()

    def load(self, file_path: str | Path) -> pd.DataFrame:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        ext = path.suffix.lower()
        if ext not in self.SUPPORTED:
            raise ValueError(f"不支持的文件格式: {ext}")
        if ext == ".csv":
            df = self._load_csv(path)
        elif ext in (".xlsx", ".xls"):
            df = self._load_excel(path)
        elif ext == ".json":
            df = pd.read_json(path)
        elif ext == ".dta":
            df = pd.read_stata(path)
        elif ext == ".parquet":
            df = pd.read_parquet(path)
        else:
            df = pd.DataFrame()
        self._log.info("数据加载: %s, shape=%s", path.name, df.shape)
        return df

    def _load_csv(self, path: Path) -> pd.DataFrame:
        for enc in ["utf-8", "gbk", "gb2312", "gb18030", "latin-1"]:
            try:
                for sep in [",", ";", "\t", "|"]:
                    try:
                        probe = pd.read_csv(path, encoding=enc, sep=sep, nrows=5)
                        if probe.shape[1] > 1:
                            return pd.read_csv(path, encoding=enc, sep=sep, low_memory=False)
                    except Exception:
                        continue
            except UnicodeDecodeError:
                continue
        raise ValueError(f"无法读取CSV: {path}")

    def _load_excel(self, path: Path) -> pd.DataFrame:
        xl = pd.ExcelFile(path)
        for sheet in xl.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            if not df.empty:
                self._log.info("工作表: %s", sheet)
                return df
        return pd.DataFrame()

    # ------------------------------------------------------------------
    # Multi-file support
    # ------------------------------------------------------------------

    def _resolve_paths(self, paths: list[str]) -> list[Path]:
        """Expand glob patterns and directories to concrete file paths."""
        resolved: list[Path] = []
        for p in paths:
            path = Path(p)
            if "*" in p or "?" in p:
                # Glob pattern — expand relative to cwd
                base = path.parent if path.parent != Path(".") else Path.cwd()
                pattern = path.name
                matched = sorted(base.glob(pattern))
                resolved.extend(m for m in matched if m.suffix.lower() in self.SUPPORTED)
            elif path.is_dir():
                matched = sorted(path.iterdir())
                resolved.extend(m for m in matched if m.suffix.lower() in self.SUPPORTED)
            elif path.exists():
                if path.suffix.lower() in self.SUPPORTED:
                    resolved.append(path)
            else:
                self._log.warning("路径不存在，跳过: %s", p)
        if not resolved:
            raise FileNotFoundError(f"未找到可加载的数据文件: {paths}")
        self._log.info("解析路径: %d 个文件", len(resolved))
        return resolved

    def _detect_merge_strategy(self, dfs: dict[str, pd.DataFrame]) -> tuple[str, list[str] | None]:
        """Detect how to merge multiple DataFrames.
        Returns (strategy, shared_id_columns_or_None).
        """
        if len(dfs) <= 1:
            return "separate", None
        names = list(dfs.keys())
        cols_list = [set(dfs[n].columns) for n in names]

        # Check for common columns across ALL files
        common_all = cols_list[0].intersection(*cols_list[1:])
        # Check for ID-like columns
        id_cols = {c for c in common_all if c.endswith("ID") or c.endswith("Id")}

        total_cols = set().union(*cols_list)
        avg_cols = sum(len(c) for c in cols_list) / len(cols_list)

        if len(common_all) / max(avg_cols, 1) >= 0.5:
            return "concat", None
        if id_cols:
            return "merge", sorted(id_cols)
        return "separate", None

    def load_multiple(self, paths: list[str], merge: str = "auto") -> pd.DataFrame | dict[str, pd.DataFrame]:
        """Load multiple data files with optional merging.

        Args:
            paths: File paths, glob patterns, or directories.
            merge: "auto", "concat", "merge", or "separate".

        Returns:
            A single DataFrame if merged, or a dict keyed by stem name.
        """
        resolved = self._resolve_paths(paths)
        if len(resolved) == 1:
            return self.load(resolved[0])

        dfs: dict[str, pd.DataFrame] = {}
        for rp in resolved:
            key = rp.stem
            # Deduplicate keys
            orig_key = key
            n = 1
            while key in dfs:
                key = f"{orig_key}_{n}"
                n += 1
            dfs[key] = self.load(rp)

        # Determine strategy
        strategy = merge
        join_keys = None
        if strategy == "auto":
            strategy, join_keys = self._detect_merge_strategy(dfs)
            self._log.info("自动检测合并策略: %s, 共用键: %s", strategy, join_keys)

        if strategy == "separate":
            return dfs
        elif strategy == "concat":
            combined = pd.concat(dfs.values(), axis=0, ignore_index=True, sort=False)
            self._log.info("多文件合并(concat): %d 文件 -> shape=%s", len(dfs), combined.shape)
            return combined
        elif strategy == "merge":
            if not join_keys:
                cols_list = [set(d.columns) for d in dfs.values()]
                join_keys = sorted(cols_list[0].intersection(*cols_list[1:]) if cols_list else set())
                join_keys = [c for c in join_keys if c.endswith("ID") or c.endswith("Id")]
            if not join_keys:
                self._log.warning("无法找到共用ID列进行merge，回退到separate")
                return dfs
            merged = list(dfs.values())[0]
            for i, (name, df) in enumerate(list(dfs.items())[1:], start=1):
                merged = merged.merge(df, on=join_keys, how="outer", suffixes=("", f"_{i}"))
            self._log.info("多文件合并(merge): %d 文件, 键=%s -> shape=%s", len(dfs), join_keys, merged.shape)
            return merged
        else:
            self._log.warning("未知合并策略: %s，回退到separate", strategy)
            return dfs


# ===========================================================================
# Type Inference
# ===========================================================================

class TypeInference:
    """Classify columns as continuous, categorical, binary, or datetime."""

    def __init__(self, max_unique: int = 20, max_ratio: float = 0.3) -> None:
        self.max_unique = max_unique
        self.max_ratio = max_ratio
        self._log = logger()

    def infer(self, df: pd.DataFrame) -> dict[str, dict]:
        meta: dict[str, dict] = {}
        for col in df.columns:
            meta[col] = self._infer_col(df[col])
        n_cont = sum(1 for m in meta.values() if m["type"] == "continuous")
        n_cat = sum(1 for m in meta.values() if m["type"] in ("categorical", "binary"))
        n_dt = sum(1 for m in meta.values() if m["type"] == "datetime")
        self._log.info("类型推断: %d连续, %d分类, %d日期", n_cont, n_cat, n_dt)
        return meta

    def _infer_col(self, series: pd.Series) -> dict:
        n = len(series)
        n_unique = series.nunique(dropna=True)
        n_missing = int(series.isna().sum())
        info: dict = {"name": str(series.name), "dtype": str(series.dtype),
                      "n_missing": n_missing, "n_unique": n_unique, "type": "continuous"}

        if pd.api.types.is_datetime64_any_dtype(series):
            info["type"] = "datetime"
            return info
        if n_unique <= 2:
            info["type"] = "binary"
            return info

        if series.dtype == "object":
            try:
                pd.to_datetime(series.dropna(), errors="coerce").notna().sum() / max(1, n) > 0.8
                info["type"] = "datetime"
                return info
            except Exception:
                pass
            try:
                pd.to_numeric(series.dropna())
                info["type"] = "continuous"
                return info
            except (ValueError, TypeError):
                info["type"] = "categorical"
                return info

        if pd.api.types.is_numeric_dtype(series):
            info["type"] = "continuous"
            info["stats"] = {"mean": series.mean(), "std": series.std(),
                             "min": series.min(), "max": series.max(), "median": series.median()}
            if 2 < n_unique <= self.max_unique and (n_unique / n) < self.max_ratio:
                info["type"] = "categorical"
            return info
        info["type"] = "categorical"
        return info

    def get_columns_by_type(self, meta: dict[str, dict], *types: str) -> list[str]:
        return [n for n, i in meta.items() if i["type"] in types]


# ===========================================================================
# Imputation
# ===========================================================================

class Imputation:
    """Handle missing values."""

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold
        self._log = logger()

    def handle(self, df: pd.DataFrame, meta: dict[str, dict]) -> tuple[pd.DataFrame, dict]:
        report: dict = {"before": int(df.isna().sum().sum()), "dropped_columns": [],
                        "dropped_rows": 0, "imputed_columns": {}, "after": 0}
        for col in df.columns:
            if df[col].isna().mean() > self.threshold:
                report["dropped_columns"].append(col)
                self._log.info("丢弃高缺失列: %s", col)
        df = df.drop(columns=report["dropped_columns"], errors="ignore")
        before = len(df)
        df = df.dropna(how="all")
        report["dropped_rows"] = before - len(df)
        for col in df.columns:
            if df[col].isna().sum() == 0:
                continue
            ct = meta.get(col, {}).get("type", "continuous")
            if ct in ("binary", "categorical"):
                mode = df[col].mode().iloc[0] if not df[col].mode().empty else "未知"
                df[col] = df[col].fillna(mode)
                report["imputed_columns"][col] = {"method": "mode", "count": int(df[col].isna().sum())}
            else:
                imp = SimpleImputer(strategy="median")
                df[col] = imp.fit_transform(df[[col]])
                report["imputed_columns"][col] = {"method": "median", "count": int(df[col].isna().sum())}
        report["after"] = int(df.isna().sum().sum())
        self._log.info("缺失值: %d→%d (丢弃%d列, 填充%d列)",
                       report["before"], report["after"], len(report["dropped_columns"]), len(report["imputed_columns"]))
        return df, report

    def iterative_impute(self, df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        if not cols:
            return df
        try:
            imp = IterativeImputer(random_state=42, max_iter=10)
            numeric = df.select_dtypes(include=[np.number]).columns.tolist()
            to_imp = [c for c in cols if c in numeric]
            if to_imp:
                df[to_imp] = imp.fit_transform(df[numeric])[:, [numeric.index(c) for c in to_imp]]
                self._log.info("IterativeImputer: %d列", len(to_imp))
        except Exception as e:
            self._log.warning("IterativeImputer失败: %s", e)
        return df


# ===========================================================================
# Outlier Handler
# ===========================================================================

class OutlierHandler:
    """Detect and winsorize outliers."""

    def __init__(self, method: str = "iqr", threshold: float = 1.5) -> None:
        self.method = method
        self.threshold = threshold
        self._log = logger()

    def handle(self, df: pd.DataFrame, meta: dict[str, dict]) -> tuple[pd.DataFrame, dict]:
        report: dict = {"method": self.method, "columns": {}}
        continuous = [n for n, i in meta.items() if i["type"] == "continuous"]
        total = 0
        for col in continuous:
            mask, bounds = self._detect(df[col])
            n = mask.sum()
            if n > 0:
                report["columns"][col] = {"count": int(n), "ratio": round(n / len(df), 4), "bounds": bounds}
                df[col] = df[col].clip(lower=bounds[0], upper=bounds[1])
                total += n
        self._log.info("异常值 (%s): %d个截尾, %d列", self.method, total, len(report["columns"]))
        return df, report

    def _detect(self, series: pd.Series) -> tuple[pd.Series, tuple[float, float]]:
        clean = series.dropna()
        if len(clean) < 10:
            return pd.Series(False, index=series.index), (-np.inf, np.inf)
        if self.method == "iqr":
            q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
            iqr = q3 - q1
            lo, hi = q1 - self.threshold * iqr, q3 + self.threshold * iqr
            mask = (series < lo) | (series > hi)
            return mask, (lo, hi)
        elif self.method == "zscore":
            z = np.abs(sp_stats.zscore(clean, nan_policy="omit"))
            mask = pd.Series(False, index=series.index)
            mask.loc[clean.index] = z > self.threshold
            lo = clean.mean() - self.threshold * clean.std()
            hi = clean.mean() + self.threshold * clean.std()
            return mask, (lo, hi)
        return pd.Series(False, index=series.index), (-np.inf, np.inf)


# ===========================================================================
# Stats Collector
# ===========================================================================

class StatsCollector:
    """Collect dataset statistics for model selection."""

    def __init__(self) -> None:
        self._log = logger()

    def collect(self, df: pd.DataFrame, meta: dict[str, dict]) -> dict[str, object]:
        cont = [c for c, m in meta.items() if m["type"] == "continuous"]
        bin_cols = [c for c, m in meta.items() if m["type"] == "binary"]
        cat_cols = [c for c, m in meta.items() if m["type"] == "categorical"]
        stats: dict[str, object] = {
            "sample_size": len(df), "feature_count": len(df.columns),
            "n_continuous": len(cont), "n_binary": len(bin_cols), "n_categorical": len(cat_cols),
            "data_type": self._detect_type(df, meta),
            "is_panel": self._detect_panel(df),
            "is_time_series": False,
            "has_binary_treatment": False, "has_continuous_treatment": False,
            "linearity_holds": True, "gaussian_errors": True,
            "stationary": "non time-series",
            "description": "",
        }
        stats["description"] = (
            f"样本量: {stats['sample_size']}; 变量数: {stats['feature_count']}; "
            f"连续: {stats['n_continuous']}; 分类: {stats['n_categorical']}; "
            f"类型: {stats['data_type']}" + ("; 面板数据" if stats["is_panel"] else "")
        )
        self._log.info("统计: n=%d, type=%s, panel=%s", stats["sample_size"], stats["data_type"], stats["is_panel"])
        return stats

    def _detect_type(self, df: pd.DataFrame, meta: dict[str, dict]) -> str:
        date_cols = [c for c, m in meta.items() if m["type"] == "datetime"]
        id_cols = [c for c, m in meta.items() if m["type"] == "categorical" and m["n_unique"] > 5]
        if date_cols and id_cols:
            return "panel"
        elif date_cols:
            return "time_series"
        return "cross_section"

    def _detect_panel(self, df: pd.DataFrame) -> bool:
        id_pats = ("id", "code", "编号", "代码", "企业", "公司", "entity", "firm", "person")
        time_pats = ("date", "year", "month", "time", "日期", "年份", "时间", "年", "period")
        has_id = any(any(p in str(c).lower() for p in id_pats) for c in df.columns)
        has_time = any(any(p in str(c).lower() for p in time_pats) for c in df.columns)
        return has_id and has_time


# ===========================================================================
# EDA Generator
# ===========================================================================

class EDAGenerator:
    """Generate EDA plots."""

    def __init__(self, output_dir: str = "./output/graphs") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._log = logger()

    def generate(self, df: pd.DataFrame, meta: dict[str, dict]) -> list[str]:
        paths: list[str] = []
        paths.extend(self._plot_missing(df))
        paths.extend(self._plot_correlation(df, meta))
        self._log.info("EDA: %d张图", len(paths))
        return paths

    def _plot_missing(self, df: pd.DataFrame) -> list[str]:
        if df.isna().sum().sum() == 0:
            return []
        path = str(self.output_dir / "missing_heatmap.png")
        fig, ax = plt.subplots(figsize=(10, max(4, len(df.columns) * 0.3)))
        sns.heatmap(df.isnull(), cbar=False, yticklabels=False, cmap="Reds", ax=ax)
        ax.set_title("Missing Values Heatmap")
        plt.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return [path]

    def _plot_correlation(self, df: pd.DataFrame, meta: dict[str, dict]) -> list[str]:
        cont = [c for c, m in meta.items() if m["type"] == "continuous"]
        if len(cont) < 2:
            return []
        corr = df[cont].corr()
        path = str(self.output_dir / "correlation_heatmap.png")
        fig, ax = plt.subplots(figsize=(max(8, len(cont) * 0.8), max(6, len(cont) * 0.6)))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, square=True, linewidths=0.5,
                    ax=ax, annot_kws={"size": 8}, mask=np.triu(np.ones_like(corr, dtype=bool)))
        ax.set_title("Correlation Matrix")
        plt.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return [path]


# ===========================================================================
# DataCleaner — orchestrator
# ===========================================================================

class DataCleaner:
    """Full data cleaning orchestrator."""

    def __init__(self, config: dict) -> None:
        dc = config.get("data", {})
        self.loader = DataLoader()
        self.type_inf = TypeInference(dc.get("categorical_max_unique", 20), dc.get("categorical_max_ratio", 0.3))
        self.imputation = Imputation(dc.get("missing_threshold", 0.5))
        self.outlier = OutlierHandler(dc.get("outlier_method", "iqr"), dc.get("outlier_threshold", 1.5))
        self.stats = StatsCollector()
        self.eda = EDAGenerator()
        self.output_dir = config.get("pipeline", {}).get("output_dir", "./output")
        self._log = logger()

    def run(self, data_input: str | list[str], merge: str = "auto") -> tuple[pd.DataFrame | dict[str, pd.DataFrame], dict, dict[str, object]]:
        """Load, clean, and profile data. Accepts single path or list of paths/globs/directories.
        Returns (cleaned_df_or_dict, meta, stats_dict).
        """
        self._log.info("=== 数据清洗 ===")

        # Resolve multi-file input
        if isinstance(data_input, list) or "*" in str(data_input) or "?" in str(data_input):
            paths = [data_input] if isinstance(data_input, str) else data_input
            raw = self.loader.load_multiple(paths, merge=merge)
        elif Path(data_input).is_dir():
            raw = self.loader.load_multiple([data_input], merge=merge)
        else:
            raw = self.loader.load(data_input)

        # Handle dict of DataFrames (separate mode)
        if isinstance(raw, dict):
            cleaned: dict[str, pd.DataFrame] = {}
            all_meta: dict[str, dict] = {}
            for name, df in raw.items():
                df = df.drop_duplicates()
                meta = self.type_inf.infer(df)
                for col in [c for c, m in meta.items() if m["type"] == "datetime"]:
                    try:
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                    except Exception:
                        pass
                df, _ = self.imputation.handle(df, meta)
                df, _ = self.outlier.handle(df, meta)
                meta = self.type_inf.infer(df)
                cleaned[name] = df
                all_meta[name] = meta
                self._log.info("清洗完成 [%s]: %d行 x %d列", name, *df.shape)
            combined_stats = self.stats.collect(list(cleaned.values())[0], list(all_meta.values())[0])
            combined_stats["_multi_file"] = True
            combined_stats["_file_count"] = len(cleaned)
            return cleaned, all_meta, combined_stats

        # Single DataFrame path (original behavior)
        raw = raw.drop_duplicates()
        meta = self.type_inf.infer(raw)

        for col in [c for c, m in meta.items() if m["type"] == "datetime"]:
            try:
                raw[col] = pd.to_datetime(raw[col], errors="coerce")
            except Exception:
                pass

        raw, miss_report = self.imputation.handle(raw, meta)
        raw, out_report = self.outlier.handle(raw, meta)
        meta = self.type_inf.infer(raw)  # re-infer after cleaning
        stats = self.stats.collect(raw, meta)
        self.eda.generate(raw, meta)

        self._log.info("清洗完成: %d行 x %d列", *raw.shape)
        return raw, meta, stats
