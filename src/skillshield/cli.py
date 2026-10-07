"""SkillShield command-line interface (docs/product-plan.md P5).

``skillshield scan <path>`` runs the complete assessment pipeline
(``skillshield.pipeline.assess``) and prints the result. This is the
"preferred first interface" the plan calls for -- a single command that
performs ingestion through assessment without the caller touching any
internal module directly.
"""

from __future__ import annotations

import argparse
import json
import sys

from skillshield.ingestion.errors import IngestionError
from skillshield.pipeline import assess, assessment_to_jsonable
from skillshield.policy.errors import PolicyLoadError


def _format_capability_set(label: str, capabilities: frozenset) -> str:
    if not capabilities:
        return f"  {label} (0): none"
    names = ", ".join(sorted(capabilities))
    return f"  {label} ({len(capabilities)}): {names}"


def _format_evidence(evidence) -> list[str]:
    lines = []
    for item in evidence:
        detail_parts = [f"{k}={v}" for k, v in sorted(item.detail.items())]
        detail = f" [{', '.join(detail_parts)}]" if detail_parts else ""
        lines.append(f"        - {item.source.value}: {item.capability}{detail}")
    return lines


def format_report(assessment) -> str:
    """Render an Assessment as the human-readable report shown by default."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("SKILLSHIELD SECURITY ASSESSMENT")
    lines.append("=" * 60)
    lines.append(f"Skill: {assessment.skill_name} (v{assessment.skill_version}, id={assessment.skill_id})")
    lines.append("")
    lines.append(f"RECOMMENDATION: {assessment.recommendation.value}")
    lines.append("")
    lines.append("Capability summary (D/S/R/P):")
    lines.append(_format_capability_set("Declared", assessment.capabilities.declared))
    lines.append(_format_capability_set("Static", assessment.capabilities.static))
    lines.append(_format_capability_set("Runtime", assessment.capabilities.runtime))
    lines.append(_format_capability_set("Policy-permitted", assessment.capabilities.policy_permitted))
    lines.append("")

    if not assessment.findings:
        lines.append("Findings: none")
    else:
        lines.append(f"Findings ({len(assessment.findings)}):")
        for finding in assessment.findings:
            lines.append("")
            lines.append(f"  [{finding.severity.value}] {finding.finding_type.value}")
            if finding.capability:
                lines.append(f"    Capability: {finding.capability}")
            lines.append(f"    {finding.explanation}")
            if finding.policy_info is not None:
                permitted = "permitted" if finding.policy_info.permitted else "denied"
                lines.append(f"    Policy: {finding.policy_info.policy_name} ({permitted})")
            if finding.source_location:
                lines.append(f"    Source: {finding.source_location}")
            if finding.evidence:
                lines.append("    Evidence:")
                lines.extend(_format_evidence(finding.evidence))

    lines.append("")
    lines.append("Limitations:")
    for limitation in assessment.limitations:
        lines.append(f"  - {limitation}")
    lines.append("")
    lines.append(
        f"(policy={assessment.policy_name}, artifact_digest={assessment.artifact_digest}, "
        f"generated_at={assessment.generated_at})"
    )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skillshield", description="Assess a downloaded Agentic Skill.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Run a full security assessment on a skill.")
    scan.add_argument("path", help="Path to a skill directory or ZIP archive.")
    scan.add_argument(
        "--policy", type=str, default=None, metavar="PATH", help="Path to a policy JSON file (default: built-in conservative policy)."
    )
    scan.add_argument(
        "--timeout", type=float, default=10.0, metavar="SECONDS", help="Controlled-execution timeout in seconds (default: 10.0)."
    )
    scan.add_argument("--json", action="store_true", help="Print the assessment as JSON instead of a human-readable report.")

    ui = subparsers.add_parser("ui", help="Launch the local SkillShield web UI.")
    ui.add_argument("--host", type=str, default="127.0.0.1", metavar="HOST", help="Host to bind (default: 127.0.0.1).")
    ui.add_argument("--port", type=int, default=8765, metavar="PORT", help="Port to bind (default: 8765).")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        try:
            assessment = assess(
                args.path,
                policy_path=args.policy,
                timeout_seconds=args.timeout,
            )
        except IngestionError as exc:
            print(f"Could not assess '{args.path}': ingestion failed ({type(exc).__name__}): {exc}", file=sys.stderr)
            return 2
        except PolicyLoadError as exc:
            print(f"Could not load policy: {exc}", file=sys.stderr)
            return 3

        if args.json:
            print(json.dumps(assessment_to_jsonable(assessment), indent=2))
        else:
            print(format_report(assessment))
        return 0

    if args.command == "ui":
        from skillshield.ui.server import create_server

        server = create_server(args.host, args.port)
        bound_host, bound_port = server.server_address
        print(f"SkillShield UI running at http://{bound_host}:{bound_port}/ (Ctrl+C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 1  # pragma: no cover - argparse.error() already exits


if __name__ == "__main__":
    sys.exit(main())
