"""Deterministic host-side orchestration for a pinned SwirPhoneOS AOSP workspace."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath
import re
import shutil
import xml.etree.ElementTree as ET

from .platform import PlatformBaseline
from .product_contract import ProductContract
from .stage_manifest import StageManifestError, load_stage_files


class AospWorkspaceError(ValueError):
    """Raised when reproducible-workspace evidence or input is unsafe/invalid."""

_SHA1=re.compile(r"[0-9a-f]{40}\Z")
_MAX_MANIFEST_BYTES=16*1024*1024
_MAX_STAGE_FILE_BYTES=2*1024*1024
_MAX_STAGE_TOTAL_BYTES=32*1024*1024
_MAX_STAGE_FILES=512
_LEGACY_STAGE_FILES=("AndroidProducts.mk","swirphoneos_cf_x86_64.mk")

@dataclass(frozen=True)
class AospWorkspacePlan:
    workspace:Path; manifest_url:str; revision:str; lunch_choice:str; jobs:int; commands:tuple[tuple[str,...],...]; stage_destination:Path
@dataclass(frozen=True)
class ResolvedManifestEvidence:
    project_count:int; unique_path_count:int; sha256:str; all_projects_pinned:bool
@dataclass(frozen=True)
class StageEntry:
    source:PurePosixPath; destination:PurePosixPath


def _safe_workspace(path:Path)->Path:
    resolved=path.expanduser().resolve()
    if resolved==Path(resolved.anchor): raise AospWorkspaceError("AOSP workspace must not be a filesystem root.")
    return resolved


def make_workspace_plan(baseline:PlatformBaseline,contract:ProductContract,workspace:Path,*,jobs:int=8)->AospWorkspacePlan:
    if not baseline.pinned or baseline.repo_init_revision is None: raise AospWorkspaceError("AOSP baseline is not completely pinned.")
    if baseline.status=="CANDIDATE_NOT_PINNED": raise AospWorkspaceError("Unpinned AOSP candidates cannot create a workspace plan.")
    if not isinstance(jobs,int) or isinstance(jobs,bool) or not 1<=jobs<=256: raise AospWorkspaceError("jobs must be an integer between 1 and 256.")
    root=_safe_workspace(workspace); stage_destination=root/"vendor"/"swir"
    build_script="set -euo pipefail; source build/envsetup.sh; "+f"lunch {contract.lunch_choice}; m -j{jobs}"
    commands=(("repo","init","-u",baseline.manifest_url,"-b",baseline.repo_init_revision),("repo","sync","-c","--no-tags","--optimized-fetch","--prune",f"-j{jobs}"),("repo","manifest","-r","-o","swirphoneos-pinned-manifest.xml"),("python","-m","swirphoneos","stage-product","--workspace",str(root),"--execute"),("bash","-lc",build_script))
    return AospWorkspacePlan(root,baseline.manifest_url,baseline.repo_init_revision,contract.lunch_choice,jobs,commands,stage_destination)


def public_workspace_plan(plan:AospWorkspacePlan)->dict[str,object]:
    return {"schema_version":2,"workspace":str(plan.workspace),"manifest_url":plan.manifest_url,"revision":plan.revision,"lunch_choice":plan.lunch_choice,"jobs":plan.jobs,"commands":[list(c) for c in plan.commands],"stage_destination":str(plan.stage_destination),"device_write_allowed":False,"build_verified":False,"boot_verified":False,"note":"Plan only. Source sync, explicit source staging, build and boot require local execution/evidence."}


def _read_manifest(path:Path)->str:
    if not path.is_file(): raise AospWorkspaceError("Resolved manifest snapshot does not exist.")
    try: raw=path.read_bytes()
    except OSError as exc: raise AospWorkspaceError("Resolved manifest snapshot could not be read.") from exc
    if not raw or len(raw)>_MAX_MANIFEST_BYTES: raise AospWorkspaceError("Resolved manifest snapshot has an invalid size.")
    try: return raw.decode("utf-8")
    except UnicodeError as exc: raise AospWorkspaceError("Resolved manifest snapshot must be UTF-8.") from exc


def validate_resolved_manifest(path:Path)->ResolvedManifestEvidence:
    text=_read_manifest(path)
    try: root=ET.fromstring(text)
    except ET.ParseError as exc: raise AospWorkspaceError("Resolved manifest snapshot is not valid XML.") from exc
    if root.tag!="manifest": raise AospWorkspaceError("Resolved manifest root element must be <manifest>.")
    projects=root.findall("project")
    if not projects: raise AospWorkspaceError("Resolved manifest contains no projects.")
    paths=set(); names=set(); all_pinned=True
    for project in projects:
        name=(project.get("name") or "").strip(); project_path=(project.get("path") or name).strip(); revision=(project.get("revision") or "").strip()
        if not name or not project_path: raise AospWorkspaceError("Resolved manifest project is missing name/path identity.")
        if name in names or project_path in paths: raise AospWorkspaceError("Resolved manifest contains duplicate project identity/path.")
        names.add(name); paths.add(project_path)
        if not _SHA1.fullmatch(revision): all_pinned=False
    if not all_pinned: raise AospWorkspaceError("Resolved manifest contains a floating/non-SHA project revision.")
    return ResolvedManifestEvidence(len(projects),len(paths),hashlib.sha256(text.encode("utf-8")).hexdigest(),True)


def public_manifest_evidence(evidence:ResolvedManifestEvidence)->dict[str,object]:
    return {"schema_version":1,"project_count":evidence.project_count,"unique_path_count":evidence.unique_path_count,"sha256":evidence.sha256,"all_projects_pinned":evidence.all_projects_pinned,"build_verified":False,"boot_verified":False}


def _load_stage_entries(product_root:Path)->tuple[StageEntry,...]:
    try: records=load_stage_files(product_root,max_files=_MAX_STAGE_FILES)
    except StageManifestError as exc: raise AospWorkspaceError(str(exc)) from exc
    if not records:
        return tuple(StageEntry(PurePosixPath(name),PurePosixPath("vendor/swir/products")/name) for name in _LEGACY_STAGE_FILES)
    if len(records)<2: raise AospWorkspaceError("AOSP stage manifest file count is invalid.")
    entries=[]; total_bytes=0
    for record in records:
        source=product_root/Path(*record.source.parts)
        if not source.is_file() or source.is_symlink(): raise AospWorkspaceError("AOSP stage source is missing or not a regular file.")
        size=source.stat().st_size
        if size<=0 or size>_MAX_STAGE_FILE_BYTES: raise AospWorkspaceError("AOSP stage source has an invalid size.")
        total_bytes+=size
        if total_bytes>_MAX_STAGE_TOTAL_BYTES: raise AospWorkspaceError("AOSP stage bundle is oversized.")
        entries.append(StageEntry(record.source,record.destination))
    return tuple(entries)


def stage_product_tree(product_root:Path,workspace:Path,*,execute:bool=False)->dict[str,object]:
    source=product_root.expanduser().resolve(); target_root=_safe_workspace(workspace); entries=_load_stage_entries(source)
    planned=[{"source":str(source/Path(*e.source.parts)),"destination":str(target_root/Path(*e.destination.parts))} for e in entries]
    if execute:
        if not (target_root/".repo").is_dir() or not (target_root/"build"/"envsetup.sh").is_file(): raise AospWorkspaceError("Refusing to stage into a directory that is not an initialized AOSP checkout.")
        for entry in entries:
            src=source/Path(*entry.source.parts); dst=target_root/Path(*entry.destination.parts); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
    return {"schema_version":3,"workspace":str(target_root),"destination_root":str(target_root/"vendor"/"swir"),"file_count":len(entries),"files":planned,"executed":execute,"device_write_allowed":False,"note":"Stages only manifest-whitelisted Swir AOSP product/app source; it does not build Android or write to a phone."}
