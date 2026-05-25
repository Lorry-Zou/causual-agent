# AI因果推断分析系统 (Causal Inference System)

基于AI Agent的企业数据因果推断分析系统。用户上传企业数据并输入中文业务目标，系统自动完成：**意图理解 → 数据清洗 → 模型选择 → 因果推断 → 结果呈现**，最终输出Word报告和管理建议。

系统同时支持**用户自定义Agent构建**：用户输入业务需求描述，系统自动分析、拆解任务，创建专属的协作Agent团队。

## 三层架构

系统采用**三层Agent协作架构**：

```
Layer 3: 任务导向层 (动态、临时)
  用户定义的Agent: 续保率Agent、营销Agent、定价Agent...
  存储位置: custom/{agent_group}/

Layer 2: 解析构建层
  协调Agent → 智能体创建Agent + 知识库匹配Agent + 工作流设定Agent
  根据用户需求自动构建Layer 3

Layer 1: 因果推断层
  数据处理Agent → 因果推断Agent → 报告撰写Agent
  提供核心因果分析能力
```

- **Layer 1**：提供数据到报告的完整因果推断能力，封装为 `CausalInferencePipeline` API供上层调用
- **Layer 2**：解读用户需求，拆解任务，自动创建Agent、匹配知识库、设定工作流
- **Layer 3**：针对具体业务场景临时生成的Agent，灵活可扩展，可调用Layer 1进行分析

## 目录结构

```
casual-agent/
├── casual-analysis.py          # 主入口 — 多模式CLI (直接分析/创建Agent/运行Agent)
├── config.yaml                 # 配置文件 (LLM, 数据处理, 模型参数, 自定义Agent)
├── requirements.txt            # Python依赖
├── README.md                   # 本文档
│
├── src/                        # Python函数库
│   ├── agent_framework.py      # 核心框架 — AgentRunner, 工具注册, CausalInferencePipeline
│   ├── custom_agent.py         # 自定义Agent管理 — CustomAgentManager, KnowledgeCollector
│   ├── utils.py                # 日志, LLM客户端, 配置, Prompt模板
│   ├── data_processing.py      # 数据加载/清洗/填充/异常值/类型推断/EDA（支持多文件）
│   ├── causal_models.py        # 7种因果推断方法 + 模型选择引擎
│   ├── visualization.py        # 学术级图表 (系数图/事件研究/Love plot)
│   ├── report.py               # Word中文报告生成 + LLM管理建议
│   └── test_data_generator.py  # 测试数据生成器 — 3大业务场景, 11张表, ~19万行数据
│
├── agents/                     # Agent定义 (Markdown, 每个Agent的角色和指令)
│   ├── coordinator.md          # [Layer 2] 协调Agent — 分析需求、拆解任务
│   ├── agent-creator.md        # [Layer 2] 智能体创建Agent — 生成Agent Prompt
│   ├── knowledge-matcher.md    # [Layer 2] 知识库匹配Agent — 必要性判断+知识匹配
│   ├── workflow-designer.md    # [Layer 2] 工作流设定Agent — 生成编排代码
│   ├── data-processing.md      # [Layer 1] 数据处理Agent — 加载清洗数据
│   ├── causal-inference.md     # [Layer 1] 因果推断Agent — 模型选择与执行
│   └── report-generator.md     # [Layer 1] 报告生成Agent — 结果呈现与管理建议
│
├── skills/                     # SKILL.md方法论参考 (Agent在执行任务时查阅)
│   ├── data-cleaning/SKILL.md       # 数据清洗
│   ├── panel-data/SKILL.md          # 面板回归 — FE/RE/Hausman检验
│   ├── iv-did-rdd/SKILL.md          # IV/DiD/RDD — 准实验方法
│   ├── psm/SKILL.md                 # PSM — 倾向得分匹配
│   ├── dml/SKILL.md                 # DML — 双机器学习
│   ├── dag-discovery/SKILL.md       # DAG发现 — PC/FCI/LiNGAM
│   └── visualization/SKILL.md       # 可视化
│
├── custom/                     # 自定义Agent存储 (Layer 3，与主代码隔离)
│   └── {agent_group_name}/
│       ├── definition.txt      # 用户原始需求
│       ├── task_plan.json      # 协调Agent的任务拆解
│       ├── agents/             # 生成的Agent prompt (.md)
│       ├── knowledge/          # 搜集/上传的知识库
│       │   ├── uploaded/       # 用户上传的资料
│       │   └── collected/      # 自动搜集/生成的知识
│       ├── skills/             # 自动生成的SKILL.md
│       └── workflow.py         # 生成的编排代码
│
├── examples/
│   ├── sample_data.csv              # 示例数据 (10企业×4年面板)
│   ├── example_prompts.md           # 7种业务场景Prompt示例
│   └── test_data/                   # 测试数据目录（空，由生成器填充）
│
├── tests/
│   └── test_all.py                  # 测试文件
│
├── RAG/                             # RAG知识库检索模块
│   ├── RAG.py                       # LangChain RAG实现
│   └── utd24_papers_all/            # UTD-24学术论文PDF
│
└── output/                     # 运行时输出
    ├── graphs/                 # EDA和模型图表
    ├── reports/                # 生成的Word报告
    ├── data/                   # 处理后的数据文件
    └── test_data/              # 测试数据生成器的输出（11张CSV表）
```

