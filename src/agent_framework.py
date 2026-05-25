"""
Agent Framework — core agent infrastructure, tool registry, causal inference pipeline.

Provides:
  - Tool implementations and registry
  - AgentRunner: LLM agent with tool-calling loop
  - CausalInferencePipeline: callable API for the 3-agent causal inference layer
  - AgentRegistry: unified agent definition management
"""

from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

# Project root
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_TURNS = 50

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def tool_shell_exec(command: str) -> str:
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        out = r.stdout
        if r.stderr:
            out += "\n[stderr]\n" + r.stderr
        if r.returncode != 0:
            out += f"\n[exit={r.returncode}]"
        return out.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "[error] timeout after 60s"
    except Exception as e:
        return f"[error] {e}"


def tool_file_read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 30000:
            content = content[:30000] + "\n... (truncated)"
        return content
    except Exception as e:
        return f"[error] {e}"


def tool_file_write(path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"OK - {len(content)} chars -> {path}"
    except Exception as e:
        return f"[error] {e}"


def tool_python_exec(code: str) -> str:
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name
        r = subprocess.run([sys.executable, tmp_path], capture_output=True, text=True, timeout=120, cwd=str(ROOT))
        out = r.stdout
        if r.stderr:
            out += "\n[stderr]\n" + r.stderr[:2000]
        return out.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "[error] execution timed out after 120s"
    except Exception as e:
        return f"[error] {e}"
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def tool_read_skill(skill_name: str) -> str:
    """Read a SKILL.md file into context."""
    skill_path = ROOT / "skills" / skill_name / "SKILL.md"
    if not skill_path.exists():
        available = [d.name for d in (ROOT / "skills").iterdir() if d.is_dir()]
        return f"[error] Skill '{skill_name}' not found. Available: {available}"
    return tool_file_read(str(skill_path))


def tool_run_causal_analysis(kwargs_json: str) -> str:
    """Run the causal inference pipeline and return structured results."""
    try:
        kwargs = json.loads(kwargs_json)
    except json.JSONDecodeError:
        return "[error] invalid JSON for run_causal_analysis"
    data_path = kwargs.get("data_path", "")
    prompt = kwargs.get("prompt", "")
    output_dir = kwargs.get("output_dir", "./output")
    methods = kwargs.get("methods", None)
    model = kwargs.get("model", "deepseek-v4-pro")
    api_key = kwargs.get("api_key", "")
    base_url = kwargs.get("base_url", "https://api.deepseek.com")

    # Fall back to environment / config when no explicit api_key passed
    if not api_key:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        from src.utils import load_config
        try:
            cfg = load_config()
            api_key = cfg.get("llm", {}).get("api_key", "")
            base_url = cfg.get("llm", {}).get("base_url", base_url)
        except Exception:
            pass

    if not data_path or not prompt:
        return "[error] run_causal_analysis requires data_path and prompt"

    client = OpenAI(api_key=api_key or "sk-placeholder", base_url=base_url)
    pipeline = CausalInferencePipeline()
    result = pipeline.run(data_path, prompt, client, model, output_dir, methods)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


def _make_tool_registry() -> dict[str, dict[str, Any]]:
    return {
        "shell_exec": {
            "function": tool_shell_exec,
            "schema": {
                "type": "function",
                "function": {
                    "name": "shell_exec", "description": "Execute a shell command",
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {"type": "string", "description": "Shell command"}},
                        "required": ["command"],
                    },
                },
            },
        },
        "file_read": {
            "function": tool_file_read,
            "schema": {
                "type": "function",
                "function": {
                    "name": "file_read", "description": "Read file contents",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string", "description": "File path"}},
                        "required": ["path"],
                    },
                },
            },
        },
        "file_write": {
            "function": tool_file_write,
            "schema": {
                "type": "function",
                "function": {
                    "name": "file_write", "description": "Write content to file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                            "content": {"type": "string", "description": "Content to write"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
        },
        "python_exec": {
            "function": tool_python_exec,
            "schema": {
                "type": "function",
                "function": {
                    "name": "python_exec",
                    "description": "Execute Python code. Use 'from src.data_processing import ...' or 'from src.causal_models import ...' etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {"code": {"type": "string", "description": "Python code"}},
                        "required": ["code"],
                    },
                },
            },
        },
        "read_skill": {
            "function": tool_read_skill,
            "schema": {
                "type": "function",
                "function": {
                    "name": "read_skill",
                    "description": "Read a SKILL.md reference file for methodology guidance.",
                    "parameters": {
                        "type": "object",
                        "properties": {"skill_name": {"type": "string", "description": "Skill name"}},
                        "required": ["skill_name"],
                    },
                },
            },
        },
        "run_causal_analysis": {
            "function": tool_run_causal_analysis,
            "schema": {
                "type": "function",
                "function": {
                    "name": "run_causal_analysis",
                    "description": (
                        "Run the full causal inference pipeline (data processing + causal inference + report). "
                        "Use this when you need to analyze data for causal relationships. "
                        "Provide args as JSON string with: data_path, prompt, output_dir, methods (optional), model (optional)."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "kwargs_json": {"type": "string", "description": "JSON string of keyword arguments"},
                        },
                        "required": ["kwargs_json"],
                    },
                },
            },
        },
    }


