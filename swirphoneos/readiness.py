"""Project ledger validation, not an independent hardware certification service."""
from __future__ import annotations

import json
from pathlib import Path
import re

REQUIRED_GATES = frozenset({
    "system_build", "physical_boot", "core_hardware", "install_restore",
    "windows_runtime", "security_review", "artifact_trust", "final_ci", "release_docs",
})


def load_ledger(path: Path) -> dict:
    def unique(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key in project ledger.")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def evaluate(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported project ledger schema.")
    milestones = data.get("milestones")
    gates = data.get("beta_gates")
    if not isinstance(milestones, list) or not milestones or not isinstance(gates, list):
        raise ValueError("Milestones and beta gates must be explicit lists.")
    total = done = 0
    seen: set[str] = set()
    for item in milestones:
        if not isinstance(item, dict):
            raise ValueError("Malformed milestone.")
        name, weight, passed = item.get("id"), item.get("weight"), item.get("complete")
        if not isinstance(name, str) or not name or name in seen:
            raise ValueError("Milestone IDs must be nonempty and unique.")
        if type(weight) is not int or not 0 < weight <= 100 or type(passed) is not bool:
            raise ValueError("Milestone weights and completion types are invalid.")
        if passed and not item.get("evidence"):
            raise ValueError("Completed milestones require evidence references.")
        seen.add(name)
        total += weight
        done += weight if passed else 0
    if total != 100:
        raise ValueError("Milestone weights must total exactly 100.")
    gate_ids = [g.get("id") if isinstance(g, dict) else None for g in gates]
    if any(not isinstance(gid, str) for gid in gate_ids):
        raise ValueError("Malformed beta gate.")
    if len(gate_ids) != len(REQUIRED_GATES) or set(gate_ids) != REQUIRED_GATES:
        raise ValueError("Mandatory beta gates are missing, duplicated or unknown.")
    blockers = []
    for gate in gates:
        if type(gate.get("passed")) is not bool:
            raise ValueError("Beta gate results must be booleans, not truthy strings.")
        if not gate["passed"]:
            blockers.append(gate["id"])
        else:
            evidence = gate.get("evidence")
            if not isinstance(evidence, list) or not evidence or not all(isinstance(x, str) and x.strip() for x in evidence):
                raise ValueError("Passed beta gates require reviewed evidence references.")
    candidate = data.get("candidate_commit")
    if any(g["passed"] for g in gates) and (not isinstance(candidate, str) or not re.fullmatch(r"[0-9a-f]{40}", candidate)):
        raise ValueError("Beta evidence must identify an exact candidate commit.")
    # A ledger alone cannot prove test execution, artifact trust or hardware state.
    # Exact candidate-file binding exists, but semantic gate verification is still incomplete.
    return {
        "progress_percent": done,
        "completed_milestones": sum(m["complete"] for m in milestones),
        "total_milestones": len(milestones),
        "beta_gates_passed": len(REQUIRED_GATES) - len(blockers),
        "beta_gates_total": len(REQUIRED_GATES),
        "blockers": blockers,
        "ledger_gates_complete": not blockers,
        "beta_release_allowed": False,
        "publication_blocker": "Candidate file binding exists, but gate-specific semantic evidence verification is not complete.",
    }
