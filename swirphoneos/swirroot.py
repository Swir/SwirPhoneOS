"""Safety contract for the future first-party SwirRoot service.

This module deliberately performs no root, bootloader, image or device writes.
It validates the policy that a future Android implementation must satisfy.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

REQUIRED_STATES = ("UNAVAILABLE", "ROOT_OFF", "ROOT_ON", "TRANSITION")
REQUIRED_TRANSITION_GATES = frozenset(
    {
        "exact_build_match",
        "verified_device_profile",
        "owner_confirmation",
        "rollback_material_verified",
        "journal_available",
        "update_state_safe",
        "expected_nonroot_state_known",
    }
)
REQUIRED_ENABLE_GATES = REQUIRED_TRANSITION_GATES
REQUIRED_UNROOT_GATES = REQUIRED_TRANSITION_GATES
REQUIRED_FORBIDDEN_METHODS = frozenset(
    {
        "bootloader_exploit",
        "vendor_protection_bypass",
        "silent_unlock",
        "unattended_flash",
        "account_lock_bypass",
    }
)


class SwirRootPolicyError(ValueError):
    """Raised when SwirRoot policy metadata is unsafe or malformed."""


@dataclass(frozen=True)
class SwirRootPolicy:
    policy_id: str
    states: tuple[str, ...]
    default_state: str
    authorization_default: str
    per_app_authorization: bool
    audit_required: bool
    enable_gates: frozenset[str]
    unroot_gates: frozenset[str]
    forbidden_methods: frozenset[str]
    write_operations_enabled: bool
    supported_builds: tuple[str, ...]

    @property
    def root_available(self) -> bool:
        return self.write_operations_enabled and bool(self.supported_builds)


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SwirRootPolicyError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> object:
    if not path.is_file() or path.is_symlink():
        raise SwirRootPolicyError("SwirRoot policy file must be an existing regular file, not a symlink.")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SwirRootPolicyError("SwirRoot policy file cannot be read.") from exc
    if len(text) > 131_072:
        raise SwirRootPolicyError("SwirRoot policy file is oversized.")
    try:
        return json.loads(text, object_pairs_hook=_strict_object)
    except SwirRootPolicyError:
        raise
    except json.JSONDecodeError as exc:
        raise SwirRootPolicyError("SwirRoot policy file is invalid JSON.") from exc


def _string_set(value: object, field: str, *, exact: frozenset[str] | None = None) -> frozenset[str]:
    if not isinstance(value, list) or not value:
        raise SwirRootPolicyError(f"{field} must be a non-empty list.")
    if not all(isinstance(item, str) and item and len(item) <= 96 for item in value):
        raise SwirRootPolicyError(f"{field} contains an invalid item.")
    result = frozenset(value)
    if len(result) != len(value):
        raise SwirRootPolicyError(f"{field} contains duplicates.")
    if exact is not None and result != exact:
        raise SwirRootPolicyError(f"{field} does not match the mandatory safety contract.")
    return result


def validate_policy(data: object) -> SwirRootPolicy:
    if not isinstance(data, dict) or set(data) != {
        "schema_version",
        "policy_id",
        "states",
        "default_state",
        "authorization",
        "enable_requirements",
        "unroot_requirements",
        "forbidden_methods",
        "write_operations_enabled",
        "supported_builds",
        "notes",
    }:
        raise SwirRootPolicyError("SwirRoot policy must match schema v1 exactly.")
    if data["schema_version"] != 1:
        raise SwirRootPolicyError("Unsupported SwirRoot policy schema.")
    policy_id = data["policy_id"]
    if policy_id != "swirroot-v1":
        raise SwirRootPolicyError("Unexpected SwirRoot policy id.")

    states_raw = data["states"]
    if not isinstance(states_raw, list) or tuple(states_raw) != REQUIRED_STATES:
        raise SwirRootPolicyError("SwirRoot state model must remain explicit and ordered.")
    default_state = data["default_state"]
    if default_state != "UNAVAILABLE":
        raise SwirRootPolicyError("Unverified builds must default SwirRoot to UNAVAILABLE.")

    authorization = data["authorization"]
    if not isinstance(authorization, dict) or set(authorization) != {
        "default",
        "per_app",
        "audit_required",
        "emergency_disable",
    }:
        raise SwirRootPolicyError("SwirRoot authorization policy is malformed.")
    if authorization["default"] != "deny":
        raise SwirRootPolicyError("Root authorization must be deny-by-default.")
    for key in ("per_app", "audit_required", "emergency_disable"):
        if authorization[key] is not True:
            raise SwirRootPolicyError(f"SwirRoot authorization requires {key}=true.")

    enable_gates = _string_set(
        data["enable_requirements"], "enable_requirements", exact=REQUIRED_ENABLE_GATES
    )
    unroot_gates = _string_set(
        data["unroot_requirements"], "unroot_requirements", exact=REQUIRED_UNROOT_GATES
    )
    forbidden_methods = _string_set(
        data["forbidden_methods"], "forbidden_methods", exact=REQUIRED_FORBIDDEN_METHODS
    )

    writes = data["write_operations_enabled"]
    if type(writes) is not bool:
        raise SwirRootPolicyError("write_operations_enabled must be boolean.")
    supported_builds = data["supported_builds"]
    if not isinstance(supported_builds, list) or len(supported_builds) > 128:
        raise SwirRootPolicyError("supported_builds must be a bounded list.")
    clean_builds: list[str] = []
    for build in supported_builds:
        if not isinstance(build, str) or not build.strip() or len(build) > 128:
            raise SwirRootPolicyError("supported_builds contains an invalid build id.")
        if any(ord(char) < 32 or ord(char) == 127 for char in build) or not build.isascii():
            raise SwirRootPolicyError("supported_builds contains unsafe characters.")
        if build in clean_builds:
            raise SwirRootPolicyError("supported_builds contains duplicates.")
        clean_builds.append(build)

    if writes and not clean_builds:
        raise SwirRootPolicyError("Root writes cannot be enabled without exact supported builds.")
    if clean_builds and not writes:
        raise SwirRootPolicyError("Supported root builds cannot be declared while writes are disabled.")

    notes = data["notes"]
    if not isinstance(notes, str) or not notes.strip() or len(notes) > 4096:
        raise SwirRootPolicyError("SwirRoot policy notes are invalid.")

    return SwirRootPolicy(
        policy_id=policy_id,
        states=REQUIRED_STATES,
        default_state=default_state,
        authorization_default="deny",
        per_app_authorization=True,
        audit_required=True,
        enable_gates=enable_gates,
        unroot_gates=unroot_gates,
        forbidden_methods=forbidden_methods,
        write_operations_enabled=writes,
        supported_builds=tuple(clean_builds),
    )


def load_policy(path: Path) -> SwirRootPolicy:
    return validate_policy(_load_json(path))


def public_policy_summary(policy: SwirRootPolicy) -> dict[str, object]:
    return {
        "schema_version": 1,
        "policy_id": policy.policy_id,
        "states": list(policy.states),
        "default_state": policy.default_state,
        "authorization_default": policy.authorization_default,
        "per_app_authorization": policy.per_app_authorization,
        "audit_required": policy.audit_required,
        "write_operations_enabled": policy.write_operations_enabled,
        "supported_build_count": len(policy.supported_builds),
        "root_available": policy.root_available,
        "enable_requirements": sorted(policy.enable_gates),
        "unroot_requirements": sorted(policy.unroot_gates),
        "forbidden_methods": sorted(policy.forbidden_methods),
    }
