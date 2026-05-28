"""
Gherkin validator — checks generated BDD test cases for structural correctness.
Validates Feature/Scenario/Given/When/Then syntax and extracts scenario metadata.
"""

import re
from dataclasses import dataclass, field


@dataclass
class GherkinScenario:
    title:    str
    tags:     list[str]
    steps:    list[str]
    line_num: int
    is_outline: bool = False


def validate_gherkin(gherkin_text: str) -> dict:
    """
    Validate a Gherkin feature file for structural correctness.
    Returns validation result, scenario list, and quality metrics.
    """
    errors   = []
    warnings = []
    lines    = gherkin_text.strip().splitlines()

    if not lines:
        return _result(False, errors=["Empty Gherkin text provided"], gherkin_text=gherkin_text)

    # ── Feature block ──────────────────────────────────────────────────────────
    feature_lines = [l for l in lines if l.strip().startswith("Feature:")]
    if not feature_lines:
        errors.append("Missing 'Feature:' declaration")
    elif len(feature_lines) > 1:
        errors.append("Multiple 'Feature:' declarations found — a file should have exactly one")

    feature_title = ""
    if feature_lines:
        feature_title = feature_lines[0].strip()[len("Feature:"):].strip()
        if not feature_title:
            warnings.append("Feature title is empty")

    # ── Scenario extraction ────────────────────────────────────────────────────
    scenarios: list[GherkinScenario] = []
    current_tags: list[str] = []
    current_scenario: GherkinScenario | None = None

    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if line.startswith("@"):
            current_tags = [t.strip() for t in line.split() if t.startswith("@")]
            continue

        if line.startswith("Scenario Outline:") or line.startswith("Scenario:"):
            if current_scenario:
                scenarios.append(current_scenario)
            is_outline = line.startswith("Scenario Outline:")
            prefix = "Scenario Outline:" if is_outline else "Scenario:"
            title  = line[len(prefix):].strip()
            if not title:
                warnings.append(f"Line {i}: Scenario has no title")
            current_scenario = GherkinScenario(
                title=title,
                tags=list(current_tags),
                steps=[],
                line_num=i,
                is_outline=is_outline,
            )
            current_tags = []
            continue

        if current_scenario and line.startswith(
            ("Given ", "When ", "Then ", "And ", "But ")
        ):
            current_scenario.steps.append(line)
            continue

    if current_scenario:
        scenarios.append(current_scenario)

    # ── Scenario validation ────────────────────────────────────────────────────
    if not scenarios:
        errors.append("No Scenario or Scenario Outline blocks found")

    for sc in scenarios:
        step_types = [s.split()[0] for s in sc.steps]

        if not any(t == "Given" for t in step_types):
            warnings.append(f"Scenario '{sc.title}': missing Given step")
        if not any(t == "When" for t in step_types):
            warnings.append(f"Scenario '{sc.title}': missing When step")
        if not any(t == "Then" for t in step_types):
            warnings.append(f"Scenario '{sc.title}': missing Then step")
        if len(sc.steps) == 0:
            errors.append(f"Scenario '{sc.title}': has no steps")
        if len(sc.steps) > 15:
            warnings.append(
                f"Scenario '{sc.title}': {len(sc.steps)} steps — consider splitting"
            )

    # ── Maritime domain tag check ──────────────────────────────────────────────
    safety_tags = {"@safety", "@compliance", "@critical", "@marpol", "@stcw",
                   "@mlc", "@ism", "@isps", "@solas"}
    tagged_safety = sum(
        1 for sc in scenarios if any(t.lower() in safety_tags for t in sc.tags)
    )

    if scenarios and tagged_safety == 0:
        warnings.append(
            "No safety/compliance tags found (@safety, @compliance, @critical). "
            "Tag safety-critical scenarios for traceability."
        )

    # ── Quality metrics ────────────────────────────────────────────────────────
    total_steps     = sum(len(sc.steps) for sc in scenarios)
    outline_count   = sum(1 for sc in scenarios if sc.is_outline)
    all_tags        = [t for sc in scenarios for t in sc.tags]

    return _result(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        feature_title=feature_title,
        scenario_count=len(scenarios),
        outline_count=outline_count,
        total_steps=total_steps,
        avg_steps_per_scenario=round(total_steps / len(scenarios), 1) if scenarios else 0,
        safety_tagged_count=tagged_safety,
        all_tags=sorted(set(all_tags)),
        scenarios=[
            {
                "title":      sc.title,
                "tags":       sc.tags,
                "step_count": len(sc.steps),
                "is_outline": sc.is_outline,
                "line":       sc.line_num,
            }
            for sc in scenarios
        ],
        gherkin_text=gherkin_text,
    )


def extract_scenario_titles(gherkin_text: str) -> list[str]:
    """Quick helper — returns just the list of scenario titles."""
    result = validate_gherkin(gherkin_text)
    return [sc["title"] for sc in result.get("scenarios", [])]


def _result(valid: bool, errors: list, gherkin_text: str = "", **kwargs) -> dict:
    return {
        "valid":         valid,
        "errors":        errors,
        "warnings":      kwargs.get("warnings", []),
        "feature_title": kwargs.get("feature_title", ""),
        "scenario_count": kwargs.get("scenario_count", 0),
        "outline_count":  kwargs.get("outline_count", 0),
        "total_steps":    kwargs.get("total_steps", 0),
        "avg_steps_per_scenario": kwargs.get("avg_steps_per_scenario", 0),
        "safety_tagged_count":    kwargs.get("safety_tagged_count", 0),
        "all_tags":       kwargs.get("all_tags", []),
        "scenarios":      kwargs.get("scenarios", []),
    }