TOOLS = _make_tool_registry()


def get_tool_schemas() -> list[dict[str, Any]]:
    return [t["schema"] for t in TOOLS.values()]


# ---------------------------------------------------------------------------
# Agent Runner
# ---------------------------------------------------------------------------


class AgentRunner:
    """Manages an agent with a system prompt and tool-based conversation loop."""

    def __init__(
        self,
        system_prompt: str,
        client: OpenAI,
        model: str = "deepseek-v4-pro",
        max_turns: int = MAX_TURNS,
        extra_tools: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.client = client
        self.model = model
        self.max_turns = max_turns
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        self._tools = {**TOOLS, **(extra_tools or {})}
        self.tool_schemas = [t["schema"] for t in self._tools.values()]

    def run(self, user_message: str) -> str:
        """Run the agent loop with a user message. Returns the agent's final text response."""
        self.messages.append({"role": "user", "content": user_message})

        for turn in range(1, self.max_turns + 1):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tool_schemas,
            )
            choice = response.choices[0]
            msg = choice.message
            self.messages.append(msg.model_dump())

            if not msg.tool_calls:
                content = msg.content or ""
                print(f"\n{'─'*40}\n[Agent] 第{turn}轮完成，返回最终结果\n{'─'*40}")
                return content

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                # Truncate display for readability
                args_str = str(tc.function.arguments)
                if len(args_str) > 200:
                    args_str = args_str[:200] + "..."

                entry = self._tools.get(name)
                if entry:
                    sig = inspect.signature(entry["function"])
                    accepted = set(sig.parameters.keys())
                    filtered_args = {k: v for k, v in args.items() if k in accepted}
                    # Check for missing required arguments (LLM may omit them)
                    missing = [
                        p for p, param in sig.parameters.items()
                        if param.default is inspect.Parameter.empty and p not in filtered_args
                    ]
                    if missing:
                        result = f"[error] tool '{name}' missing required argument(s): {', '.join(missing)}. Please provide: {', '.join(missing)}"
                    else:
                        result = entry["function"](**filtered_args)
                else:
                    result = f"[error] unknown tool: {name}"

                # Print real-time progress
                if name == "python_exec":
                    code_preview = str(args.get("code", ""))[:150].replace("\n", " ")
                    print(f"  [{turn}] {name}: {code_preview}...")
                elif name == "run_causal_analysis":
                    kw = str(args.get("kwargs_json", ""))[:120]
                    print(f"  [{turn}] {name}: {kw}")
                else:
                    print(f"  [{turn}] {name}: {args_str[:120]}")

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })

        return "[Agent] 达到最大轮次，停止。"


# ---------------------------------------------------------------------------
# Agent prompt loader
# ---------------------------------------------------------------------------


def load_agent_prompt(agent_name: str) -> str:
    """Load an agent role definition from agents/<name>.md."""
    agent_path = ROOT / "agents" / f"{agent_name}.md"
    if not agent_path.exists():
        available = [f.stem for f in (ROOT / "agents").glob("*.md")]
        raise FileNotFoundError(
            f"Agent definition not found: {agent_path}. Available: {available}"
        )
    return agent_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Method name parsing
