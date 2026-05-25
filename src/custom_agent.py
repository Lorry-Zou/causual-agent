"""
Custom Agent Management — lifecycle management for user-defined task-oriented agents.

Provides:
  - CustomAgentManager: CRUD operations for custom agent groups
  - KnowledgeCollector: necessity judgment and knowledge gathering utilities
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

# Project root
ROOT = Path(__file__).parent.parent
DEFAULT_CUSTOM_DIR = ROOT / "custom"


class CustomAgentManager:
    """Manage the lifecycle of custom agent groups (Layer 3).

    Each agent group is stored in custom/<group_name>/ with:
      - definition.txt      Original user requirements
      - task_plan.json      Coordinator agent's decomposition output
      - agents/             Generated agent prompt .md files
      - knowledge/          Collected/generated knowledge bases
      - skills/             Generated SKILL.md files
      - workflow.py         Generated orchestration code
    """

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        self.storage_dir = Path(storage_dir) if storage_dir else DEFAULT_CUSTOM_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Directory structure
    # ------------------------------------------------------------------

    def get_agent_group_path(self, name: str) -> Path:
        return self.storage_dir / name

    def create_agent_group(self, name: str, definition_text: str) -> Path:
        """Initialize a new agent group directory with the user's requirements."""
        group_path = self.storage_dir / name
        # Create full directory structure
        for subdir in ["agents", "knowledge/uploaded", "knowledge/collected", "skills"]:
            (group_path / subdir).mkdir(parents=True, exist_ok=True)

        # Save original definition
        (group_path / "definition.txt").write_text(definition_text, encoding="utf-8")
        return group_path

    # ------------------------------------------------------------------
    # Save operations
    # ------------------------------------------------------------------

    def save_task_plan(self, group_name: str, plan: dict[str, Any]) -> Path:
        """Save the coordinator's task plan JSON."""
        plan_path = self.storage_dir / group_name / "task_plan.json"
        plan_path.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return plan_path

    def save_agent_prompt(self, group_name: str, agent_name: str, content: str) -> Path:
        """Save a generated agent prompt."""
        prompt_path = self.storage_dir / group_name / "agents" / f"{agent_name}.md"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(content, encoding="utf-8")
        return prompt_path

    def save_knowledge(self, group_name: str, name: str, content: str,
                       *, collected: bool = True) -> Path:
        """Save a knowledge document (collected or uploaded)."""
        sub = "collected" if collected else "uploaded"
        kpath = self.storage_dir / group_name / "knowledge" / sub / name
        kpath.parent.mkdir(parents=True, exist_ok=True)
        kpath.write_text(content, encoding="utf-8")
        return kpath

    def save_skill(self, group_name: str, skill_name: str, content: str) -> Path:
        """Save a SKILL.md file."""
        skill_path = self.storage_dir / group_name / "skills" / skill_name / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(content, encoding="utf-8")
        return skill_path

    def save_workflow(self, group_name: str, code: str) -> Path:
        """Save the generated workflow.py."""
        wf_path = self.storage_dir / group_name / "workflow.py"
        wf_path.write_text(code, encoding="utf-8")
        return wf_path

    # ------------------------------------------------------------------
    # File copy
    # ------------------------------------------------------------------

    def copy_uploaded_file(self, group_name: str, file_path: str | Path) -> Path:
        """Copy a user-uploaded file into the group's knowledge/uploaded/ directory."""
        src = Path(file_path)
        dst = self.storage_dir / group_name / "knowledge" / "uploaded" / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return dst

    # ------------------------------------------------------------------
    # Load operations
    # ------------------------------------------------------------------

    def load_agent_group(self, name: str) -> dict[str, Any]:
        """Load all data for an agent group."""
        group_path = self.storage_dir / name
        if not group_path.exists():
            raise FileNotFoundError(f"Agent group not found: {name}")

        info: dict[str, Any] = {"name": name, "path": str(group_path)}

        definition_file = group_path / "definition.txt"
        if definition_file.exists():
            info["definition"] = definition_file.read_text(encoding="utf-8")

        plan_file = group_path / "task_plan.json"
        if plan_file.exists():
            info["task_plan"] = json.loads(plan_file.read_text(encoding="utf-8"))

        agents_dir = group_path / "agents"
        if agents_dir.exists():
            info["agents"] = {
                f.stem: f.read_text(encoding="utf-8")
                for f in agents_dir.glob("*.md")
            }

        return info

    def list_agent_groups(self) -> list[str]:
        """List all custom agent group names."""
        if not self.storage_dir.exists():
            return []
        return sorted(
            d.name for d in self.storage_dir.iterdir()
            if d.is_dir() and (d / "definition.txt").exists()
        )

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_agent_group(self, name: str) -> bool:
        """Remove an entire agent group. Returns True if successful."""
        group_path = self.storage_dir / name
        if not group_path.exists():
            print(f"Agent组 '{name}' 不存在。")
            return False
        shutil.rmtree(group_path)
        print(f"Agent组 '{name}' 已清除。")
        return True

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def run_agent_group(
        self,
        name: str,
        data_path: str,
        client: Any,
        model: str = "deepseek-v4-pro",
        output_dir: str = "./output",
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """Load and execute a custom agent group's workflow."""
        from src.agent_framework import AgentRunner, CausalInferencePipeline

        group_path = self.storage_dir / name
        workflow_path = group_path / "workflow.py"

        if not workflow_path.exists():
            raise FileNotFoundError(
                f"Workflow file not found: {workflow_path}. "
                "The agent group was created but its workflow was not generated."
            )

        namespace: dict[str, Any] = {}
        workflow_code = workflow_path.read_text(encoding="utf-8")
        exec(workflow_code, namespace)

        if "run_workflow" in namespace:
            result = namespace["run_workflow"](
                data_path=data_path, prompt=prompt,
                client=client, model=model, output_dir=output_dir,
            )
        elif "WorkflowRunner" in namespace:
            runner = namespace["WorkflowRunner"]()
            result = runner.run(
                data_path=data_path, prompt=prompt,
                client=client, model=model, output_dir=output_dir,
            )
        else:
            raise RuntimeError(
                "workflow.py must define either 'run_workflow' function "
                "or 'WorkflowRunner' class."
            )

        return result


class KnowledgeCollector:
    """Judge knowledge necessity and collect knowledge from various sources.

    Used by the Knowledge Matcher Agent to:
    1. Judge whether a knowledge item is truly necessary
    2. Search open-source channels for relevant resources
    3. Generate knowledge artifacts when external sources are unavailable
    4. Compile request lists for the user when all else fails
    """

    @staticmethod
    def judge_necessity(agent_role: str, agent_responsibilities: list[str],
                        knowledge_topic: str, knowledge_description: str) -> str:
        """
        Return one of: "critical", "helpful", "optional"

        This is a heuristic — the actual judgment is made by the LLM-based
        knowledge-matcher agent. This function provides the structural interface.
        """
        # The actual necessity judgment is performed by the LLM agent.
        # This function serves as a hook for future programmatic checks.
        return "helpful"  # Default; LLM agent overrides

    @staticmethod
    def compile_request_list(missing_items: list[dict[str, Any]]) -> str:
        """Compile a human-readable list of knowledge items to request from the user.

        Args:
            missing_items: List of dicts with keys:
                - agent_name: Which agent needs this
                - topic: Knowledge topic
                - reason: Why it's necessary
                - suggested_source: Where the user might find it

        Returns:
            Formatted markdown string for the user.
        """
        lines = [
            "# 知识索取清单",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "以下知识对Agent的正常运行至关重要，但无法从公开渠道获取。请提供相关资料。",
            "",
        ]

        for i, item in enumerate(missing_items, 1):
            lines.append(f"## {i}. {item.get('topic', '未知主题')}")
            lines.append(f"- **需求Agent**: {item.get('agent_name', '未知')}")
            lines.append(f"- **必要性**: {item.get('reason', '未说明')}")
            if item.get("suggested_source"):
                lines.append(f"- **建议来源**: {item['suggested_source']}")
            if item.get("format"):
                lines.append(f"- **建议格式**: {item['format']}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def generate_skill_md(topic: str, content: str, tags: list[str] | None = None) -> str:
        """Generate a SKILL.md string with proper frontmatter.

        Args:
            topic: Skill name (slug)
            content: Markdown body content
            tags: Optional list of tags

        Returns:
            Complete SKILL.md content string.
        """
        tags_yaml = "\n  - ".join(tags or [topic])
        return f"""---
name: {topic}
description: Auto-generated skill for {topic}
workflow_stage: analysis
compatibility:
  - claude-code
author: AI-Generated (Knowledge Matcher Agent)
version: 1.0.0
tags:
  - {tags_yaml}
---

{content}
"""
