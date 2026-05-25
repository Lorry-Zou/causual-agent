"""Utility functions: logging, LLM client, config, helpers, prompts, matplotlib font setup."""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import yaml
from openai import OpenAI

# ---------------------------------------------------------------------------
# Matplotlib CJK font configuration (called once at import time)
# ---------------------------------------------------------------------------

_CJK_FONT_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans SC",
    "Noto Sans CJK SC",
    "HarmonyOS Sans SC",
    "DengXian",
    "KaiTi",
    "SimSun",
    "FangSong",
]

_FONT_CONFIGURED = False


def configure_matplotlib_font() -> str:
    """Robustly configure matplotlib for Chinese (CJK) text rendering.

    Searches available fonts, sets rcParams, and rebuilds the font cache if
    needed.  Returns the name of the selected font.  Safe to call multiple
    times — subsequent calls are no-ops.
    """
    global _FONT_CONFIGURED
    if _FONT_CONFIGURED:
        sans = plt.rcParams.get("font.sans-serif", ["Arial"])
        return sans[0] if isinstance(sans, list) else str(sans)

    # Force matplotlib to rescan system fonts (handles stale cache)
    try:
        fm._load_fontmanager(try_read_cache=False)
    except Exception:
        pass

    # Find the first available CJK font
    available = {f.name for f in fm.fontManager.ttflist}
    selected = "DejaVu Sans"
    for font_name in _CJK_FONT_CANDIDATES:
        if font_name in available:
            selected = font_name
            break
    else:
        # Fallback: look for any font with CJK-suggestive name
        for f in fm.fontManager.ttflist:
            name_lower = f.name.lower()
            if any(tag in name_lower for tag in ("hei", "song", "kai", "ming", "cjk", "sc", "chinese")):
                selected = f.name
                break

    plt.rcParams["font.sans-serif"] = [selected, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    # Rebuild font cache so future matplotlib instances pick it up
    try:
        cache_dir = Path(matplotlib.get_cachedir())
        for cache_file in cache_dir.glob("fontlist-v*.json"):
            cache_file.unlink(missing_ok=True)
    except Exception:
        pass

    _FONT_CONFIGURED = True
    _log = logging.getLogger("casual-agent")
    _log.info("Matplotlib CJK font: %s", selected)
    return selected


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

_logger: logging.Logger | None = None


def get_logger(output_dir: str | None = None) -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger
    _logger = logging.getLogger("casual-agent")
    _logger.setLevel(logging.DEBUG)
    _logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    _logger.addHandler(console)
    if output_dir:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(path / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        _logger.addHandler(fh)
    return _logger


def logger() -> logging.Logger:
    return get_logger()


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

_VAR_PATTERN = re.compile(r"\$\{(\w+)}")


def _resolve_env(value: str) -> str:
    def _repl(m: re.Match) -> str:
        return os.environ.get(m.group(1), "")
    return _VAR_PATTERN.sub(_repl, value)


def _resolve_dict(d: dict[str, Any]) -> dict[str, Any]:
    for k, v in d.items():
        if isinstance(v, str):
            d[k] = _resolve_env(v)
        elif isinstance(v, dict):
            d[k] = _resolve_dict(v)
    return d


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        # PyInstaller: look next to the .exe first
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            candidate = exe_dir / "config.yaml"
            if candidate.exists():
                path = candidate
        if path is None:
            # Fallback: source tree layout
            path = Path(__file__).parent.parent / "config.yaml"
    if not Path(path).exists():
        # Return sensible defaults so the app doesn't crash
        return {
            "llm": {"api_key": "", "base_url": "https://api.deepseek.com",
                    "model": "deepseek-v4-pro", "temperature": 0.1, "max_tokens": 393216},
            "data": {"categorical_max_ratio": 0.3, "categorical_max_unique": 20,
                     "missing_threshold": 0.5, "outlier_method": "iqr", "outlier_threshold": 1.5},
            "models": {"default": ["panel_regression", "propensity_score"],
                       "selection_confidence_threshold": 0.3},
            "pipeline": {"interactive": True, "max_turns": 3, "output_dir": "./output"},
            "report": {"format": "docx", "include_code": False, "language": "zh"},
        }
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return _resolve_dict(raw)


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

class LLMClient:
    """OpenAI-compatible chat API wrapper (DeepSeek default)."""

    def __init__(self, config: dict[str, Any]) -> None:
        llm_cfg = config.get("llm", {})
        self.model = llm_cfg.get("model", "deepseek-chat")
        self.temperature = llm_cfg.get("temperature", 0.1)
        self.max_tokens = llm_cfg.get("max_tokens", 4096)
        self.client = OpenAI(
            api_key=llm_cfg.get("api_key", ""),
            base_url=llm_cfg.get("base_url", "https://api.deepseek.com"),
        )
        self._log = logger()

    def chat(self, messages: list[dict[str, str]], response_format: str = "text") -> str:
        kwargs: dict[str, Any] = dict(
            model=self.model, messages=messages,
            temperature=self.temperature, max_tokens=self.max_tokens,
        )
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        self._log.debug("LLM call: %d messages, model=%s", len(messages), self.model)
        resp = self.client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content or ""
        self._log.debug("LLM response: %d chars", len(content))
        return content

    def chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        raw = self.chat(messages, response_format="json")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            self._log.warning("LLM returned invalid JSON; returning raw text")
            return {"raw": raw}


# ---------------------------------------------------------------------------
# Prompt templates (bilingual Chinese/English)
# ---------------------------------------------------------------------------

INTENT_SYSTEM = """你是一个因果推断分析专家。用户会提供一段关于数据分析需求的中文描述。
你的任务是将用户的需求解析为结构化的JSON输出。

规则：
1. "effect"（果/因变量）：用户想要提升、优化或解释的指标/变量。必须是数据中可能存在的变量名。
2. "treatment"（处理变量/因）：用户关注的或者已经实施的干预变量。如果用户没有明确说，用空字符串。
3. "candidate_causes"（潜在原因）：可能影响效果变量的特征，列出一组可能的原因。
4. "business_goal"（业务目标）：用一句话概括用户想达到的目标。
5. "constraints"：用户特别提到的分析方法或限制条件。
6. "methods"（因果推断方法）：如果用户在需求中明确指定了分析方法，将其映射为对应的方法名列表。
   可选方法名（必须严格使用以下内部名称）：
   - panel_regression: 面板回归、固定效应、随机效应
   - diff_in_diff: 双重差分、DID、DiD、倍差法
   - instrumental_variable: 工具变量、IV、2SLS
   - propensity_score: 倾向得分匹配、PSM、倾向性评分
   - double_ml: 双机器学习、DML
   - rdd: 断点回归、RDD、断点回归设计
   - dag_discovery: 因果图、DAG、因果发现
   如果用户未指定任何方法，则为空数组[]。
7. 如果信息不足以判断，设置 "needs_clarification": true 并提供追问问题。

只输出JSON，不要有其他内容。"""

INTENT_USER = """用户需求：{prompt}

数据中可用的列名：{columns}

请解析用户意图并输出JSON。"""

MODEL_SELECTION_SYSTEM = """你是一个计量经济学专家。根据数据的统计特征，帮助选择最合适的因果推断方法。

可用的方法：
- dag_discovery: 因果图发现（DAG），适合探索性分析，无需预设处理变量
- diff_in_diff: 双重差分（DiD），需要面板数据+处理前后时间+处理/对照组
- instrumental_variable: 工具变量（IV），需要有疑似工具变量
- panel_regression: 面板数据回归（固定效应/随机效应），有实体和时间维度
- propensity_score: 倾向得分匹配（PSM），截面数据，二值处理变量，有混淆变量
- double_ml: 双机器学习（DML），大样本+高维特征，存在混淆变量
- rdd: 断点回归（RDD），有明确的断点/阈值

请基于以下数据特征和用户意图，推荐1-3个最合适的方法，并给出简要理由。

只输出JSON：{{"selected_methods": ["method1", "method2"], "rationale": "理由", "confidence": 0.8}}"""

REPORT_SYSTEM = """你是一个数据分析报告撰写专家。请根据因果推断的结果，用中文生成一份清晰、严谨的分析报告。

要求：
1. 语言严谨但不晦涩，面向企业管理层
2. 解读显著性：p值的含义要解释清楚
3. 给出管理建议：基于因果效应的大小和方向，给出具体的行动建议
4. 如果结果不显著，也要诚实说明，并建议可能的改进方向"""

RECOMMENDATIONS_SYSTEM = """你是一个企业管理顾问。请基于因果推断分析的实证结果，为企业提供可操作的管理建议。

输出要求：
- 基于数据证据，而非主观判断
- 区分"强烈建议"（结果统计显著+效应量大）和"考虑尝试"（效应量小或不显著）
- 每条建议要具体、可落地
- 同时指出分析的局限性和注意事项"""

RECOMMENDATIONS_PROMPT = """业务目标：{business_goal}

分析发现：
{findings}

请生成3-5条管理建议。"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_pvalue(p: float) -> str:
    if p < 0.001:
        return f"{p:.4f}***"
    elif p < 0.01:
        return f"{p:.4f}**"
    elif p < 0.05:
        return f"{p:.4f}*"
    elif p < 0.1:
        return f"{p:.4f}."
    return f"{p:.4f}"
