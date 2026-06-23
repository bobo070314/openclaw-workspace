#!/usr/bin/env python3.
"""V3.0 Planner — LLM-driven task decomposition engine.

Usage:
  python planner.py "deploy app and ensure security"
  python planner.py --json --model deepseek "audit codebase"
  python planner.py --keyword-only "deploy and audit"    # no API key needed
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Step:
    action: str
    params: dict
    depends_on: List[str] = field(default_factory=list)
    description: str = ""


class Planner:
    """Natural language → Step DAG (LLM primary, keyword fallback)."""

    # ----------------------------------------------------------------
    # 148-skill inventory (auto-discovered at init)
    # ----------------------------------------------------------------
    SKILL_INVENTORY: List[str] = []

    # Keyword matrix (used when LLM is unavailable)
    KEYWORD_MAP: Dict[str, List[str]] = {
        "security": ["security-audit"],
        "audit": ["security-audit"],
        "deploy": ["deployment-automation", "web-deploy-github"],
        "review": ["frontend-code-review", "backend-code-review"],
        "code": ["code-navigator"],
        "pr": ["create-pr"],
        "issue": ["create-issue"],
        "note": ["release-notes-generator"],
        "migrate": ["db-migrations"],
        "drizzle": ["drizzle"],
        "diagram": ["infra-diagram-as-code"],
        "test": ["agent-testing"],
        "clone": ["clone-project"],
        "env": ["add-setting-env"],
        "release": ["release-notes-generator", "github-actions-generator"],
        "api": ["api-doc-generator"],
        "sql": ["sql-optimizer"],
        "安全": ["security-audit"],
        "审计": ["security-audit"],
        "部署": ["deployment-automation", "web-deploy-github"],
        "审查": ["frontend-code-review", "backend-code-review"],
        "拉取": ["create-pr"],
        "问题": ["create-issue"],
        "发布": ["release-notes-generator", "github-actions-generator"],
        "迁移": ["db-migrations"],
        "图表": ["infra-diagram-as-code"],
        "测试": ["agent-testing"],
        "克隆": ["clone-project"],
        "环境": ["add-setting-env"],
        "文档": ["api-doc-generator"],
        "优化": ["sql-optimizer"],
    }

    DEPENDENCIES: Dict[str, List[str]] = {
        "deployment-automation": ["security-audit"],
        "create-pr": ["frontend-code-review"],
        "web-deploy-github": ["deployment-automation"],
        "release-notes-generator": ["frontend-code-review", "backend-code-review"],
    }

    # ----------------------------------------------------------------
    # LLM config
    # ----------------------------------------------------------------
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("OPENCLW_PLANNER_MODEL", "deepseek/deepseek-chat")
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
        # Build inventory
        self._build_inventory()

    def _build_inventory(self):
        from pathlib import Path

        skills_dir = Path(r"D:\bobo\openclaw-foreign\skills")
        if skills_dir.exists():
            self.SKILL_INVENTORY = sorted(
                d.name
                for d in skills_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".") and (d / "run.py").exists()
            )

    def _llm_plan(self, goal: str) -> List[Step]:
        """Ask LLM to decompose goal into a step DAG."""
        if not self.api_key:
            return []

        skills = (
            self.SKILL_INVENTORY if self.SKILL_INVENTORY else list({s for v in self.KEYWORD_MAP.values() for s in v})
        )

        prompt = f"""You are a task planner. Decompose the goal into executable steps.

Available skills (use ONLY these names):
{", ".join(skills)}

Goal: {goal}

Return ONLY a JSON array. Each element:
{{
  "action": "skill-name",
  "params": {{"key": "value"}},
  "depends_on": ["action-name-of-dependency"],
  "description": "why this step"
}}

Rules:
- security-audit before any deploy step
- frontend-code-review before create-pr
- Do NOT invent skill names; use ONLY the available list
- Order steps logically (audit first, deploy last)
- Return ONLY the JSON array, no markdown, no explanation"""

        try:
            import requests  # avoid hard openai dep

            resp = requests.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 2000,
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

            # Extract JSON array
            start = content.find("[")
            end = content.rfind("]") + 1
            if start != -1 and end > start:
                raw_steps = json.loads(content[start:end])
                return [
                    Step(
                        action=s["action"],
                        params=s.get("params", {}),
                        depends_on=s.get("depends_on", []),
                        description=s.get("description", ""),
                    )
                    for s in raw_steps
                ]
        except Exception as e:
            print(f"[Planner] LLM failed ({e}), falling back to keyword", file=sys.stderr)

        return []

    def _keyword_plan(self, goal: str) -> List[Step]:
        """Keyword-based fallback planner."""
        goal_lower = goal.lower()
        matched = []

        for keyword, skills in self.KEYWORD_MAP.items():
            if keyword.lower() in goal_lower:
                for sk in skills:
                    if sk not in matched:
                        matched.append(sk)

        if not matched:
            return [
                Step(action="deployment-automation", params={}, description="Fallback: deploy"),
                Step(
                    action="security-audit",
                    params={"target": "."},
                    depends_on=["deployment-automation"],
                    description="Fallback: audit after deploy",
                ),
            ]

        steps = []
        for skill in matched:
            deps = self.DEPENDENCIES.get(skill, [])
            steps.append(Step(action=skill, params={}, depends_on=deps, description=f"Keyword: {skill}"))

        # Deduplicate dependencies
        for s in steps:
            s.depends_on = [d for d in s.depends_on if d in {x.action for x in steps}]

        return steps

    def plan(self, goal: str) -> List[Step]:
        """Plan: try LLM, fall back to keywords."""
        if self.api_key:
            llm_steps = self._llm_plan(goal)
            if llm_steps:
                return llm_steps
        return self._keyword_plan(goal)

    def to_dict(self, steps: List[Step]) -> List[dict]:
        return [
            {
                "action": s.action,
                "params": s.params,
                "depends_on": s.depends_on,
                "description": s.description,
            }
            for s in steps
        ]


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="V3.0 Planner — LLM task decomposition")
    parser.add_argument("goal", nargs="?", default="deploy app and ensure security", help="User goal")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--model", help="LLM model override")
    parser.add_argument("--keyword-only", action="store_true", help="Skip LLM, keyword only")
    parser.add_argument("--list-skills", action="store_true", help="Show known skills")
    args = parser.parse_args()

    p = Planner(model=args.model)

    if args.list_skills:
        skills = p.SKILL_INVENTORY or sorted({s for v in p.KEYWORD_MAP.values() for s in v})
        print(f"{len(skills)} skills:\n  " + "\n  ".join(skills))
        return 0

    if args.keyword_only:
        p.api_key = None  # force keyword fallback

    steps = p.plan(args.goal)

    output = {
        "goal": args.goal,
        "planner": "LLM" if (p.api_key and not args.keyword_only) else "keyword",
        "step_count": len(steps),
        "steps": p.to_dict(steps),
    }

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"Goal: {args.goal}  ({output['planner']})")
        print(f"Steps: {len(steps)}")
        for i, s in enumerate(steps, 1):
            deps = f" ← depends: {', '.join(s.depends_on)}" if s.depends_on else ""
            print(f"  {i}. {s.action}{deps}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