# ---------------------------------------------------------------------------

METHOD_ALIASES: dict[str, str] = {
    **{m: m for m in [
        "panel_regression", "diff_in_diff", "instrumental_variable",
        "propensity_score", "double_ml", "rdd", "dag_discovery",
    ]},
    "did": "diff_in_diff", "iv": "instrumental_variable",
    "2sls": "instrumental_variable", "psm": "propensity_score",
    "dml": "double_ml", "rdd": "rdd", "dag": "dag_discovery",
    "panel": "panel_regression", "fe": "panel_regression", "re": "panel_regression",
    "双重差分": "diff_in_diff", "倍差法": "diff_in_diff",
    "工具变量": "instrumental_variable",
    "倾向得分匹配": "propensity_score", "倾向性评分": "propensity_score",
    "双机器学习": "double_ml",
    "断点回归": "rdd", "断点回归设计": "rdd",
    "因果图": "dag_discovery", "因果发现": "dag_discovery",
    "面板回归": "panel_regression", "固定效应": "panel_regression", "随机效应": "panel_regression",
}


def parse_method_arg(raw: str) -> list[str]:
    """Parse comma-separated method names into internal keys."""
    result: list[str] = []
    for part in raw.split(","):
        key = part.strip().lower()
        if not key:
            continue
        mapped = METHOD_ALIASES.get(key)
        if mapped:
            if mapped not in result:
                result.append(mapped)
        else:
            print(f"  [警告] 未知方法名: '{part.strip()}'，已忽略。可用: {sorted(set(METHOD_ALIASES.keys()))}")
    return result


# ---------------------------------------------------------------------------
# Intent parsing
# ---------------------------------------------------------------------------


def parse_user_intent(
    prompt: str, data_paths: str | list[str], client: OpenAI, model: str = "deepseek-v4-pro"
) -> dict[str, Any]:
    """Parse user's Chinese business prompt into structured intent via a single LLM call.
    Accepts a single file path or a list of paths/globs/directories.
    """
    from src.data_processing import DataLoader
    from src.utils import INTENT_SYSTEM, INTENT_USER

    loader = DataLoader()
    # Resolve multi-file input
    if isinstance(data_paths, list) or "*" in str(data_paths) or "?" in str(data_paths):
        paths = [data_paths] if isinstance(data_paths, str) else data_paths
        raw = loader.load_multiple(paths, merge="auto")
    elif Path(data_paths).is_dir():
        raw = loader.load_multiple([data_paths], merge="auto")
    else:
        raw = loader.load(data_paths)

    if isinstance(raw, dict):
        # Multiple separate DataFrames — collect columns from all
        columns: list[str] = []
        file_info = {name: list(df.columns) for name, df in raw.items()}
        for cols in file_info.values():
            columns.extend(cols)
        columns = list(dict.fromkeys(columns))  # deduplicate keeping order
    else:
        columns = list(raw.columns)
        file_info = None

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": INTENT_SYSTEM},
            {"role": "user", "content": INTENT_USER.format(prompt=prompt, columns=columns)},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    intent: dict[str, Any] = json.loads(response.choices[0].message.content or "{}")
    intent["raw_prompt"] = prompt
    if isinstance(raw, dict):
        intent["_multi_file"] = True
        intent["_file_count"] = len(raw)
        intent["_file_columns"] = file_info
    return intent


# ---------------------------------------------------------------------------
# Causal Inference Pipeline (Layer 1 API)
# ---------------------------------------------------------------------------


