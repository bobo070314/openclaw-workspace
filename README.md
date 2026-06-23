# V1.1 Self-Evolving Factory

> 🔄 **V∞ 自进化技能工厂** — 规则引擎驱动 + LLM 闭环优化 + Git 版本追踪

[![GitHub repo](https://img.shields.io/badge/repo-bobo070314%2Fv1.1--self--evo--factory-blue)](https://github.com/bobo070314/v1.1-self-evo-factory)
[![Skills](https://img.shields.io/badge/skills-27_live-green)](https://github.com/bobo070314/v1.1-self-evo-factory/tree/master/skills)
[![Pipeline](https://img.shields.io/badge/pipeline-self--coder+self--improve-orange)](https://github.com/bobo070314/v1.1-self-evo-factory/tree/master/v1.1-self-evo-factory/pipeline)
[![Ruff](https://img.shields.io/badge/lint-ruff_0.15.18-purple)](https://github.com/astral-sh/ruff)
[![Pre-commit](https://img.shields.io/badge/hook-pre--commit-lightgrey)](https://pre-commit.com/)

---

## 📊 快照（2026-06-23）

| 维度 | 状态 |
|------|------|
| 技能目录总数 | **152** |
| Live 技能 (run.py) | **27** |
| Stub 技能 (SKILL.md) | **95** |
| 第三方源码目录 | **30**（Chart.js / docker / eslint / next.js 等） |
| 自进化闭环 | **27/27 ALL GREEN** |
| Ruff 质量 | **39 fixed, 29 doc-style** |
| Git commits | **10** |
| Cron 每日自愈 | **9:00 Asia/Shanghai** |

---

## 🧬 核心架构

```
v1.1-self-evo-factory/
├── pipeline/
│   ├── self_coder.py          # 9规则静态分析引擎（0错误/4假阳性）
│   ├── self_improve.py        # V2.10 @repair 闭环优化器
│   └── daily_eval_reporter.py # 每日自愈 cron 报告
├── skills/                    # 152个技能目录
│   ├── 12核心技能              # create-skill, agent-testing, db-migrations...
│   ├── 2基础设施               # token-saver, sandbox-executor
│   ├── 12高频桩                # react, typescript, zustand, i18n...
│   └── 95stub + 30bare        # 文档技能 + 第三方源码
├── eval-suite/                # 14个测试文件（100%通过率）
├── states/                    # 运行时状态快照（闭环历史）
└── scripts/                   # 批处理/安装脚本
```

## 🔧 技术栈

- **规则引擎**: Pure Python AST + Regex（无外部依赖）
- **代码质量**: Ruff 0.15.18 + Pre-commit hook
- **自愈框架**: self-heal 0.5.0 `@repair` 装饰器
- **Python 版本**: 3.11+
- **Git 仓库**: [bobo070314/v1.1-self-evo-factory](https://github.com/bobo070314/v1.1-self-evo-factory)

## 🚀 快速开始

```bash
# 克隆仓库
git clone git@github.com:bobo070314/v1.1-self-evo-factory.git
cd v1.1-self-evo-factory

# 安装 pre-commit hook
python .git/hooks/pre-commit.py

# 跑自进化闭环
python v1.1-self-evo-factory/pipeline/self_coder.py --rules path/to/file.py --json

# 全量质量扫描
python v1.1-self-evo-factory/pipeline/self_improve.py --all

# 安装 ruff
pip install ruff
python -m ruff check skills/ --fix
```

## 🤖 自进化闭环

```
scan(self_coder) → optimize(self_improve) → snapshot(json) → evaluate → KEEP or ROLLBACK
```

每次优化都会：
1. `self_coder --rules <file>` 扫描 9 条关键规则
2. `self_improve.py` 调用 `@repair` 装饰器自动修复
3. 状态快照存到 `states/improve_<skill>_<timestamp>.json`
4. 比较 pre/post-eval 决定保留或回滚

## 🛡️ 安全审计

`sandbox-executor` 提供 Docker 容器隔离：
- 只读文件系统（read-only root）
- 禁止提权（no-new-privileges）
- 全员能力放弃（cap-drop ALL）
- 默认关闭网络
- 内存限制 + 超时保护

## 📈 路线图

- [x] V1.1 规则引擎骨架
- [x] V1.2 自动闭环（self_improve.py）
- [x] V1.3-V1.4 token-saver + sandbox-executor
- [x] V2.0 12核心技能全部 live
- [x] V2.10 ruff + self-heal-llm + cron 上线
- [ ] V3.0 eval-suite 覆盖率 100%
- [ ] V3.1 notion/linear/wecom 外部 API 集成测试

---

<p align="center">
  <sub>Made with 🔥 by OpenClaw International Edition • ASCII art powered by V∞</sub>
</p>
