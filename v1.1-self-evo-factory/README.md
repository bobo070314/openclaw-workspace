# V1.1 自进化 AI 工厂

## 目标

不依赖外部 API Key 的 self-coder 闭合回路：**写代码 → 评测 → 进化 → 再评测 → 落盘**

## 核心闭环

```
┌─────────────────────────────────────────────────┐
│                  V1.1 Pipeline                    │
│                                                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │  WRITE    │───▶│  EVAL    │───▶│ IMPROVE  │   │
│  │ (规则引擎) │    │ (测试套)  │    │ (自动修)  │   │
│  └──────────┘    └──────────┘    └──────────┘   │
│        │               │              │           │
│        └───────────────┴──────────────┘           │
│                        │                          │
│                   ┌────▼────┐                     │
│                   │  COMMIT  │                     │
│                   └─────────┘                     │
└─────────────────────────────────────────────────┘
```

## 阶段规划

### Phase 1: 核心骨架（当前）
- [ ] self-coder 规则引擎复活并落盘
- [ ] eval-suite 基础测试框架
- [ ] 状态持久化（states/*.json）
- [ ] 首次 Git 提交

### Phase 2: 自进化
- [ ] self_improve.py 闭环脚本
- [ ] 自动修复 → 再评测 → keep/rollback
- [ ] 健康检查（V∞ HEALTH）

### Phase 3: 扩展
- [ ] 多技能覆盖（security-audit, db-migrations, etc.）
- [ ] token-saver 集成
- [ ] Docker 沙箱隔离

## 目录结构

```
v1.1-self-evo-factory/
├── README.md           ← 你在这
├── pipeline/            ← 核心引擎
│   ├── self_coder.py   ← 规则引擎
│   └── self_improve.py ← 闭环改进
├── eval-suite/          ← 评测框架
│   ├── run_all.py      ← 批量运行
│   └── test_*.py       ← 各技能测试
├── skills/              ← 目标技能（符号链接/引用）
├── states/              ← 持久化状态
└── logs/                ← 运行日志
```

## 技术决策

- **不开 API Key**：Phase 1 全规则引擎
- **Docker 隔离**：sandbox-executor 提供安全保证
- **Git 提交**：每个改进点一个 commit
- **状态文件**：JSON 持久化，可审计
