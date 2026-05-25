#!/usr/bin/env python3
"""One-shot migration: organize data/ files into per-agent output/ directories.

Maps existing files from functional subdirectories under data/ to the
corresponding agent output directories under output/, generating detailed
summary.json manifests.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

GROUP_DIR = Path(__file__).parent
DATA_DIR = GROUP_DIR / "data"
OUTPUT_DIR = GROUP_DIR / "output"

# Mapping: (subdir_pattern, agent_name, description_template)
MIGRATION_MAP = [
    ("profiles", "user_profiling", "客户画像JSON"),
    ("reports", "coverage_gap_diagnosis", "保障缺口诊断报告JSON"),
    ("policies", "policy_lifecycle", "保单状态数据"),
    ("events", "policy_lifecycle", "保单事件/预警数据"),
    ("recovery", "policy_lifecycle", "流失召回/恢复策略数据"),
    ("causal_inputs", "coverage_gap_diagnosis", "因果推断输入数据"),
    ("causal_outputs/churn_attribution", "policy_lifecycle", "流失归因因果分析"),
    ("causal_outputs/gap_calibration", "coverage_gap_diagnosis", "缺口校准因果分析"),
]


def auto_describe(filepath: Path) -> str:
    """Generate a detailed auto-description of a file."""
    suffix = filepath.suffix.lower()
    size_kb = filepath.stat().st_size / 1024
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

    parts = [f"文件大小: {size_kb:.1f}KB", f"修改时间: {mtime}"]

    try:
        if suffix == ".csv":
            import pandas as pd
            df = pd.read_csv(filepath, nrows=5)
            full = pd.read_csv(filepath)
            parts.append(f"行数: {len(full)}, 列数: {len(full.columns)}")
            parts.append(f"列名: {', '.join(full.columns[:15])}")
            if len(full.columns) > 15:
                parts.append(f"... 共{len(full.columns)}列")
        elif suffix == ".json":
            content = json.loads(filepath.read_text(encoding="utf-8"))
            if isinstance(content, list):
                parts.append(f"JSON数组, 记录数: {len(content)}")
                if content and isinstance(content[0], dict):
                    parts.append(f"字段: {', '.join(list(content[0].keys())[:10])}")
            elif isinstance(content, dict):
                parts.append(f"JSON对象, 顶层键: {', '.join(list(content.keys())[:10])}")
                if len(content) > 10:
                    parts.append(f"... 共{len(content)}个键")
            else:
                parts.append(f"JSON, 类型: {type(content).__name__}")
        elif suffix == ".md":
            text = filepath.read_text(encoding="utf-8")
            parts.append(f"Markdown, 长度: {len(text)}字符")
            first_line = text.strip().split("\n")[0][:80]
            parts.append(f"首行: {first_line}")
        elif suffix in (".png", ".jpg", ".jpeg"):
            parts.append(f"图片文件")
        else:
            parts.append(f"类型: {suffix}")
    except Exception:
        parts.append("(无法自动分析内容)")

    return " | ".join(parts)


def migrate():
    """Copy files from data/ to output/ organized by agent, with summary.json."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_files = 0
    agent_summaries: dict[str, dict[str, str]] = {}

    for subdir, agent_name, desc_template in MIGRATION_MAP:
        src_dir = DATA_DIR / subdir
        if not src_dir.exists():
            print(f"  [跳过] {subdir} (目录不存在)")
            continue

        dest_dir = OUTPUT_DIR / agent_name
        # Handle nested causal outputs
        if "causal_outputs" in subdir:
            trigger = subdir.split("/")[-1]
            dest_dir = OUTPUT_DIR / agent_name / "causal" / trigger
        dest_dir.mkdir(parents=True, exist_ok=True)

        if agent_name not in agent_summaries:
            # Load existing summary if any
            existing = OUTPUT_DIR / agent_name / "summary.json"
            if existing.exists():
                try:
                    agent_summaries[agent_name] = json.loads(existing.read_text(encoding="utf-8"))
                except Exception:
                    agent_summaries[agent_name] = {}
            else:
                agent_summaries[agent_name] = {}

        for src_file in sorted(src_dir.rglob("*")):
            if src_file.is_dir():
                continue
            # Determine relative path within dest
            rel = src_file.relative_to(src_dir)
            dest_file = dest_dir / rel.name
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy (not move)
            shutil.copy2(src_file, dest_file)

            # Generate description
            auto_desc = auto_describe(src_file)
            description = f"{desc_template} — {auto_desc}"

            # Use relative path as key
            key = str(rel.name) if rel.parent == Path(".") else str(rel)
            agent_summaries[agent_name][key] = description
            total_files += 1
            print(f"  {key} -> {agent_name}/{key}")

    # Write summary.json for each agent
    for agent_name, files in agent_summaries.items():
        summary_path = OUTPUT_DIR / agent_name / "summary.json"
        summary_path.write_text(
            json.dumps(files, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n  summary.json -> {agent_name}/ ({len(files)} files)")

    print(f"\n迁移完成: {total_files} 个文件 -> {OUTPUT_DIR}")
    print(f"原始数据保留在 {DATA_DIR} (未删除)")


if __name__ == "__main__":
    migrate()
