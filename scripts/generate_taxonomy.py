#!/usr/bin/env python3
"""
InkLoop Taxonomy Generator & Coverage Register CLI (Task T6.1).
Bootstraps backend sys.path to guarantee flawless execution from repository root or scripts dir.
Supports register checking, detailed coverage auditing, baseline rebuilding, and custom export.
"""
import sys
import argparse
from pathlib import Path

# Bootstrap backend into sys.path to resolve 'app' imports reliably
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.catalogue.register import TaxonomyRegister
    from app.catalogue.governance import LicenseRegistry
    from app.catalogue.enums import CoverageStatus
except ImportError as exc:
    print(f"Error importing InkLoop catalogue modules: {exc}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)


def cmd_check(register: TaxonomyRegister) -> int:
    """Audits taxonomy invariants and prints pass/fail summary."""
    errors = register.validate_invariants()
    summary = register.get_summary()

    print("=" * 60)
    print("INKLOOP 60-GROUP TAXONOMY REGISTER AUDIT")
    print("=" * 60)
    print(f"Total Groups:             {summary.total_groups}/60")
    print(f"Total Canonical Elements: {summary.total_canonical_elements}")
    print(f"Validated Groups:         {summary.validated_count}")
    print(f"Experimentally Tested:    {summary.experimentally_tested_count}")
    print(f"Researched Groups:        {summary.researched_count}")
    print(f"Unresearched Baseline:    {summary.unresearched_count}")
    print(f"Total Recipes:            {summary.total_recipes}")
    print(f"Total Generation Rules:   {summary.total_rules}")
    print(f"Total Research Claims:    {summary.total_claims}")
    print(f"Total Cited Sources:      {summary.total_sources}")
    print("-" * 60)

    if errors:
        print(f"AUDIT FAILED: {len(errors)} invariant violation(s) found:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("AUDIT PASSED: All 60 groups satisfy structural and evidence invariants.")
    return 0


def cmd_audit(register: TaxonomyRegister) -> int:
    """Prints comprehensive coverage audit including licensing compliance."""
    ret = cmd_check(register)

    lic_reg = LicenseRegistry(seed_defaults=True)
    lic_audit = lic_reg.audit_licenses()

    print("\n" + "=" * 60)
    print("LICENSING & GOVERNANCE AUDIT")
    print("=" * 60)
    print(f"Total Registered Licenses:   {lic_audit['total_registered_licenses']}")
    print(f"Commercial Cleared Assets:   {lic_audit['commercial_cleared_count']}")
    print(f"Uncleared / Unknown Rights:  {lic_audit['uncleared_or_unknown_count']}")
    print("Breakdown by Category:")
    for lic_type, count in lic_audit["breakdown_by_license_type"].items():
        print(f"  - {lic_type}: {count}")

    if lic_audit["uncleared_or_unknown_count"] > 0:
        print("\nWarning: Uncleared licenses require verification before commercial distribution.")
    else:
        print("\nAll baseline assets and libraries are cleared for commercial comic publication.")

    return ret


def cmd_rebuild(register: TaxonomyRegister) -> int:
    """Rebuilds the canonical 60-group data from data_loader and updates JSON."""
    print("Rebuilding canonical 60-group taxonomy register from data_loader...")
    register.rebuild_baseline()
    print("Successfully rebuilt and saved to register JSON.")
    return cmd_check(register)


def cmd_export(register: TaxonomyRegister, export_path: Path) -> int:
    """Exports register to custom path."""
    print(f"Exporting taxonomy register to {export_path}...")
    register.save(target_path=export_path)
    print(f"Export completed: {export_path.stat().st_size} bytes written.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="InkLoop Image Generation Knowledge Taxonomy & Governance CLI"
    )
    parser.add_argument(
        "--check", action="store_true", help="Audit register against structural and evidence invariants"
    )
    parser.add_argument(
        "--audit", action="store_true", help="Perform comprehensive coverage and licensing compliance audit"
    )
    parser.add_argument(
        "--rebuild", action="store_true", help="Rebuild register JSON from canonical data_loader baseline"
    )
    parser.add_argument(
        "--export", type=Path, help="Export canonical 60-group register JSON to specified path"
    )

    args = parser.parse_args()
    register = TaxonomyRegister(force_rebuild=args.rebuild)

    if args.rebuild:
        sys.exit(cmd_check(register))
    elif args.audit:
        sys.exit(cmd_audit(register))
    elif args.export:
        sys.exit(cmd_export(register, args.export))
    elif args.check:
        sys.exit(cmd_check(register))
    else:
        # Default: run check and brief summary
        sys.exit(cmd_check(register))


if __name__ == "__main__":
    main()
