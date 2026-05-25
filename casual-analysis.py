#!/usr/bin/env python3
"""
AI-Driven Causal Inference System — Multi-Agent Pipeline Architecture.

The system supports the following operating modes:

  Mode A — Direct causal analysis (existing):
    python casual-analysis.py --data data.csv --prompt "提高参保率"

  Mode B — Custom agent creation + analysis:
    python casual-analysis.py --agent-file requirements.txt --data data.csv --prompt "分析目标"
    python casual-analysis.py --agent-file requirements.txt  (仅创建，无数据分析)

  Mode C — Run a previously created custom agent:
    python casual-analysis.py --run-agent agent-name --data data.csv --prompt "分析目标"

Architecture (3 layers):
  Layer 1 — Causal Inference:  data-processing → causal-inference → report-generator
  Layer 2 — Analysis & Build: coordinator → agent-creator + knowledge-matcher + workflow-designer
  Layer 3 — Task-Oriented:     dynamically generated custom agents (stored in custom/)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI

# Project root
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.agent_framework import (
    AgentRunner,
    CausalInferencePipeline,
    generate_final_report,
    load_agent_prompt,
    parse_method_arg,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = ROOT / "config.yaml"


def _resolve_env_vars(value: str) -> str:
    pat = re.compile(r"\$\{(\w+)}")

    def _repl(m: re.Match) -> str:
        return os.environ.get(m.group(1), "")

    return pat.sub(_repl, value)


def _resolve_dict(d: dict[str, Any]) -> dict[str, Any]:
    for k, v in d.items():
        if isinstance(v, str):
            d[k] = _resolve_env_vars(v)
        elif isinstance(v, dict):
            d[k] = _resolve_dict(v)
    return d


def load_config(path: str | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_CONFIG
    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return _resolve_dict(raw)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AI因果推断分析系统 (Multi-Agent)")
    # Mode A: direct analysis (existing)
    p.add_argument("--data", "-d", nargs="*", default=None, help="数据文件路径（支持多个文件、通配符、目录）")
    p.add_argument("--prompt", "-p", default=None, help="分析目标 (中文)")
    # Mode B: custom agent creation
    p.add_argument("--create-agent", "-A", default=None,
                   help="创建自定义Agent (直接输入需求描述)")
    p.add_argument("--agent-file", "-F", default=None,
                   help="创建自定义Agent (从文件读取需求描述)")
    p.add_argument("--name", "-n", default=None,
                   help="自定义Agent组名称 (与 --create-agent/--agent-file 配合使用)")
    # Mode C: run custom agent
    p.add_argument("--run-agent", "-R", default=None,
                   help="运行已创建的自定义Agent组")
    # Clean up
    p.add_argument("--clean-agent", "-C", default=None,
                   help="清除指定的自定义Agent组")
    p.add_argument("--list-agents", "-L", action="store_true", default=False,
                   help="列出所有已创建的自定义Agent组")
    # Common options
    p.add_argument("--output", "-o", default="./output", help="输出目录")
    p.add_argument("--config", "-c", default=None, help="配置文件")
    p.add_argument("--interactive", "-i", action="store_true", default=False)
    p.add_argument("--model", "-m", default=None, help="LLM模型")
    p.add_argument("--method", "-M", default="", help="因果推断方法 (逗号分隔)")

    return p.parse_args()


# ---------------------------------------------------------------------------
# Mode A: Direct causal analysis pipeline
# ---------------------------------------------------------------------------


def run_direct_analysis_pipeline(args: argparse.Namespace) -> None:
    """Run the existing 3-agent causal inference pipeline directly on data."""
    data_paths = args.data  # list of str or None
    if not data_paths:
        print("错误: 未指定数据文件。使用 --data <文件路径> 指定。")
        sys.exit(1)

    # Validate at least one file exists (globs/dirs resolved by pipeline)
    from src.data_processing import DataLoader
    loader = DataLoader()
    try:
        resolved = loader._resolve_paths(data_paths)
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)

    config = load_config(args.config)
    config["pipeline"] = config.get("pipeline", {})
    config["pipeline"]["output_dir"] = args.output
    config["pipeline"]["interactive"] = args.interactive

    llm_cfg = config.get("llm", {})
    api_key = llm_cfg.get("api_key", "") or os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("警告: 未设置LLM API Key。请在 config.yaml 的 llm.api_key 中配置。")

    model = args.model or llm_cfg.get("model", "deepseek-v4-pro")
    client = OpenAI(
        api_key=api_key or "sk-placeholder",
        base_url=llm_cfg.get("base_url", "https://api.deepseek.com"),
    )

    for d in ["output/graphs", "output/reports"]:
        (ROOT / d).mkdir(parents=True, exist_ok=True)

    n_files = len(resolved)
    file_display = ", ".join(p.name for p in resolved[:3])
    if n_files > 3:
        file_display += f" ... (+{n_files - 3} 个文件)"

    print("=" * 60)
    print("  AI因果推断分析系统 (直接分析模式)")
    print("=" * 60)
    print(f"  数据({n_files}个文件): {file_display}")
    print(f"  目标: {args.prompt}")
    if args.method:
        print(f"  指定方法: {args.method}")
    print(f"  模型: {model}")
    print("=" * 60)

    pipeline = CausalInferencePipeline()
    methods = parse_method_arg(args.method) if args.method else None
    result = pipeline.run(
        data_paths, args.prompt, client, model, args.output, methods
    )

    # Generate the single final report
    generate_final_report(result, args.output, client, model)

    print(f"\n输出目录: {args.output}/")
    print("分析完成。")


# ---------------------------------------------------------------------------
# Mode B: Custom agent creation pipeline
# ---------------------------------------------------------------------------


def run_custom_agent_creation_pipeline(
    requirements_text: str,
    client: OpenAI,
    model: str,
    agent_name: str | None = None,
    uploaded_files: list[str] | None = None,
    data_paths: list[str] | str | None = None,
    prompt: str | None = None,
    output_dir: str = "./output",
) -> str:
    """
    Mode B: Create custom agents from user requirements.

    If data_paths + prompt are provided:
      Phase 2-1 ~ 2-2c: Create agents (coordinate → build → knowledge → workflow)
      Phase 2-3: Run the created workflow on data
      Phase 2-4: Generate comprehensive report (system design + analysis)

    If no data:
      Phase 2-1 ~ 2-2c: Create agents
      Phase 2-3: Generate capability report (system design only)
    """
    from src.custom_agent import CustomAgentManager

    manager = CustomAgentManager()

    # -----------------------------------------------------------------------
    # Phase 2-0: Determine agent group name
    # -----------------------------------------------------------------------
    print(f"\n{'─'*50}")
    print("[Phase 2-0] 确定Agent组名称...")
    print("─" * 50)

    if not agent_name:
        # Ask LLM to generate a short English slug from the requirements
        name_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": (
                    "You are a naming assistant. Given a user's requirements for a custom AI agent system, "
                    "generate a short, descriptive English slug name (lowercase, hyphens for spaces, "
                    "max 40 characters). Examples: 'insurance-renewal-boost', 'marketing-cost-optimizer'. "
                    "Output ONLY the slug, nothing else."
                )},
                {"role": "user", "content": requirements_text[:2000]},
            ],
            temperature=0.3,
        )
        agent_name = name_response.choices[0].message.content.strip().lower()
        agent_name = re.sub(r"[^a-z0-9-]", "", agent_name)[:40]
        print(f"  自动生成名称: {agent_name}")
    else:
        print(f"  使用指定名称: {agent_name}")

    # Initialize storage
    group_path = manager.create_agent_group(agent_name, requirements_text)
    print(f"  存储路径: {group_path}")

    # Copy uploaded files if any
    if uploaded_files:
        for f in uploaded_files:
            manager.copy_uploaded_file(agent_name, f)
            print(f"  已上传: {Path(f).name}")

    # -----------------------------------------------------------------------
    # Phase 2-1: Coordination agent — analyze & decompose
    # -----------------------------------------------------------------------
    print(f"\n{'─'*50}")
    print("[Phase 2-1] 协调Agent分析需求、拆解任务...")
    print("─" * 50)

    coordinator_prompt = load_agent_prompt("coordinator")
    coordinator = AgentRunner(coordinator_prompt, client, model=model)

    coord_message = f"""请分析以下用户对智能体系统的需求，输出结构化的任务拆解JSON。