class CausalInferencePipeline:
    """Callable API wrapping the 3-agent causal inference pipeline.

    Usage:
        pipeline = CausalInferencePipeline()
        result = pipeline.run(data_path, prompt, client, model, output_dir)
        # result = {intent, phase1_result, phase2_result, phase3_result, report_path}
    """

    def __init__(self) -> None:
        self._last_result: dict[str, Any] = {}

    def run(
        self,
        data_paths: str | list[str],
        prompt: str,
        client: OpenAI,
        model: str = "deepseek-v4-pro",
        output_dir: str = "./output",
        methods: list[str] | None = None,
        merge: str = "auto",
    ) -> dict[str, Any]:
        """Execute the full causal inference pipeline and return structured results.

        Args:
            data_paths: Single file path, or list of paths/globs/directories.
            prompt: Business analysis goal in Chinese.
            client: OpenAI-compatible client.
            model: Model name.
            output_dir: Output directory for graphs and reports.
            methods: Specific causal methods to use (optional).
            merge: Merge strategy for multiple files ("auto", "concat", "merge", "separate").
        """
        # Resolve to a normalized list of paths for display/validation
        path_list = [data_paths] if isinstance(data_paths, str) else data_paths
        # Expand globs/directories via the loader's resolver
        from src.data_processing import DataLoader as _DataLoader
        loader_temp = _DataLoader()
        try:
            resolved_paths = loader_temp._resolve_paths(path_list)
        except FileNotFoundError as e:
            return {"error": str(e)}

        # Ensure output dirs
        for d in ["output/graphs", "output/reports"]:
            (ROOT / d).mkdir(parents=True, exist_ok=True)

        n_files = len(resolved_paths)
        file_display = ", ".join(p.name for p in resolved_paths[:3])
        if n_files > 3:
            file_display += f" ... (+{n_files - 3} 个文件)"

        print(f"\n{'='*60}")
        print(f"  Causal Inference Pipeline (Layer 1)")
        print(f"{'='*60}")
        print(f"  数据({n_files}个文件): {file_display}")
        print(f"  合并策略: {merge}")
        print(f"  目标: {prompt}")

        # -----------------------------------------------------------------
        # Phase 0: Parse user intent
        # -----------------------------------------------------------------
        print(f"\n{'─'*50}")
        print("[Phase 0] 解析用户意图...")
        print("─" * 50)
        try:
            intent = parse_user_intent(prompt, data_paths, client, model=model)
            print(f"  业务目标: {intent.get('business_goal', intent.get('raw_prompt', ''))}")
            print(f"  效果变量: {intent.get('effect', '待识别')}")
            print(f"  处理变量: {intent.get('treatment', '待识别')}")
            if intent.get("_multi_file"):
                print(f"  多文件模式: {intent.get('_file_count', 0)} 个数据集")
        except Exception as e:
            print(f"  [警告] 意图解析失败: {e}")
            intent = {"raw_prompt": prompt, "business_goal": prompt}

        if methods:
            intent["methods"] = methods
            print(f"  指定方法: {', '.join(methods)}")
        else:
            llm_methods = intent.get("methods", [])
            if llm_methods:
                print(f"  从需求中识别到方法: {', '.join(llm_methods)}")

        # Build a data file reference string for agent messages
        data_ref = "\n".join(f"  - {p.absolute()}" for p in resolved_paths)
        merge_note = f"\n**合并策略**: {merge}" if n_files > 1 else ""

        # -----------------------------------------------------------------
        # Phase 1: Data Processing Agent
        # -----------------------------------------------------------------
        print(f"\n{'─'*50}")
        print("[Phase 1] 数据清洗与探索性分析 (Data Processing Agent)...")
        print("─" * 50)
        dp_prompt = load_agent_prompt("data-processing")
        dp_runner = AgentRunner(dp_prompt, client, model=model)
        dp_message = f"""请处理以下数据文件并完成数据清洗和探索性分析：
**数据文件** ({n_files}个):
{data_ref}{merge_note}
**输出目录**: {output_dir}
用户意图分析结果：
{json.dumps(intent, ensure_ascii=False, indent=2)}
"""
        phase1_result = dp_runner.run(dp_message)
        print(f"  [Phase 1] 数据清洗完成")

        # -----------------------------------------------------------------
        # Phase 2: Causal Inference Agent
        # -----------------------------------------------------------------
        print(f"\n{'─'*50}")
        print("[Phase 2] 模型选择与因果推断 (Causal Inference Agent)...")
        print("─" * 50)
        ci_prompt = load_agent_prompt("causal-inference")
        ci_runner = AgentRunner(ci_prompt, client, model=model)

        user_methods = intent.get("methods", [])
        if user_methods:
            methods_directive = f"""用户已明确指定因果推断方法: {user_methods}。
请直接使用这些方法进行分析，跳过自动评分选择步骤。
使用 run_models 时，将 selected={user_methods} 传入即可。
"""
        else:
            methods_directive = ""

        ci_message = f"""{methods_directive}请基于清洗后的数据执行因果推断分析。

用户意图（来自Phase 0）:
{json.dumps(intent, ensure_ascii=False, indent=2)}

数据处理阶段的结果:
{phase1_result}

输出目录: {output_dir}
"""
        phase2_result = ci_runner.run(ci_message)
        print(f"  [Phase 2] 因果推断完成")

        graphs_dir = str(ROOT / output_dir / "graphs")
        result = {
            "intent": intent,
            "phase1_result": phase1_result,
            "phase2_result": phase2_result,
            "graphs_path": graphs_dir,
            "data_path": str(data_paths) if isinstance(data_paths, str) else ", ".join(data_paths),
        }
        self._last_result = result
        return result

    @property
    def last_result(self) -> dict[str, Any]:
        return self._last_result