## 模块功能说明

### src/agent_framework.py — 核心框架

Agent运行的基础设施：
- **AgentRunner**：LLM agent运行器，管理system prompt、工具调用循环（最多50轮），实时输出思考过程
- **TOOLS**：6种工具注册表 — `shell_exec`, `file_read`, `file_write`, `python_exec`, `read_skill`, `run_causal_analysis`
- **CausalInferencePipeline**：封装Layer 1三阶段管线，提供 `run(data_paths, ...)` API。`data_paths` 支持单文件路径（`str`）或多文件列表（`list[str]`），自动处理glob通配符和目录展开，支持 `merge` 参数控制合并策略
- **parse_user_intent()**：从数据中提取列信息供LLM意图解析，多文件模式下返回文件数量及各文件字段元数据
- **AgentRegistry**：统一管理内置和自定义Agent定义

### src/custom_agent.py — 自定义Agent管理

- **CustomAgentManager**：管理自定义Agent组的完整生命周期（创建/保存/加载/删除/执行）
- **KnowledgeCollector**：判断知识必要性、搜索开源资源、生成SKILL.md、整理索取清单

### src/data_processing.py — 数据处理

数据加载器（CSV/Excel/JSON/Stata/Parquet，自动检测编码和分隔符）、类型推断（连续/分类/二值/日期）、缺失值处理（中位数/众数/MICE）、异常值处理（IQR/Z-score截尾）、统计信息采集和EDA可视化。

**多文件支持**（新增）：
- `DataLoader.load_multiple(paths, merge)` — 加载多个文件，支持四种合并策略：
  - `"auto"`：自动检测（相同schema→拼接 / 共享ID列→关联 / 无关联→分离）
  - `"concat"`：纵向拼接（`pd.concat`，对齐列）
  - `"merge"`：按共享ID列（如 `客户ID`、`保单ID`）关联合并
  - `"separate"`：保持独立，返回 `dict[str, DataFrame]`
- `DataLoader._resolve_paths(paths)` — 展开glob通配符和目录为具体文件列表
- `DataCleaner.run(data_input, merge)` — 支持单文件路径或多文件列表，对多文件分离模式逐表清洗

### src/causal_models.py — 因果模型

7种因果推断方法，每种包含 `fit() → estimate_ate() → diagnostics() → plot()` 完整工作流：

| 方法 | 适用场景 | 关键诊断 |
|------|---------|---------|
| **Panel Regression** | 面板数据（实体+时间） | Hausman检验 (FE vs RE) |
| **DiD** | 处理前后+处理/对照组 | 平行趋势检验 |
| **IV** | 存在工具变量 | 第一阶段F统计量 (>10) |
| **PSM** | 截面数据+二值处理 | SMD平衡性诊断 |
| **DML** | 大样本+多维混淆 | 交叉验证ATE |
| **RDD** | 明确断点/阈值 | McCrary密度检验 |
| **DAG Discovery** | 探索性分析 | PC/FCI/LiNGAM算法 |

