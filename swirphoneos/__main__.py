"""Run from the repository: python -m swirphoneos <command>."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from . import __version__
from .android_apps import AndroidAppSourceError, public_android_app_source_summary, validate_android_app_sources
from .aosp_workspace import AospWorkspaceError, make_workspace_plan, public_manifest_evidence, public_workspace_plan, stage_product_tree, validate_resolved_manifest
from .build_evidence import BuildEvidenceError, collect_build_evidence, create_evidence_bundle, load_json_report
from .build_preflight import BuildPreflightError, capture_host, evaluate_preflight
from .cuttlefish_evidence import CuttlefishEvidenceCollector, CuttlefishEvidenceError
from .diagnostics import DiagnosticError, ReadOnlyAdb
from .fastboot import FastbootDiagnosticError, ReadOnlyFastboot
from .i18n import LocalizationError, catalog_summary
from .identity import IdentityAssessmentError, build_unified_report
from .platform import PlatformBaselineError, load_baseline, public_baseline_summary
from .product_contract import ProductContractError, public_product_summary, validate_product_contract
from .profiles import ProfileError, discover_profiles, public_profile_summary
from .readiness import evaluate, load_ledger
from .swirroot import SwirRootPolicyError, load_policy, public_policy_summary
from .system_apps import SystemAppRegistryError, load_registry, public_registry_summary
from .transaction_evidence import TransactionEvidenceError, create_journal, load_plan, public_plan_summary, verify_artifacts

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="SwirPhoneOS read-only developer tooling — by Swir"); parser.add_argument("--version",action="version",version=__version__); sub=parser.add_subparsers(dest="command",required=True)
    for name in ("status","gate"): command=sub.add_parser(name); command.add_argument("--ledger",type=Path,default=Path("project.json"))
    inspect=sub.add_parser("inspect",help="Read selected properties from one authorized USB phone via ADB"); inspect.add_argument("--adb",required=True,type=Path,help="Absolute path to a trusted Android SDK adb executable")
    inspect_fastboot=sub.add_parser("inspect-fastboot",help="Read a small allowlist of variables from one local USB phone in Fastboot/FastbootD mode"); inspect_fastboot.add_argument("--fastboot",required=True,type=Path,help="Absolute path to a trusted Android SDK fastboot executable")
    inspect_device=sub.add_parser("inspect-device",help="Combine one read-only ADB/Fastboot report with non-authoritative local profile hints"); inspect_device.add_argument("--transport",required=True,choices=("adb","fastboot")); inspect_device.add_argument("--tool",required=True,type=Path,help="Absolute path to trusted adb/fastboot"); inspect_device.add_argument("--profiles",type=Path,default=Path("device_packs"))
    profiles=sub.add_parser("profiles",help="Validate and list metadata-only device profiles"); profiles.add_argument("--root",type=Path,default=Path("device_packs"))
    baseline=sub.add_parser("baseline",help="Validate and show the offline pinned AOSP baseline"); baseline.add_argument("--file",type=Path,default=Path("platform/aosp_baseline.json"))
    product_contract=sub.add_parser("product-contract",help="Validate the checked-in SwirPhoneOS Cuttlefish product integration contract"); product_contract.add_argument("--root",type=Path,default=Path("platform/aosp_product"))
    build_preflight=sub.add_parser("build-preflight",help="Inspect the local build host without installing/downloading/changing anything"); build_preflight.add_argument("--workspace",type=Path,default=Path.cwd())
    aosp_plan=sub.add_parser("aosp-plan",help="Generate an argv-only exact-tag AOSP sync/stage/build plan without executing it"); aosp_plan.add_argument("--workspace",type=Path,required=True); aosp_plan.add_argument("--jobs",type=int,default=8); aosp_plan.add_argument("--baseline",type=Path,default=Path("platform/aosp_baseline.json")); aosp_plan.add_argument("--product-root",type=Path,default=Path("platform/aosp_product"))
    resolved_manifest=sub.add_parser("aosp-manifest",help="Validate a captured repo manifest -r snapshot and report SHA-256"); resolved_manifest.add_argument("--file",type=Path,required=True)
    build_evidence=sub.add_parser("build-evidence",help="Hash a completed local SwirPhoneOS AOSP product and bind it to the pinned manifest"); build_evidence.add_argument("--workspace",type=Path,required=True); build_evidence.add_argument("--manifest",type=Path,required=True); build_evidence.add_argument("--baseline",type=Path,default=Path("platform/aosp_baseline.json"))
    evidence_bundle=sub.add_parser("evidence-bundle",help="Bind completed build evidence to completed Cuttlefish runtime evidence"); evidence_bundle.add_argument("--build",type=Path,required=True); evidence_bundle.add_argument("--runtime",type=Path,required=True)
    stage_product=sub.add_parser("stage-product",help="Plan or explicitly stage manifest-whitelisted Swir AOSP product/app source"); stage_product.add_argument("--workspace",type=Path,required=True); stage_product.add_argument("--product-root",type=Path,default=Path("platform/aosp_product")); stage_product.add_argument("--execute",action="store_true")
    cuttlefish=sub.add_parser("cuttlefish-evidence",help="Capture strict read-only runtime evidence from one local Cuttlefish/emulator"); cuttlefish.add_argument("--adb",required=True,type=Path,help="Absolute path to a trusted Android SDK adb executable"); cuttlefish.add_argument("--manifest",type=Path,default=Path("system_apps/manifest.json"))
    transaction_plan=sub.add_parser("transaction-plan",help="Validate a local preparation-only install/rollback plan; never performs device writes"); transaction_plan.add_argument("--file",required=True,type=Path)
    transaction_evidence=sub.add_parser("transaction-evidence",help="Verify local plan artifacts and optionally create a read-only recovery journal"); transaction_evidence.add_argument("--plan",required=True,type=Path); transaction_evidence.add_argument("--artifacts",required=True,type=Path); transaction_evidence.add_argument("--journal",type=Path,default=None,help="Optional absolute create-only .json journal path")
    sub.add_parser("i18n",help="Validate shared localization catalogs and show translation coverage")
    apps=sub.add_parser("apps",help="Validate the essential first-party system-app registry"); apps.add_argument("--manifest",type=Path,default=Path("system_apps/manifest.json"))
    android_apps=sub.add_parser("android-apps",help="Validate checked-in first-party Android app source without claiming build/runtime"); android_apps.add_argument("--product-root",type=Path,default=Path("platform/aosp_product")); android_apps.add_argument("--manifest",type=Path,default=Path("system_apps/manifest.json"))
    root_policy=sub.add_parser("root-policy",help="Validate the fail-closed SwirRoot safety contract; performs no device writes"); root_policy.add_argument("--policy",type=Path,default=Path("swirroot/policy.json"))
    args=parser.parse_args(argv)
    try:
        if args.command=="inspect": result=ReadOnlyAdb(args.adb).inspect()
        elif args.command=="inspect-fastboot": result=ReadOnlyFastboot(args.fastboot).inspect()
        elif args.command=="inspect-device":
            report=ReadOnlyAdb(args.tool).inspect() if args.transport=="adb" else ReadOnlyFastboot(args.tool).inspect(); result=build_unified_report(args.transport,report,discover_profiles(args.profiles))
        elif args.command=="profiles":
            registry=discover_profiles(args.root); result={"schema_version":1,"profile_count":len(registry),"profiles":[public_profile_summary(p) for p in registry],"flash_allowed":False}
        elif args.command=="baseline": result=public_baseline_summary(load_baseline(args.file))
        elif args.command=="product-contract": result=public_product_summary(validate_product_contract(args.root))
        elif args.command=="build-preflight": result=evaluate_preflight(capture_host(args.workspace.resolve()))
        elif args.command=="aosp-plan": result=public_workspace_plan(make_workspace_plan(load_baseline(args.baseline),validate_product_contract(args.product_root),args.workspace,jobs=args.jobs))
        elif args.command=="aosp-manifest": result=public_manifest_evidence(validate_resolved_manifest(args.file))
        elif args.command=="build-evidence": result=collect_build_evidence(args.workspace,args.manifest,args.baseline)
        elif args.command=="evidence-bundle": result=create_evidence_bundle(load_json_report(args.build),load_json_report(args.runtime))
        elif args.command=="stage-product": validate_product_contract(args.product_root); result=stage_product_tree(args.product_root,args.workspace,execute=args.execute)
        elif args.command=="cuttlefish-evidence": result=CuttlefishEvidenceCollector(args.adb).inspect(load_registry(args.manifest))
        elif args.command=="transaction-plan": result=public_plan_summary(load_plan(args.file))
        elif args.command=="transaction-evidence":
            plan=load_plan(args.plan); evidence=verify_artifacts(plan,args.artifacts); result=create_journal(args.journal,plan,evidence) if args.journal is not None else evidence
        elif args.command=="i18n": result=catalog_summary()
        elif args.command=="apps": result=public_registry_summary(load_registry(args.manifest))
        elif args.command=="android-apps": result=public_android_app_source_summary(validate_android_app_sources(args.product_root,args.manifest))
        elif args.command=="root-policy": result=public_policy_summary(load_policy(args.policy))
        else: result=evaluate(load_ledger(args.ledger))
        print(json.dumps(result,indent=2,ensure_ascii=True)); return 2 if args.command=="gate" and not result["beta_release_allowed"] else 0
    except (AndroidAppSourceError,AospWorkspaceError,BuildEvidenceError,BuildPreflightError,CuttlefishEvidenceError,DiagnosticError,FastbootDiagnosticError,IdentityAssessmentError,LocalizationError,PlatformBaselineError,ProductContractError,ProfileError,SwirRootPolicyError,SystemAppRegistryError,TransactionEvidenceError,OSError,ValueError):
        print("Operation failed: check project metadata or the trusted Android SDK tool path, USB mode, AOSP workspace/evidence/app source, local transaction evidence, host workspace and single-device connection. Raw errors are withheld for privacy.",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
