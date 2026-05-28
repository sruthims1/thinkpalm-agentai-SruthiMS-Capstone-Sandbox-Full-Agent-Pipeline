#!/usr/bin/env python
"""
MaritimeTestAI — CLI interface for the 4-agent QA pipeline.

Examples:
  python cli.py --feature "Crew Certification" --description "STCW cert management with expiry alerts"
  python cli.py --feature "Fatigue Management" --file sample_features/fatigue_management.txt
  python cli.py --feature "Voyage Planning"    --file sample_features/voyage_planning.txt --output json
  python cli.py --feature "Port Call"          --description "96h pre-arrival notices" --session-id abc123
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path

# Add src/ to path so all modules resolve without prefix
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

try:
    from rich.console import Console
    from rich.table   import Table
    from rich.panel   import Panel
    RICH = True
except ImportError:
    RICH = False

from pipeline.langgraph_pipeline import run_pipeline_sync


def _log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def _print_result(result: dict, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(result, indent=2, default=str))
        return

    de  = result.get("domain_analysis",   result.get("domain_enrichment", {})) or {}
    gr  = result.get("gherkin_result",    {}) or {}
    pr  = result.get("playwright_result", result.get("test_result", {})) or {}
    ar  = result.get("audit_result",      {}) or {}
    rr  = pr.get("risk_report", {}) or {}

    q_score  = rr.get("quality_score",         ar.get("overall_score",          0))
    p1_cov   = rr.get("p1_safety_coverage_pct",ar.get("p1_coverage_pct",        0))
    ov_cov   = rr.get("overall_coverage_pct",  pr.get("coverage_report", {}).get("coverage_percentage", 0))

    if RICH:
        c = Console()
        c.print(Panel(
            f"[bold cyan]MaritimeTestAI[/] — [yellow]{result.get('feature_name', '')}[/]",
            subtitle="[dim]4-Agent Maritime QA Pipeline[/]",
            style="blue",
        ))

        t = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 2))
        t.add_column("Metric",  style="cyan",  width=30)
        t.add_column("Value",   style="white", width=45)
        t.add_row("Risk Level",           _risk_fmt(de.get("risk_level", "—")))
        t.add_row("Applicable Regs",      str(len(de.get("applicable_regulations", []))))
        t.add_row("Gherkin Scenarios",    str(gr.get("scenario_count", 0)))
        t.add_row("Test Quality Score",   f"{q_score}/100")
        t.add_row("P1 Safety Coverage",   f"{p1_cov}%")
        t.add_row("Overall Coverage",     f"{ov_cov}%")
        t.add_row("Audit Score",          f"{ar.get('overall_score', '—')}/100")
        t.add_row("P1 Audit Coverage",    f"{ar.get('p1_coverage_pct', '—')}%")
        t.add_row("Coverage Gaps",        str(len(ar.get("coverage_gaps", []))))
        t.add_row("Critical P1 Gaps",     str(sum(1 for g in ar.get("coverage_gaps",[]) if g.get("priority")=="P1")))
        c.print(t)

        if ar.get("recommendations"):
            c.print("\n[bold yellow]Recommendations:[/]")
            for rec in ar["recommendations"][:5]:
                c.print(f"  [yellow]•[/] {rec}")

        if ar.get("executive_summary"):
            c.print(f"\n[bold green]Executive Summary:[/] {ar['executive_summary']}")

        sc_list = gr.get("scenario_titles", [])
        if sc_list:
            c.print(f"\n[bold green]Scenarios ({len(sc_list)}):[/]")
            for s in sc_list[:8]:
                c.print(f"  [green]✓[/] {s}")
            if len(sc_list) > 8:
                c.print(f"  [dim]... and {len(sc_list) - 8} more[/]")

        c.print(f"\n[dim]Generated files: generated_tests/{result.get('feature_name','').lower().replace(' ','_')}.*[/]")
    else:
        fn = result.get("feature_name", "")
        sep = "=" * 64
        print(f"\n{sep}")
        print(f"  MaritimeTestAI — {fn}")
        print(sep)
        print(f"  Risk Level:        {de.get('risk_level', '—')}")
        print(f"  Gherkin Scenarios: {gr.get('scenario_count', 0)}")
        print(f"  Quality Score:     {q_score}/100")
        print(f"  P1 Coverage:       {p1_cov}%")
        print(f"  Overall Coverage:  {ov_cov}%")
        print(f"  Audit Score:       {ar.get('overall_score', '—')}/100")
        print(f"  Coverage Gaps:     {len(ar.get('coverage_gaps', []))}")
        if ar.get("executive_summary"):
            print(f"\n  {ar['executive_summary']}")
        print(sep)


def _risk_fmt(risk: str) -> str:
    if not RICH:
        return risk
    colours = {"HIGH": "bold red", "MEDIUM": "bold yellow", "LOW": "bold green"}
    c = colours.get(risk.upper(), "white")
    return f"[{c}]{risk}[/]"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="maritime-qa",
        description="MaritimeTestAI — AI-powered maritime QA pipeline (4 agents, LangGraph)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py --feature "Crew Certification" --description "Track STCW certs with departure blocking"
  python cli.py --feature "Fatigue Management" --file sample_features/fatigue_management.txt
  python cli.py --feature "Voyage Planning"    --file sample_features/voyage_planning.txt --output json
  python cli.py --feature "Incident Reporting" --file sample_features/incident_reporting.txt
        """,
    )
    parser.add_argument("--feature",     required=True,               help="Feature name (e.g. 'Crew Certification')")
    parser.add_argument("--description", default="",                   help="Inline feature description")
    parser.add_argument("--file",        default=None,                 help="Path to .txt file with feature description")
    parser.add_argument("--session-id",  default=None,                 help="Resume a previous session (LangGraph checkpoint)")
    parser.add_argument("--output",      choices=["pretty", "json"],   default="pretty")

    args = parser.parse_args()

    description = args.description
    if args.file:
        try:
            description = Path(args.file).read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"[ERROR] File not found: {args.file}", file=sys.stderr)
            sys.exit(1)

    if not description.strip():
        print("[ERROR] Provide --description 'text' or --file path/to/feature.txt", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    if RICH:
        from rich.console import Console
        Console().print(f"\n[bold cyan]MaritimeTestAI[/] — Starting 4-agent pipeline for: [yellow]{args.feature}[/]")
    else:
        print(f"\nMaritimeTestAI — Starting pipeline for: {args.feature}")
    print("─" * 64)

    result = run_pipeline_sync(
        feature_name=args.feature,
        feature_description=description,
        session_id=args.session_id,
        log_cb=_log,
    )

    print("─" * 64)
    _print_result(result, args.output)

    if result.get("error"):
        print(f"\n[ERROR] Pipeline error: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