`score_methods()` + `select_methods()` 自动模型选择引擎：基于数据特征自动评分推荐。

### src/visualization.py — 可视化

系数森林图、事件研究图、PSM平衡性Love Plot，支持中文标签。

### src/report.py — 报告生成

生成专业的Word (.docx) 中文报告。系统支持三种报告类型，由report-generator Agent根据运行模式自动适配：
- **causal**：标准因果推断报告（6章中覆盖4章）
- **capability**：系统能力报告（Agent架构、职责、实施路线图）
- **comprehensive**：综合分析报告（完整6章，两大部分：Agent系统设计 + 因果分析报告）

## 使用方法

### 方式一：直接使用（Windows 打包版，推荐）

无需安装 Python，下载解压即可运行。

**1. 下载并解压**

获取 `causal-agent-vX.X.X.zip`，解压到任意目录。

**2. 配置 API Key**

编辑解压目录中的 `config.yaml`，填入你的 DeepSeek API Key：

```yaml
llm:
  api_key: sk-your-api-key-here   # 替换为你的真实 Key
```

或者设置环境变量（二选一）：

```cmd
set DEEPSEEK_API_KEY=sk-your-api-key-here
```

**3. 运行分析**

打开命令行（cmd 或 PowerShell），进入解压目录：

```cmd
cd C:\path\to\causal-agent
causal-analysis --data 你的数据.csv --prompt "分析目标"
```

支持的功能与源码版完全一致（三种模式、多文件、通配符等），报告生成在 `output/reports/` 目录。

### 构建打包版（开发者）

如果需要自行构建 .exe：

```powershell
# 安装 PyInstaller
pip install pyinstaller

# 一键构建
powershell -ExecutionPolicy Bypass -File build_installer.ps1

# 输出: dist/causal-agent-v0.1.0.zip
```

### 方式二：源码运行（开发者）

**安装依赖：**

```bash
cd casual-agent
pip install -r requirements.txt
```

**配置 API Key：**

编辑 `config.yaml`，填入 API Key，或设置环境变量：

```bash
# Windows
set DEEPSEEK_API_KEY=sk-your-api-key-here
# Linux/Mac
export DEEPSEEK_API_KEY="sk-your-api-key"
```

`config.yaml` 中的 `${DEEPSEEK_API_KEY}` 会自动读取环境变量。

### CLI运行

系统支持三种运行模式。所有模式最终都生成Word (.docx) 分析报告。

#### 模式A：直接因果分析

对数据直接执行完整的因果推断分析（Phase 0→1→2→3），产出标准因果推断报告：

```bash
# 单文件（向后兼容）
python casual-analysis.py --data examples/sample_data.csv --prompt "分析营销支出对续保率的因果影响"

# 多文件 — 按共享ID列（如客户ID）自动关联合并
python casual-analysis.py --data output/test_data/客户画像表.csv output/test_data/保单主表.csv --prompt "分析客户保障情况"

# 通配符 — 加载目录下所有CSV
python casual-analysis.py --data "output/test_data/*.csv" --prompt "综合分析"

# 目录 — 加载目录内所有支持的文件
python casual-analysis.py --data output/test_data/ --prompt "分析续保率影响因素"

# 指定方法和输出目录
python casual-analysis.py --data data.csv --prompt "提高参保率" --method DID,PSM --output ./my_results
```

> **数据合并策略**：多文件时系统自动检测关系 — 表结构相同则纵向拼接，共享ID列则关联合并，完全不同的表则保持独立分析。

#### 模式B：创建自定义Agent + 分析

根据业务需求创建专属Agent团队，并可同步运行分析。最终产出**综合分析报告**（两大部分：Agent系统设计与功能 + 分析报告）：