用户需求描述：
---
{requirements_text}
---

输出要求：
1. 分析用户需要哪些新智能体（每个智能体的名称、角色、职责、所需工具）
2. 分析每个智能体需要匹配哪些知识库和skill
3. 设计这些智能体的工作流程（执行顺序、数据传递、依赖关系）
4. 分析哪些智能体需要调用因果推断层的能力，以及如何调用
5. 如果有用户上传的文件，请参考使用

只输出JSON，格式如下：
```json
{{
  "agents_to_create": [
    {{
      "name": "agent-name",
      "role": "一句话角色描述",
      "responsibilities": ["职责1", "职责2"],
      "tools_needed": ["python_exec", "read_skill"],
      "interaction_with_causal_layer": "是否需要/如何使用因果推断层"
    }}
  ],
  "knowledge_requirements": [
    {{
      "agent_name": "对应的agent名称",
      "topic": "知识主题",
      "description": "需要哪些具体知识",
      "user_uploaded": false,
      "necessity": "critical|helpful|optional"
    }}
  ],
  "workflow": {{
    "description": "工作流总体描述",
    "steps": [
      {{
        "order": 1,
        "agent": "agent-name",
        "action": "该步骤做什么",
        "depends_on": [],
        "output_to": ["下游agent名称"]
      }}
    ]
  }},
  "causal_layer_usage": {{
    "needed": true,
    "usage_description": "描述自定义agent如何调用因果推断层",
    "trigger_points": ["何时触发因果分析"]
  }}
}}
```
"""
    task_plan_text = coordinator.run(coord_message)

    # Extract JSON from coordinator response (may be wrapped in markdown)
    try:
        if "```json" in task_plan_text:
            json_start = task_plan_text.index("```json") + 7
            json_end = task_plan_text.index("```", json_start)
            task_plan_text = task_plan_text[json_start:json_end].strip()
        elif "```" in task_plan_text:
            json_start = task_plan_text.index("```") + 3
            json_end = task_plan_text.index("```", json_start)
            task_plan_text = task_plan_text[json_start:json_end].strip()
    except ValueError:
        pass

    try:
        task_plan = json.loads(task_plan_text)
    except json.JSONDecodeError:
        print("  [警告] 协调Agent输出非标准JSON，尝试修复...")
        # Attempt to find JSON-like content
        import re as _re
        match = _re.search(r'\{.*\}', task_plan_text, _re.DOTALL)
        if match:
            task_plan = json.loads(match.group(0))
        else:
            raise RuntimeError("无法解析协调Agent的输出为JSON")

    manager.save_task_plan(agent_name, task_plan)
    print(f"  任务拆解完成: {len(task_plan.get('agents_to_create', []))}个新Agent待创建")

    # -----------------------------------------------------------------------
    # Phase 2-2a: Agent Creator — generate agent prompt files
    # -----------------------------------------------------------------------
    print(f"\n{'─'*50}")
    print("[Phase 2-2a] 智能体创建Agent — 生成Agent Prompt...")
    print("─" * 50)

    creator_prompt = load_agent_prompt("agent-creator")
    creator = AgentRunner(creator_prompt, client, model=model)

    creator_message = f"""请根据以下任务计划创建所有新Agent的system prompt文件。

