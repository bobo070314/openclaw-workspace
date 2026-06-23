#!/usr/bin/env python3.
"""V3.0 Agent Registry — Specialized agent definitions with skill allowlists.

Each agent has:
- name: unique identifier
- skills: allowed skill list (whitelist)
- system_prompt: role description for LLM routing
"""

from typing import Dict


class Agent:
    def __init__(self, name: str, skills: list[str], system_prompt: str, icon: str = "🤖"):
        self.name = name
        self.skills = skills
        self.system_prompt = system_prompt
        self.icon = icon


AGENT_REGISTRY: Dict[str, Agent] = {
    "sec-agent": Agent(
        name="sec-agent",
        icon="🛡️",
        skills=[
            "security-audit",
            "frontend-code-review",
            "backend-code-review",
            "add-setting-env",
        ],
        system_prompt="你是安全专家 Agent，负责代码安全审计、漏洞检测、环境变量审查。先审计再允许部署。",
    ),
    "code-agent": Agent(
        name="code-agent",
        icon="💻",
        skills=[
            "code-navigator",
            "db-migrations",
            "drizzle",
            "create-pr",
            "create-issue",
            "clone-project",
        ],
        system_prompt="你是全栈开发 Agent，负责代码导航、数据库操作、PR 和 Issue 管理。",
    ),
    "ops-agent": Agent(
        name="ops-agent",
        icon="🚀",
        skills=[
            "deployment-automation",
            "web-deploy-github",
            "github-actions-generator",
            "infra-diagram-as-code",
            "sandbox-executor",
        ],
        system_prompt="你是运维部署 Agent，负责 CI/CD、GitHub Pages、基础设施图表、容器化部署。",
    ),
    "doc-agent": Agent(
        name="doc-agent",
        icon="📝",
        skills=[
            "release-notes-generator",
            "notion",
            "linear",
            "tencent-docs",
            "wecomcli-msg",
            "wecomcli-contact",
            "wecomcli-doc",
            "wecomcli-meeting",
            "wecomcli-schedule",
            "wecomcli-todo",
            "api-doc-generator",
        ],
        system_prompt="你是文档协作 Agent，负责 Release Notes、Notion/Linear/腾讯文档/企微等协作工具。",
    ),
    "qa-agent": Agent(
        name="qa-agent",
        icon="🧪",
        skills=["agent-testing", "evaluator", "sql-optimizer"],
        system_prompt="你是质量保障 Agent，负责自动化测试、技能评测、SQL 优化。",
    ),
}


def get_agent_for_skill(skill_name: str) -> str | None:
    """Return the agent name that owns a given skill."""
    for name, agent in AGENT_REGISTRY.items():
        if skill_name in agent.skills:
            return name
    return None


def get_skills_for_agent(agent_name: str) -> list[str]:
    """Return allowed skills for an agent."""
    agent = AGENT_REGISTRY.get(agent_name)
    return agent.skills if agent else []


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------
def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="V3.0 Agent Registry")
    parser.add_argument("--list", action="store_true", help="List all agents")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--skill", help="Find agent for a skill")
    args = parser.parse_args()

    if args.skill:
        agent = get_agent_for_skill(args.skill)
        print(f"{args.skill} → {agent or 'unassigned'}")

    elif args.list:
        if args.json:
            data = {
                name: {"icon": a.icon, "skills": a.skills, "prompt": a.system_prompt}
                for name, a in AGENT_REGISTRY.items()
            }
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            for name, a in AGENT_REGISTRY.items():
                print(f"\n{a.icon} {name} ({len(a.skills)} skills)")
                print(f"   {a.system_prompt}")
                print(f"   Skills: {', '.join(a.skills[:5])}{'...' if len(a.skills) > 5 else ''}")


if __name__ == "__main__":
    main()