def generate_final_report(
    pipeline_result: dict[str, Any],
    output_dir: str,
    client: OpenAI,
    model: str = "deepseek-v4-pro",
    extra_context: dict[str, Any] | None = None,
) -> str:
    """Generate a single comprehensive Word report from pipeline results.

    Args:
        pipeline_result: The dict returned by CausalInferencePipeline.run().
        output_dir: Output directory (report saved to output_dir/reports/).
        client: OpenAI-compatible client.
        model: Model name.
        extra_context: Optional additional results (e.g., workflow outputs).

    Returns:
        The report-generator agent's final message (contains report path info).
    """
    print(f"\n{'─'*50}")
    print("[Report] 生成综合分析报告 (Report Generator Agent)...")
    print("─" * 50)

    rg_prompt = load_agent_prompt("report-generator")
    rg_runner = AgentRunner(rg_prompt, client, model=model)

    intent = pipeline_result.get("intent", {})
    phase1 = pipeline_result.get("phase1_result", "")
    phase2 = pipeline_result.get("phase2_result", "")
    graphs_dir = pipeline_result.get("graphs_path", f"{output_dir}/graphs")

    extra_str = ""
    if extra_context:
        extra_str = f"""
**额外分析上下文**（来自工作流各步骤的汇总结果）:
{json.dumps(extra_context, ensure_ascii=False, indent=2, default=str)[:8000]}
"""

    rg_message = f"""请生成一份**深度综合分析报告**。这份报告是本次运行的唯一最终报告，应综合所有分析阶段的结果，详尽深入。

**报告要求**:
- 内容深度详细，综合系统运行前后所有分析进行撰写
- 包含所有因果推断发现、数据洞察、管理建议
- 交叉引用不同分析阶段的结果，形成完整的分析链路
- 引用所有生成的图表（图表目录: {graphs_dir}）
- 报告语言为中文，面向管理决策层

用户意图:
{json.dumps(intent, ensure_ascii=False, indent=2)}

数据处理阶段结果:
{phase1}

因果推断阶段结果:
{phase2}
{extra_str}
图表目录: {graphs_dir}
输出目录: {output_dir}
"""
    rg_result = rg_runner.run(rg_message)
    print(f"\n{'='*60}")
    print(rg_result)
    print(f"{'='*60}")
    return rg_result


# ---------------------------------------------------------------------------
# Agent Output Manager — per-agent output storage with summary manifests
# ---------------------------------------------------------------------------

