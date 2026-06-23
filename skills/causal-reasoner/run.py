#!/usr/bin/env python3
"""causal-reasoner v0.2.0 — Causal DAG inference engine
=====================================================
Backtracks observed effects through a weighted Bayesian DAG
to identify root causes. Reads daemon state, writes reasoning logs.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

VERSION = "0.2.0"

# ── Causal DAG (adjacency: cause → [effects]) ──────────────────────────
CAUSAL_GRAPH = {
    "git_push": ["deploy"],
    "deploy": ["cpu_load", "memory_usage", "disk_usage"],
    "config_change": ["cpu_load", "memory_usage"],
    "high_traffic": ["cpu_load", "memory_usage", "disk_usage"],
    "disk_write": ["disk_usage"],
    "memory_leak": ["memory_usage"],
    "cron_job": ["cpu_load"],
    "build_process": ["cpu_load", "memory_usage"],
}

# ── Prior belief table (how likely each cause triggers each effect, 0-1)
PRIORS = {
    ("deploy", "cpu_load"): 0.90,
    ("deploy", "memory_usage"): 0.70,
    ("deploy", "disk_usage"): 0.50,
    ("git_push", "deploy"): 0.40,
    ("config_change", "cpu_load"): 0.30,
    ("config_change", "memory_usage"): 0.25,
    ("high_traffic", "cpu_load"): 0.95,
    ("high_traffic", "memory_usage"): 0.80,
    ("high_traffic", "disk_usage"): 0.60,
    ("disk_write", "disk_usage"): 0.95,
    ("memory_leak", "memory_usage"): 0.90,
    ("cron_job", "cpu_load"): 0.60,
    ("build_process", "cpu_load"): 0.85,
    ("build_process", "memory_usage"): 0.75,
}

# === AUTO-TUNED BY EVOLUTION ENGINE ===
# Last adjustment: never
AUTO_WEIGHTS = {
    "deploy": 0.9,
    "high_traffic": 0.5,
    "config_change": 0.7,
    "build_process": 0.6,
    "disk_write": 0.8,
    "memory_leak": 0.7,
    "git_push": 0.8,
    "cron_job": 0.4,
}
# === END AUTO-TUNE ===


def _get_weight(cause):
    """Get live weight from evolution engine, fall back to PRIORS."""
    try:
        return AUTO_WEIGHTS.get(cause, 0.5)
    except Exception:
        return 0.5


DECAY_FACTOR = 0.85  # confidence decays per hop back through the DAG


def _handle_std_flags():
    """Intercept --version / --json / --dry-run before argparse.
    Returns (exit_code, output_str) or None to continue.
    """
    args = sys.argv[1:]
    output = {}
    for i, a in enumerate(args):
        if a == "--version":
            output["version"] = VERSION
            if "--json" in args:
                print(json.dumps(output))
            else:
                print(f"causal-reasoner v{VERSION}")
            sys.exit(0)
        if a == "--dry-run":
            # --dry-run with --infer or --list-graph → print what would happen
            target = None
            try:
                ti = args.index("--infer")
                target = args[ti + 1]
            except (ValueError, IndexError):
                pass
            mode = "infer" if target else "list-graph" if "--list-graph" in args else "unknown"
            output = {
                "mode": "dry-run",
                "action": mode,
                "infer_target": target,
                "graph_nodes": len(CAUSAL_GRAPH),
                "priors_count": len(PRIORS),
                "decay_factor": DECAY_FACTOR,
            }
            if "--json" in args:
                print(json.dumps(output))
            else:
                print(f"[DRY-RUN] causal-reasoner v{VERSION} — would run: {mode} target={target or 'N/A'}")
            sys.exit(0)
    return None


def load_evidence(evidence_path=None):
    """Load evidence from daemon state file or environment."""
    evidence = {}
    if evidence_path and os.path.exists(evidence_path):
        try:
            with open(evidence_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            # Map daemon state keys to causal evidence
            if state.get("cpu_percent"):
                evidence["cpu_load"] = state["cpu_percent"]
            if state.get("memory_percent"):
                evidence["memory_usage"] = state["memory_percent"]
            if state.get("disk_percent"):
                evidence["disk_usage"] = state["disk_percent"]
            for key in [
                "deploy",
                "git_push",
                "config_change",
                "high_traffic",
                "disk_write",
                "memory_leak",
                "cron_job",
                "build_process",
            ]:
                if state.get(key):
                    evidence[key] = state[key]
        except (json.JSONDecodeError, OSError) as e:
            evidence["_load_error"] = str(e)

    # Fallback: check environment
    for key in ["deploy", "git_push", "config_change", "high_traffic"]:
        env_val = os.environ.get(f"REASONER_{key.upper()}")
        if env_val and env_val.lower() in ("1", "true", "yes"):
            evidence[key] = True

    return evidence


def get_parents(node, graph):
    """Return all direct parents (potential causes) of a node in the DAG."""
    parents = []
    for cause, effects in graph.items():
        if node in effects:
            parents.append(cause)
    return parents


def infer_causes(effect, evidence, graph=None, priors=None):
    """Backtrack from observed effect through the causal DAG.
    Returns list of (cause, confidence) tuples sorted by confidence desc.
    """
    if graph is None:
        graph = CAUSAL_GRAPH
    if priors is None:
        priors = PRIORS

    results = []
    direct_parents = get_parents(effect, graph)

    for parent in direct_parents:
        # Base confidence from prior (with evolution engine dynamic weight if available)
        base_conf = priors.get((parent, effect), 0.10)
        base_conf *= _get_weight(parent)  # V4.1: live weight from evolution engine

        # Evidence boost: if evidence confirms this parent happened
        evidence_boost = 1.0
        if evidence.get(parent):
            evidence_boost = 1.50  # 50% boost if evidence confirms

        confidence = min(base_conf * evidence_boost, 1.0)

        # Recursive: check root causes (2nd-level parents)
        root_parents = get_parents(parent, graph)
        root_chain = []
        for root in root_parents:
            root_base = priors.get((root, parent), 0.10)
            root_ev_boost = 1.50 if evidence.get(root) else 1.0
            root_conf = min(root_base * root_ev_boost, 1.0)
            chain_conf = min(root_conf * base_conf * DECAY_FACTOR, 1.0)
            root_chain.append({"cause": root, "confidence": round(chain_conf, 4)})

        results.append(
            {
                "cause": parent,
                "confidence": round(confidence, 4),
                "root_chain": root_chain if root_chain else None,
            }
        )

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def is_expected(effect, causes, evidence, threshold=0.60):
    """Check if any high-confidence cause is in the 'expected' whitelist
    AND confirmed by evidence (not just probabilistic prior).
    """
    expected_causes = {"deploy", "build_process", "cron_job"}
    for c in causes:
        cause_name = c["cause"]
        if cause_name in expected_causes and c["confidence"] >= threshold:
            # Must have evidence to confirm
            if evidence.get(cause_name):
                return True, cause_name
    return False, None


def parse_args():
    parser = argparse.ArgumentParser(description="Causal DAG inference engine")
    parser.add_argument("--infer", type=str, help="Effect to explain (e.g., cpu_load)")
    parser.add_argument("--evidence-path", type=str, help="Path to daemon state.json")
    parser.add_argument("--list-graph", action="store_true", help="Dump causal DAG")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--dry-run", action="store_true", help="Preview without side effects")
    parser.add_argument("--version", action="store_true", help="Print version")
    return parser.parse_args()


def main():
    # Intercept std flags first
    handled = _handle_std_flags()
    if handled is not None:
        return

    args = parse_args()

    if args.version:
        print(json.dumps({"version": VERSION}) if args.json else f"causal-reasoner v{VERSION}")
        return 0

    if args.list_graph:
        output = {"graph": CAUSAL_GRAPH, "priors_count": len(PRIORS), "nodes": list(CAUSAL_GRAPH.keys())}
        if args.json:
            print(json.dumps(output, indent=2))
        else:
            print("Causal DAG:")
            for cause, effects in CAUSAL_GRAPH.items():
                print(f"  {cause} -> {effects}")
        return 0

    if args.dry_run:
        target = args.infer or "N/A"
        output = {
            "mode": "dry-run",
            "infer_target": target,
            "graph_nodes": len(CAUSAL_GRAPH),
            "priors_count": len(PRIORS),
            "decay_factor": DECAY_FACTOR,
        }
        print(json.dumps(output, indent=2) if args.json else f"[DRY-RUN] Would infer: {target}")
        return 0

    if not args.infer:
        print(json.dumps({"error": "Missing --infer <effect>"}) if args.json else "ERROR: --infer required")
        return 2

    # Load evidence
    evidence = {}
    if args.evidence_path:
        evidence = load_evidence(args.evidence_path)

    # Infer
    causes = infer_causes(args.infer, evidence)
    is_exp, exp_cause = is_expected(args.infer, causes, evidence)

    result = {
        "effect": args.infer,
        "evidence_keys": list(evidence.keys()),
        "causes": causes,
        "expected": is_exp,
        "expected_cause": exp_cause,
        "verdict": "expected" if is_exp else "unexplained",
    }

    # Log to reasoning journal
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "reasoning.jsonl")
    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "effect": args.infer,
        "top_cause": causes[0] if causes else None,
        "expected": is_exp,
        "evidence": evidence,
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except OSError:
        pass

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Causal Reasoner v{VERSION}")
        print(f"  Effect:    {args.infer}")
        print(f"  Evidence:  {list(evidence.keys()) or 'none'}")
        print(
            f"  Top cause: {causes[0]['cause']} ({causes[0]['confidence']:.0%})" if causes else "  Top cause: unknown"
        )
        print(f"  Verdict:   {result['verdict'].upper()}")
        if is_exp:
            print(f"  Action:    Suppress alert (expected load from {exp_cause})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