```bash
# 完整流程：创建Agent + 运行分析 + 综合报告（支持多文件）
python casual-analysis.py --agent-file 个人非车险智能体.txt --data output/test_data/客户画像表.csv output/test_data/保单主表.csv --prompt "分析续保率影响因素"

# 使用通配符加载所有测试数据
python casual-analysis.py --agent-file 个人非车险智能体.txt --data "output/test_data/*.csv" --prompt "全面分析保险业务"

# 仅创建Agent（无数据时只生成系统能力报告）
python casual-analysis.py --agent-file 个人非车险智能体.txt

# 指定名称
python casual-analysis.py --create-agent "保险续保率提升智能体..." --name renewal-agent --data output/test_data/ --prompt "分析续保率"
```

创建流程（Phase 2-0 → 2-4）：
1. **协调Agent** 分析需求 → 输出结构化任务计划JSON
2. **智能体创建Agent** 为每个新Agent生成system prompt (.md文件)
3. **知识库匹配Agent** 判断各知识项必要性 → 搜索/生成/索取
4. **工作流设定Agent** 生成编排代码 (workflow.py)
5. 若有数据 → **运行创建的Agent工作流** → 产出综合分析报告
6. 若无数据 → 产出系统能力报告

所有生成内容存储在 `custom/{agent_name}/` 目录。

#### 模式C：运行已有Agent

加载已创建的Agent组并运行分析，产出与Mode B（有数据）相同的综合分析报告：

```bash
# 单文件运行
python casual-analysis.py --run-agent renewal-agent --data data.csv --prompt "分析Q3续保率下降原因"

# 多文件运行
python casual-analysis.py --run-agent renewal-agent --data output/test_data/客户画像表.csv output/test_data/保单主表.csv --prompt "综合分析"
```

#### 其他命令

```bash
# 查看已创建的Agent组
python casual-analysis.py --list-agents

# 清除指定Agent组
python casual-analysis.py --clean-agent renewal-agent
```

### 测试数据生成

系统内置了一个针对保险业务场景的测试数据生成器，可生成具有真实统计分布和相关性的模拟数据：

```bash
# 一键生成全部测试数据
python src/test_data_generator.py
```

生成 **11张CSV表，约19万行数据**，覆盖三大业务场景，输出到 `output/test_data/`：

| 场景 | 表名 | 行数 | 说明 |
|------|------|------|------|
| **保单全生命周期** | 客户画像表 | 5,000 | 人口统计、收入、活跃度、价值等级 |
| | 保单主表 | 10,000 | 9种产品类型、保单状态、保费/保额、理赔 |
| | 生命周期事件日志 | 50,000 | 26种事件类型、自动化动作、响应时间 |
| | 缴费记录表 | 50,000 | 缴费状态、失败原因、宽限期/复效追踪 |
| **保障缺口诊断** | 客户保障概况表 | 5,000 | 各险种保额、房贷/负债、社保、健康风险 |
| | 保障缺口诊断结果表 | 35,000 | 7大缺口维度、严重度评分、推荐方案 |
| | 缺口诊断日志表 | 10,000 | AI模型版本、置信度、诊断耗时、异常标记 |
| **智能咨询对话** | 对话会话表 | 3,000 | 10种意图、渠道、满意度、情绪趋势 |
| | 对话消息明细表 | 16,000 | 逐轮对话、AI置信度、RAG引用、合规过滤 |
| | 咨询结果追踪表 | 3,000 | 转化结果、NPS评分、成交金额 |
| | 常见问题知识库引用表 | 6,000 | 8类知识条目、检索方式、采纳率 |

**数据特点**：
- 所有金额字段使用对数正态分布，评分使用Beta分布，计数使用零膨胀Poisson分布
- 表间通过 `客户ID`、`保单ID` 等共享键关联，支持跨场景联合分析
- 包含大量边界案例（零保额、超龄客户、合规违规、低置信度诊断等）
- 固定随机种子（`SEED=42`），可复现
- 可直接配合多文件加载功能使用：
  ```bash
  # 加载全部测试数据进行综合分析
  python casual-analysis.py --data "output/test_data/*.csv" --prompt "分析保险业务全景"
  
  # 按场景选择子集
  python casual-analysis.py --data output/test_data/客户画像表.csv output/test_data/保单主表.csv --prompt "分析客户续保率影响因素"
  ```