任务计划 (agents_to_create):
{json.dumps(task_plan.get('agents_to_create', []), ensure_ascii=False, indent=2)}

因果推断层调用需求:
{json.dumps(task_plan.get('causal_layer_usage', {}), ensure_ascii=False, indent=2)}

工作流描述:
{json.dumps(task_plan.get('workflow', {}), ensure_ascii=False, indent=2)}

对每个Agent，请使用 file_write 工具将prompt保存到:
custom/{agent_name}/agents/<agent-name>.md

每个prompt必须包含：
1. 角色定义（你是xxx，负责xxx）
2. 职责清单
3. 可用工具及使用方式
4. 如何调用因果推断层（如果需要的话 — 使用 run_causal_analysis 工具）
5. 输入/输出规范
6. 工作示例

存储路径前缀: custom/{agent_name}/
"""
    creator_result = creator.run(creator_message)
    print(f"  智能体Prompt生成完成")
    print(f"  {creator_result[:300]}...")

    # -----------------------------------------------------------------------
    # Phase 2-2b: Knowledge Matcher — evaluate necessity, gather knowledge
    # -----------------------------------------------------------------------
    print(f"\n{'─'*50}")
    print("[Phase 2-2b] 知识库与Skill匹配Agent — 判断必要性并匹配知识...")
    print("─" * 50)

    kmatcher_prompt = load_agent_prompt("knowledge-matcher")
    kmatcher = AgentRunner(kmatcher_prompt, client, model=model)

    # List uploaded files for the agent to reference
    uploaded_list = ""
    upload_dir = group_path / "knowledge" / "uploaded"
    if upload_dir.exists():
        uploaded_files_list = list(upload_dir.iterdir())
        if uploaded_files_list:
            uploaded_list = "\n用户已上传的文件:\n" + "\n".join(
                f"  - {f.name} (路径: {f.absolute()})" for f in uploaded_files_list
            )

    kmatcher_message = f"""请根据以下知识需求，为每个Agent匹配知识库和Skill。