class AgentOutputManager:
    """Manages per-agent output directories with summary.json manifests.

    Each agent's outputs are stored under ``base_dir/{agent_name}/``.
    A ``summary.json`` file lists every saved file with a short description,
    enabling downstream agents to quickly discover and reuse previous results.
    """

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def agent_dir(self, agent_name: str) -> Path:
        """Return the output directory for a specific agent."""
        d = self.base_dir / agent_name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _summary_path(self, agent_name: str) -> Path:
        return self.agent_dir(agent_name) / "summary.json"

    def _read_summary(self, agent_name: str) -> dict[str, str]:
        """Read existing summary.json, return {filename: description}."""
        sp = self._summary_path(agent_name)
        if sp.exists():
            try:
                return json.loads(sp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception):
                pass
        return {}

    def _write_summary(self, agent_name: str, files: dict[str, str]) -> None:
        """Write summary.json with {filename: description}."""
        sp = self._summary_path(agent_name)
        sp.write_text(json.dumps(files, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_output(
        self, agent_name: str, filename: str, content: str,
        description: str = "",
    ) -> Path:
        """Save a file in the agent's output directory and update summary.json.

        Args:
            agent_name: e.g. "user_profiling"
            filename: e.g. "profile.json" or "cleaned_data.csv"
            content: file content (text or CSV string)
            description: short human-readable summary for summary.json

        Returns:
            Path to the saved file.
        """
        ad = self.agent_dir(agent_name)
        filepath = ad / filename
        filepath.write_text(content, encoding="utf-8")

        summary = self._read_summary(agent_name)
        summary[filename] = description or filename
        self._write_summary(agent_name, summary)
        return filepath

    def scan_all(self) -> dict[str, dict[str, str]]:
        """Scan all agent dirs and return their summary.json contents.

        Returns:
            {agent_name: {filename: description, ...}, ...}
            Only includes agents that have a valid summary.json.
        """
        result: dict[str, dict[str, str]] = {}
        if not self.base_dir.exists():
            return result
        for d in sorted(self.base_dir.iterdir()):
            if d.is_dir():
                summary = self._read_summary(d.name)
                if summary:
                    result[d.name] = summary
        return result

    def get_output(self, agent_name: str, filename: str) -> str | None:
        """Read a specific file from an agent's output directory.
        Returns file content as string, or None if not found.
        """
        filepath = self.agent_dir(agent_name) / filename
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        return None

    def format_context_for_agent(self) -> str:
        """Build a context string listing all available outputs for an agent prompt.

        Returns a formatted string suitable for inclusion in an agent's user_message,
        or an empty string if no previous outputs exist.
        """
        all_summaries = self.scan_all()
        if not all_summaries:
            return ""

        lines = ["## 之前智能体已产生的文件清单（可按需使用 file_read 读取）", ""]
        for agent_name, files in all_summaries.items():
            lines.append(f"### {agent_name}/")
            for fname, desc in files.items():
                lines.append(f"  - `{fname}`: {desc}")
            lines.append("")
        lines.append("请先检查上述清单：如果已有文件满足你的需求，直接使用 file_read 读取；如果没有，再自行计算或调用因果推断。")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent Registry
# ---------------------------------------------------------------------------


class AgentRegistry:
    """Unified management of agent definitions across all three layers."""

    def __init__(self) -> None:
        self._builtin_dir = ROOT / "agents"
        self._custom_dir: Path | None = None

    def set_custom_dir(self, path: str | Path) -> None:
        self._custom_dir = Path(path)

    def list_builtin(self) -> list[str]:
        return sorted(f.stem for f in self._builtin_dir.glob("*.md"))

    def list_custom(self) -> list[str]:
        if not self._custom_dir or not self._custom_dir.exists():
            return []
        agent_dir = self._custom_dir / "agents"
        if not agent_dir.exists():
            return []
        return sorted(f.stem for f in agent_dir.glob("*.md"))

    def list_all(self) -> dict[str, list[str]]:
        return {
            "builtin": self.list_builtin(),
            "custom": self.list_custom(),
        }

    def load(self, agent_name: str, custom_group: str | None = None) -> str:
        """Load agent prompt by name. Searches builtin first, then custom."""
        if custom_group and self._custom_dir:
            custom_path = self._custom_dir / custom_group / "agents" / f"{agent_name}.md"
            if custom_path.exists():
                return custom_path.read_text(encoding="utf-8")

        return load_agent_prompt(agent_name)

    def register_custom(self, group_name: str, agent_name: str, prompt_content: str) -> Path:
        """Save a custom agent prompt to custom/{group}/agents/{name}.md."""
        if not self._custom_dir:
            raise ValueError("custom_dir not set. Call set_custom_dir() first.")
        agent_path = self._custom_dir / group_name / "agents" / f"{agent_name}.md"
        agent_path.parent.mkdir(parents=True, exist_ok=True)
        agent_path.write_text(prompt_content, encoding="utf-8")
        return agent_path