### 报告类型

系统根据运行模式自动选择报告类型，均通过 `agents/report-generator.md` 生成Word文档：

| 报告类型 | 模式 | 内容 |
|---------|------|------|
| **causal** | Mode A | 标准因果推断报告（5章：意图分析→数据概况→模型选择→因果推断→管理建议） |
| **capability** | Mode B（无数据） | 系统能力报告（Agent架构、职责、工作流、实施路线图） |
| **comprehensive** | Mode B（有数据）/ Mode C | 综合分析报告（两大部分：Agent系统设计 + 基于因果分析+Agent产出的分析报告，6章完整） |

## Agent系统详解

### Agent Runner

每个Agent基于统一的 `AgentRunner` 运行：
1. 加载系统提示（定义角色和任务）
2. 可调用6种工具：`shell_exec`, `file_read`, `file_write`, `python_exec`, `read_skill`, `run_causal_analysis`
3. LLM决策 → 工具调用 → 结果反馈 → 继续/结束
4. 实时输出思考过程到控制台
5. 最多50轮循环

### Layer 1 Agent（因果推断层）

- **数据处理Agent** (`agents/data-processing.md`): 专注数据质量，查阅 `skills/data-cleaning/SKILL.md`
- **因果推断Agent** (`agents/causal-inference.md`): 计量经济学家角色，自动选择方法或根据用户指定执行
- **报告生成Agent** (`agents/report-generator.md`): 将统计结果转为中文商业报告

### Layer 2 Agent（解析构建层）

- **协调Agent** (`agents/coordinator.md`): 解读用户自定义Agent需求，输出结构化JSON（含agent清单、知识需求、工作流设计）
- **智能体创建Agent** (`agents/agent-creator.md`): 根据计划为每个新Agent编写完整的system prompt
- **知识库匹配Agent** (`agents/knowledge-matcher.md`): 先判断必要性，再按优先级（用户上传→搜索→生成→索取）匹配知识
- **工作流设定Agent** (`agents/workflow-designer.md`): 生成Python编排代码，实现Agent间协作

### Layer 3 Agent（任务导向层）

动态生成的Agent，存储在 `custom/` 目录。可以调用Layer 1的因果推断能力，通过 `run_causal_analysis` 工具或直接使用 `CausalInferencePipeline` API。

### SKILL.md 的作用

Agent通过 `read_skill("psm")` 工具查阅SKILL.md文件，获取方法适用条件、执行步骤、诊断标准和常见陷阱。

## 示例场景

| 行业 | Prompt | 推荐方法 |
|------|--------|---------|
| 保险 | "提高非车险用户的参保率" | PSM, DML |
| 电商 | "分析促销活动对复购率的因果影响" | DiD |
| HR | "评估培训对绩效的真实影响" | Panel Regression, PSM |
| 金融 | "量化利率下调对企业借贷行为的影响" | DiD, IV |
| 教育 | "分析重点大学对毕业生薪资的长期影响" | RDD |

更多示例见 [examples/example_prompts.md](examples/example_prompts.md)。

## 运行测试

```bash
python tests/test_all.py
```

## 依赖

| 类别 | 包 | 用途 |
|------|---|------|
| 核心 | pandas, numpy, scipy | 数据处理 |
| 统计 | statsmodels, scikit-learn | 回归、ML基础 |
| 因果（可选） | linearmodels | 面板/IV高效估计 |
| 因果（可选） | econml | 双机器学习 |
| 因果（可选） | causal-learn | DAG发现 |
| 可视化 | matplotlib, seaborn | 图表 |
| LLM | openai | DeepSeek/OpenAI API |
| 其他 | pyyaml, openpyxl | 配置、Excel |

## 参考项目

- [awesome-econ-ai-stuff](https://github.com/meleantonio/awesome-econ-ai-stuff) — 经济学AI技能集合
- [Causal-Copilot](https://github.com/Abel-Tool/Causal-Copilot) — 自主因果分析Agent
- [Anthropic Skills](https://github.com/anthropics/skills) — Claude Code技能规范