知识需求列表:
{json.dumps(task_plan.get('knowledge_requirements', []), ensure_ascii=False, indent=2)}

Agent创建计划:
{json.dumps(task_plan.get('agents_to_create', []), ensure_ascii=False, indent=2)}
{uploaded_list}

处理规则（严格按优先级）：
1. 如果用户已上传了相关知识资料 → 直接使用（复制到对应目录）
2. 如果用户未上传 → 先判断该知识是否必要（该Agent缺了它能否正常工作）
   - 若不必要 → 跳过，标注"已跳过-非必要"
   - 若必要 → 按以下顺序获取：
     a. 通过 shell_exec 从高质量开源渠道搜索/下载
     b. 自行生成（如编写SKILL.md、整理知识文档）
     c. 以上均不可得 → 整理索取清单，明确向用户索要
3. 为每个保留的知识项生成或复制对应SKILL.md到 custom/{agent_name}/skills/

存储路径:
- 知识库: custom/{agent_name}/knowledge/collected/
- Skills: custom/{agent_name}/skills/
"""
    kmatcher_result = kmatcher.run(kmatcher_message)
    print(f"  知识匹配完成")
    print(f"  {kmatcher_result[:300]}...")

    # -----------------------------------------------------------------------
    # Phase 2-2c: Workflow Designer — generate orchestration code
    # -----------------------------------------------------------------------
    print(f"\n{'─'*50}")
    print("[Phase 2-2c] 工作流设定Agent — 生成编排代码...")
    print("─" * 50)

    wfdesigner_prompt = load_agent_prompt("workflow-designer")
    wfdesigner = AgentRunner(wfdesigner_prompt, client, model=model)

    # List created agents so far
    agents_dir = group_path / "agents"
    created_agents = list(agents_dir.glob("*.md")) if agents_dir.exists() else []
    created_list = "\n已创建的Agent文件:\n" + "\n".join(
        f"  - custom/{agent_name}/agents/{f.name}" for f in created_agents
    ) if created_agents else ""

    wfdesigner_message = f"""请根据以下工作流描述，生成Agent编排代码。

Agent组名称: {agent_name}

工作流设计:
{json.dumps(task_plan.get('workflow', {}), ensure_ascii=False, indent=2)}

Agent清单:
{json.dumps(task_plan.get('agents_to_create', []), ensure_ascii=False, indent=2)}

因果推断层调用:
{json.dumps(task_plan.get('causal_layer_usage', {}), ensure_ascii=False, indent=2)}
{created_list}

请生成一个可执行的Python工作流文件，保存到: custom/{agent_name}/workflow.py

工作流代码要求：
1. 定义一个 WorkflowRunner 类（或 run_workflow 函数）
2. 接收参数: data_path, prompt, client, model, output_dir
3. 使用 AgentRunner 加载 custom/{agent_name}/agents/ 下的agent prompt
4. 按照工作流设计按顺序/并行调度各Agent
5. 在需要时调用 CausalInferencePipeline 进行分析
6. 包含异常处理和日志输出
7. 返回结构化结果

你可以参考以下导入方式：
```python
from src.agent_framework import AgentRunner, CausalInferencePipeline, load_agent_prompt
```

使用 file_write 工具保存代码到 custom/{agent_name}/workflow.py
"""
    wfdesigner_result = wfdesigner.run(wfdesigner_message)
    print(f"  工作流代码生成完成")
    print(f"  {wfdesigner_result[:300]}...")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"  自定义Agent组创建完成!")
    print(f"  名称: {agent_name}")
    print(f"  路径: {group_path}")
    print(f"{'='*60}")
    print(f"\n生成的文件:")
    for f in sorted(group_path.rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(group_path)}")

    # -----------------------------------------------------------------------
    # Branch: run workflow if data is provided, else capability report only
    # -----------------------------------------------------------------------
    if data_paths and prompt:
        # ---------------------------------------------------------------
        # Phase 2-3: Run the created workflow on data
        # ---------------------------------------------------------------
        print(f"\n{'─'*50}")
        print("[Phase 2-3] 运行创建的Agent工作流...")
        print("─" * 50)

        # Resolve data paths (handle list, globs, directories)
        from src.data_processing import DataLoader as _DL
        _loader = _DL()
        path_list = [data_paths] if isinstance(data_paths, str) else data_paths
        try:
            resolved = _loader._resolve_paths(path_list)
        except FileNotFoundError:
            print(f"  警告: 数据文件未找到: {data_paths}，跳过分析。")
            resolved = []

        if not resolved:
            print(f"  警告: 未找到可加载的数据文件，跳过分析。")
        else:
            workflow_path = group_path / "workflow.py"
            if not workflow_path.exists():
                print(f"  警告: workflow.py 未生成，跳过分析。")
            else:
                namespace: dict[str, Any] = {"__file__": str(workflow_path)}
                workflow_code = workflow_path.read_text(encoding="utf-8")
                exec(workflow_code, namespace)

                workflow_result: dict[str, Any] = {}
                if "run_workflow" in namespace:
                    workflow_result = namespace["run_workflow"](
                        data_path=data_paths, prompt=prompt,
                        client=client, model=model, output_dir=output_dir,
                    )
                elif "WorkflowRunner" in namespace:
                    runner = namespace["WorkflowRunner"]()
                    workflow_result = runner.run(
                        data_path=data_paths, prompt=prompt,
                        client=client, model=model, output_dir=output_dir,
                    )
                else:
                    print(f"  警告: workflow.py 中未找到 run_workflow 或 WorkflowRunner，跳过分析。")

                if workflow_result:
                    print(f"  [Phase 2-3] 工作流执行完成")

                    # -----------------------------------------------------------
                    # Phase 2-4: Comprehensive report (system design + analysis)
                    # -----------------------------------------------------------
                    print(f"\n{'─'*50}")
                    print("[Phase 2-4] 生成综合分析报告 (Report Generator Agent)...")
                    print("─" * 50)

                    causal_from_wf = workflow_result.get("causal_analysis") if isinstance(workflow_result, dict) else None

                    created_agent_list = []
                    agents_dir = group_path / "agents"
                    if agents_dir.exists():
                        for f in agents_dir.glob("*.md"):
                            prompt_text = f.read_text(encoding="utf-8")
                            preview = prompt_text.split("\n")[0] if prompt_text else ""
                            created_agent_list.append({"name": f.stem, "description": preview})

                    _generate_final_report(
                        client=client, model=model, output_dir=output_dir,
                        agent_group_name=agent_name or "",
                        intent_context={
                            "business_goal": prompt,
                            "agent_group": agent_name,
                            "raw_requirements": requirements_text[:1500],
                            "data_path": data_paths,
                            "mode": "custom_agent_creation_with_data",
                        },
                        causal_results=causal_from_wf,
                        custom_outputs={
                            "agent_system_design": task_plan,
                            "created_agents": created_agent_list,
                            "agent_analysis_results": workflow_result if isinstance(workflow_result, dict) else {"raw": str(workflow_result)[:5000]},
                        },
                        report_type="comprehensive",
                    )
                    print(f"  [Phase 2-4] 综合分析报告完成")
    else:
        # ---------------------------------------------------------------
        # Phase 2-3: Capability report only (no data to analyze)
        # ---------------------------------------------------------------
        print(f"\n{'─'*50}")
        print("[Phase 2-3] 生成系统能力报告 (Report Generator Agent)...")
        print("─" * 50)

        created_agent_list = []
        agents_dir = group_path / "agents"
        if agents_dir.exists():
            for f in agents_dir.glob("*.md"):
                prompt_text = f.read_text(encoding="utf-8")
                preview = prompt_text.split("\n")[0] if prompt_text else ""
                created_agent_list.append({"name": f.stem, "description": preview})

        files_generated = [str(f.relative_to(group_path)) for f in sorted(group_path.rglob("*")) if f.is_file()]

        _generate_final_report(
            client=client, model=model, output_dir=output_dir,
            agent_group_name=agent_name or "",
            intent_context={
                "business_goal": f"构建业务智能体系统: {agent_name}",
                "raw_prompt": requirements_text[:1500],
                "mode": "custom_agent_creation",
            },
            causal_results=None,
            custom_outputs={
                "agent_group_name": agent_name,
                "agent_system_design": task_plan,
                "created_agents": created_agent_list,
                "knowledge_result": kmatcher_result[:3000],
                "workflow_result": wfdesigner_result[:3000],
                "files_generated": files_generated,
            },
            report_type="capability",
        )
        print(f"  [Phase 2-3] 系统能力报告完成")
        print(f"\n运行方式:")
        print(f"  python casual-analysis.py --run-agent {agent_name} --data <数据文件> --prompt \"<分析目标>\"")

    return agent_name


# ---------------------------------------------------------------------------
# Mode C: Run custom agent
# ---------------------------------------------------------------------------


def run_custom_agent_execution(
    agent_name: str,
    data_paths: list[str] | str | None,
    prompt: str | None,
    client: OpenAI,
    model: str,
    output_dir: str,
) -> dict[str, Any]:
    """Load and run a previously created custom agent group."""
    from src.custom_agent import CustomAgentManager

    manager = CustomAgentManager()
    group_path = manager.get_agent_group_path(agent_name)

    if not group_path or not group_path.exists():
        print(f"错误: 自定义Agent组 '{agent_name}' 不存在。")
        available = manager.list_agent_groups()
        if available:
            print(f"可用的Agent组: {', '.join(available)}")
        else:
            print("尚未创建任何自定义Agent组。")
        sys.exit(1)

    workflow_path = group_path / "workflow.py"
    if not workflow_path.exists():
        print(f"错误: Agent组 '{agent_name}' 缺少 workflow.py 文件。")
        sys.exit(1)

    print("=" * 60)
    print(f"  自定义Agent执行模式")
    print(f"  Agent组: {agent_name}")
    print(f"  数据: {data_paths}")
    print(f"  目标: {prompt}")
    print("=" * 60)

    # Execute the workflow
    namespace: dict[str, Any] = {"__file__": str(workflow_path)}
    workflow_code = workflow_path.read_text(encoding="utf-8")
    exec(workflow_code, namespace)

    if "run_workflow" in namespace:
        result = namespace["run_workflow"](
            data_path=data_paths,
            prompt=prompt,
            client=client,
            model=model,
            output_dir=output_dir,
        )
    elif "WorkflowRunner" in namespace:
        runner = namespace["WorkflowRunner"]()
        result = runner.run(
            data_path=data_paths,
            prompt=prompt,
            client=client,
            model=model,
            output_dir=output_dir,
        )
    else:
        print(f"警告: workflow.py 中未找到 run_workflow 函数或 WorkflowRunner 类。")
        result = {"error": "No run_workflow or WorkflowRunner found in workflow.py"}

    # -----------------------------------------------------------------------
    # Phase Final: Report Generation — 统一生成综合分析报告
    # -----------------------------------------------------------------------
    print(f"\n{'─'*50}")
    print("[Phase Final] 生成综合分析报告 (Report Generator Agent)...")
    print("─" * 50)

    causal_from_workflow = result.get("causal_analysis") if isinstance(result, dict) else None

    _generate_final_report(
        client=client, model=model, output_dir=output_dir,
        agent_group_name=agent_name,
        intent_context={
            "business_goal": prompt or "",
            "agent_group": agent_name,
            "data_path": data_paths,
            "mode": "custom_agent_execution",
        },
        causal_results=causal_from_workflow,
        custom_outputs=result if isinstance(result, dict) else {"raw_result": str(result)[:5000]},
        report_type="comprehensive",
    )
    print(f"  [Phase Final] 综合分析报告完成")

    return result


# ---------------------------------------------------------------------------
# Final Report Generation (shared across all modes)
# ---------------------------------------------------------------------------


def _generate_final_report(
    client: OpenAI,
    model: str,
    output_dir: str,
    intent_context: dict[str, Any],
    causal_results: dict[str, Any] | None,
    custom_outputs: dict[str, Any] | None,
    report_type: str,
    agent_group_name: str = "",
) -> str:
    """Unified report generation — the final step for all operating modes.

    Args:
        client: OpenAI-compatible client
        model: LLM model name
        output_dir: Output directory for report files
        intent_context: User intent, business goal, requirements
        causal_results: Causal inference pipeline results (None if not performed)
        custom_outputs: Custom agent outputs (None for Mode A)
        report_type: "causal" | "capability" | "comprehensive"
        agent_group_name: Custom agent group name (for scanning per-agent outputs)

    Returns:
        Report path or final message from the report-generator agent.
    """
    rg_prompt = load_agent_prompt("report-generator")
    rg_runner = AgentRunner(rg_prompt, client, model=model)

    # Scan per-agent output directories if available
    agent_outputs_context = ""
    agent_graph_dirs: list[str] = []
    if agent_group_name:
        from src.agent_framework import AgentOutputManager
        agent_output_base = ROOT / "custom" / agent_group_name / "output"
        if agent_output_base.exists():
            mgr = AgentOutputManager(agent_output_base)
            agent_outputs_context = mgr.format_context_for_agent()
            # Collect all graph directories
            for agent_dir in agent_output_base.iterdir():
                if agent_dir.is_dir():
                    for gd in agent_dir.rglob("graphs"):
                        if gd.is_dir():
                            agent_graph_dirs.append(str(gd))
                    causal_graphs = agent_dir / "causal"
                    if causal_graphs.exists():
                        for gd in causal_graphs.rglob("graphs"):
                            if gd.is_dir():
                                agent_graph_dirs.append(str(gd))

    parts = [
        "请生成一份**深度综合分析报告**。这是本次运行的唯一最终报告，应综合所有分析阶段的结果，详尽深入。",
        f"报告类型: {report_type}",
        "",
        "**报告撰写要求**:",
        "- **面向企业决策层**：语言通俗易懂，避免过多统计学术语，用业务语言解读分析结果",
        "- **图文并茂**：尽可能多的引用图表，每张图表配以通俗解释说明其业务含义",
        "- **内容丰富详实**：综合所有智能体的分析发现，形成完整的业务洞察链条",
        "- **结构清晰**：从业务背景→核心发现→分维度详析→管理建议，层层递进",
        "- 包含所有因果推断发现、数据洞察、业务解读和管理建议",
        "- 交叉引用不同分析阶段的结果，形成完整的分析逻辑链路",
        "- 报告语言为中文，面向企业管理者（非技术人员）",
    ]

    # Include per-agent output summaries for the report agent to read
    if agent_outputs_context:
        parts.append(f"\n## 任务导向型智能体分析产出清单\n{agent_outputs_context}")
        parts.append("\n请使用 file_read 工具读取上述清单中与你撰写报告相关的文件，综合所有信息撰写报告。")

    if agent_graph_dirs:
        parts.append(f"\n## 图表目录（所有智能体生成的图表）")
        for gd in agent_graph_dirs[:10]:
            parts.append(f"  - {gd}")

    parts.append(f"\n## 用户意图与背景\n{json.dumps(intent_context, ensure_ascii=False, indent=2)}")

    if causal_results:
        parts.append(f"\n## 因果推断结果\n{json.dumps(causal_results, ensure_ascii=False, indent=2, default=str)[:12000]}")
    else:
        parts.append("\n## 因果推断结果\n(本次无因果推断分析)")

    if custom_outputs:
        parts.append(f"\n## 工作流各步骤的详细产出\n{json.dumps(custom_outputs, ensure_ascii=False, indent=2, default=str)[:12000]}")
    else:
        parts.append("\n## 工作流产出\n(本次无自定义Agent产出)")

    parts.append(f"\n输出目录: {output_dir}")
    parts.append("\n请现在开始撰写Word报告，使用 python_exec 工具调用 src.report.generate_report 生成 .docx 文件。")

    rg_message = "\n\n".join(parts)
    return rg_runner.run(rg_message)


# ---------------------------------------------------------------------------
# Clean up custom agent
# ---------------------------------------------------------------------------


def run_clean_agent(agent_name: str) -> None:
    """Remove a custom agent group."""
    from src.custom_agent import CustomAgentManager

    manager = CustomAgentManager()
    manager.delete_agent_group(agent_name)


def run_list_agents() -> None:
    """List all custom agent groups."""
    from src.custom_agent import CustomAgentManager

    manager = CustomAgentManager()
    groups = manager.list_agent_groups()
    if groups:
        print(f"已创建的自定义Agent组 ({len(groups)}个):")
        for g in groups:
            group_path = manager.get_agent_group_path(g)
            def_file = group_path / "definition.txt"
            preview = ""
            if def_file.exists():
                text = def_file.read_text(encoding="utf-8")
                preview = text[:80].replace("\n", " ") + ("..." if len(text) > 80 else "")
            print(f"  - {g}")
            if preview:
                print(f"    {preview}")
    else:
        print("尚未创建任何自定义Agent组。")
        print(f"创建方式: python casual-analysis.py --create-agent \"需求描述\"")
        print(f"          python casual-analysis.py --agent-file <需求文件>")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()

    config = load_config(args.config)
    llm_cfg = config.get("llm", {})
    api_key = llm_cfg.get("api_key", "") or os.environ.get("DEEPSEEK_API_KEY", "")
    model = args.model or llm_cfg.get("model", "deepseek-v4-pro")

    if not api_key:
        print("警告: 未设置LLM API Key。请在 config.yaml 的 llm.api_key 中配置。")

    client = OpenAI(
        api_key=api_key or "sk-placeholder",
        base_url=llm_cfg.get("base_url", "https://api.deepseek.com"),
    )

    # Determine operating mode
    if args.list_agents:
        run_list_agents()
        return

    if args.clean_agent:
        run_clean_agent(args.clean_agent)
        return

    if args.create_agent or args.agent_file:
        # --- Mode B: Custom agent creation ---
        if args.create_agent:
            requirements = args.create_agent
        else:
            agent_file_path = Path(args.agent_file)
            if not agent_file_path.exists():
                print(f"错误: 需求文件不存在: {args.agent_file}")
                sys.exit(1)
            requirements = agent_file_path.read_text(encoding="utf-8")

        agent_name = run_custom_agent_creation_pipeline(
            requirements_text=requirements,
            client=client,
            model=model,
            agent_name=args.name,
            data_paths=args.data,
            prompt=args.prompt,
            output_dir=args.output,
        )
        print(f"\n创建完成! Agent组名称: {agent_name}")

    elif args.run_agent:
        # --- Mode C: Run custom agent ---
        if not args.data:
            print("错误: --run-agent 需要配合 --data 指定数据文件。")
            sys.exit(1)

        run_custom_agent_execution(
            agent_name=args.run_agent,
            data_paths=args.data,
            prompt=args.prompt or "",
            client=client,
            model=model,
            output_dir=args.output,
        )

    elif args.data and args.prompt:
        # --- Mode A: Direct causal analysis ---
        run_direct_analysis_pipeline(args)

    else:
        print("错误: 请指定运行模式。")
        print("  模式A (直接分析):     --data <文件...> --prompt <目标>")
        print("  模式B (创建+分析):    --agent-file <文件> --data <文件...> --prompt <目标>")
        print("  模式B (仅创建):       --agent-file <文件>")
        print("  模式C (运行已有Agent): --run-agent <名称> --data <文件...> --prompt <目标>")
        print("  支持多文件、通配符(*.csv)和目录")
        print("  查看Agent:           --list-agents")
        print("  清除Agent:           --clean-agent <名称>")
        sys.exit(1)


if __name__ == "__main__":
    main()
