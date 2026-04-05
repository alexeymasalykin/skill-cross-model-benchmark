"""
Skill Benchmark Analyzer
Анализирует результаты прогона, считает метрики, генерирует таблицы и графики.
Использование: python scripts/analyze_results.py results/<run_id>.json [--compare results/<baseline>.json]
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BASE_DIR = Path(__file__).resolve().parent.parent
ANALYSIS_DIR = BASE_DIR / "analysis"
ANALYSIS_DIR.mkdir(exist_ok=True)


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_test_cases() -> dict[int, dict]:
    cases = load_json(BASE_DIR / "tests" / "test_cases.json")
    return {c["id"]: c for c in cases}


# --- Evaluation ---

def get_tool_names(result: dict) -> list[str]:
    """Extract ordered list of tool names from a result."""
    return [tc["name"] for tc in result.get("tool_calls", [])]


def check_classification(result: dict, expected: dict) -> bool:
    """Check if classify_issue was called and model used correct type in create_task."""
    if expected["expected_type"] is None:
        return True
    for tc in result.get("tool_calls", []):
        if tc["name"] == "create_task":
            return tc["params"].get("type") == expected["expected_type"]
    # If no create_task expected, check that classify_issue was called
    tools = get_tool_names(result)
    return "classify_issue" in tools


def check_priority(result: dict, expected: dict) -> bool:
    """Check if priority is within allowed range."""
    if not expected["allowed_priorities"]:
        return True
    for tc in result.get("tool_calls", []):
        if tc["name"] == "create_task":
            return tc["params"].get("priority") in expected["allowed_priorities"]
    return True


def check_tool_sequence(result: dict, expected: dict) -> bool:
    """Check if tool call sequence matches expected."""
    actual = get_tool_names(result)
    expected_seq = expected["expected_tool_sequence"]
    return actual == expected_seq


def check_restraint(result: dict, expected: dict) -> bool | None:
    """Check if model correctly did NOT call create_task. Returns None if not applicable."""
    if not expected["expect_no_create_task"]:
        return None
    tools = get_tool_names(result)
    return "create_task" not in tools


def check_duplicates(result: dict, expected: dict) -> bool | None:
    """Check if duplicate_ids are correct. Returns None if not applicable."""
    if not expected["expected_duplicate_ids"]:
        return None
    for tc in result.get("tool_calls", []):
        if tc["name"] == "create_task":
            actual_ids = sorted(tc["params"].get("duplicate_ids", []))
            expected_ids = sorted(expected["expected_duplicate_ids"])
            return actual_ids == expected_ids
    return False


def check_multi_issue(result: dict, expected: dict) -> bool | None:
    """Check if model detected multiple issues. Returns None if not applicable."""
    if not expected["expect_multi_issue"]:
        return None
    tools = get_tool_names(result)
    return tools.count("create_task") >= 2


def classify_error(result: dict, expected: dict) -> str | None:
    """Classify error type. Returns None if no error."""
    actual = get_tool_names(result)
    expected_seq = expected["expected_tool_sequence"]

    # E — extra call (restraint failure)
    if expected["expect_no_create_task"] and "create_task" in actual:
        return "E"

    # A — didn't call tool at all
    if expected_seq and not actual:
        return "A"

    # B — wrong tool
    if actual and expected_seq:
        actual_set = set(actual)
        expected_set = set(expected_seq)
        if actual_set - expected_set:
            return "B"

    # D — wrong order
    if actual and expected_seq and actual != expected_seq:
        return "D"

    # C — wrong parameters
    if not check_priority(result, expected):
        return "C"
    if not check_classification(result, expected):
        return "C"
    dup_check = check_duplicates(result, expected)
    if dup_check is False:
        return "C"

    # F — lost context (used fallback = ignored mock result)
    if result.get("used_fallback"):
        return "F"

    return None


def is_fully_correct(result: dict, expected: dict) -> bool:
    """Check if result is fully correct."""
    return (
        check_tool_sequence(result, expected)
        and check_classification(result, expected)
        and check_priority(result, expected)
        and (check_restraint(result, expected) is not False)
        and (check_duplicates(result, expected) is not False)
        and (check_multi_issue(result, expected) is not False)
    )


# --- Aggregation ---

def compute_metrics(results: list[dict], test_cases: dict[int, dict]) -> dict:
    """Compute all metrics grouped by model."""
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_model[r["model"]].append(r)

    metrics = {}
    for model, runs in by_model.items():
        model_short = model.split("/")[-1]

        # Group by test case
        by_case: dict[int, list[dict]] = defaultdict(list)
        for r in runs:
            by_case[r["test_case"]].append(r)

        # Per-level success rates
        level_success: dict[int, list[bool]] = defaultdict(list)
        all_correct: list[bool] = []
        all_seq: list[bool] = []
        all_class: list[bool] = []
        all_prio: list[bool] = []
        restraint_results: list[bool] = []
        dup_results: list[bool] = []
        multi_results: list[bool] = []
        error_types: list[str] = []
        consistency_scores: list[float] = []

        for case_id, case_runs in by_case.items():
            tc = test_cases[case_id]
            case_correct = []

            for r in case_runs:
                correct = is_fully_correct(r, tc)
                case_correct.append(correct)
                all_correct.append(correct)
                level_success[tc["level"]].append(correct)
                all_seq.append(check_tool_sequence(r, tc))
                all_class.append(check_classification(r, tc))
                all_prio.append(check_priority(r, tc))

                restraint = check_restraint(r, tc)
                if restraint is not None:
                    restraint_results.append(restraint)

                dup = check_duplicates(r, tc)
                if dup is not None:
                    dup_results.append(dup)

                multi = check_multi_issue(r, tc)
                if multi is not None:
                    multi_results.append(multi)

                err = classify_error(r, tc)
                if err:
                    error_types.append(err)

            # Consistency: what % of runs for this case gave same result?
            if case_correct:
                most_common = max(
                    set(str(c) for c in case_correct),
                    key=lambda x: sum(1 for c in case_correct if str(c) == x),
                )
                consistency = sum(
                    1 for c in case_correct if str(c) == most_common
                ) / len(case_correct)
                consistency_scores.append(consistency)

        def pct(lst: list[bool]) -> float:
            return round(sum(lst) / len(lst) * 100, 1) if lst else 0.0

        # Error distribution
        error_dist = {}
        for et in ["A", "B", "C", "D", "E", "F"]:
            error_dist[et] = error_types.count(et)

        # Latencies
        latencies = [r["latency_ms"] for r in runs if "latency_ms" in r]

        metrics[model_short] = {
            "success_rate_total": pct(all_correct),
            "success_rate_L1": pct(level_success.get(1, [])),
            "success_rate_L2": pct(level_success.get(2, [])),
            "success_rate_L3": pct(level_success.get(3, [])),
            "restraint_L4": pct(restraint_results),
            "tool_sequence_accuracy": pct(all_seq),
            "classification_accuracy": pct(all_class),
            "priority_accuracy": pct(all_prio),
            "duplicate_handling": pct(dup_results),
            "multi_issue_detection": pct(multi_results),
            "consistency": round(
                sum(consistency_scores) / len(consistency_scores) * 100, 1
            ) if consistency_scores else 0.0,
            "avg_latency_ms": round(
                sum(latencies) / len(latencies)
            ) if latencies else 0,
            "error_distribution": error_dist,
            "total_runs": len(runs),
            "total_errors": len(error_types),
        }

    return metrics


# --- Output ---

def print_summary_table(metrics: dict) -> None:
    """Print the main summary table."""
    models = list(metrics.keys())
    rows = [
        ("Success rate (total)", "success_rate_total", "%"),
        ("Success rate (L1)", "success_rate_L1", "%"),
        ("Success rate (L2)", "success_rate_L2", "%"),
        ("Success rate (L3)", "success_rate_L3", "%"),
        ("Restraint (L4)", "restraint_L4", "%"),
        ("Tool sequence", "tool_sequence_accuracy", "%"),
        ("Classification", "classification_accuracy", "%"),
        ("Priority", "priority_accuracy", "%"),
        ("Duplicate handling", "duplicate_handling", "%"),
        ("Multi-issue", "multi_issue_detection", "%"),
        ("Consistency", "consistency", "%"),
        ("Avg latency", "avg_latency_ms", "ms"),
    ]

    # Header
    header = f"{'Metric':<25}" + "".join(f"{m:>20}" for m in models)
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))

    for label, key, unit in rows:
        line = f"{label:<25}"
        for m in models:
            val = metrics[m][key]
            line += f"{val:>18}{unit:>2}"
        print(line)

    print("=" * len(header))

    # Error distribution
    print("\nError Distribution:")
    error_labels = {
        "A": "A — Didn't call tool",
        "B": "B — Wrong tool",
        "C": "C — Wrong params",
        "D": "D — Wrong order",
        "E": "E — Extra call",
        "F": "F — Lost context",
    }
    header2 = f"{'Error type':<25}" + "".join(f"{m:>20}" for m in models)
    print(header2)
    print("-" * len(header2))
    for code, label in error_labels.items():
        line = f"{label:<25}"
        for m in models:
            val = metrics[m]["error_distribution"].get(code, 0)
            line += f"{val:>20}"
        print(line)


def generate_heatmap(results: list[dict], test_cases: dict[int, dict]) -> None:
    """Generate heatmap: models × test cases, color = success rate."""
    by_model: dict[str, dict[int, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for r in results:
        model = r["model"].split("/")[-1]
        tc = test_cases[r["test_case"]]
        by_model[model][r["test_case"]].append(is_fully_correct(r, tc))

    models = sorted(by_model.keys())
    case_ids = sorted(test_cases.keys())

    data = []
    for model in models:
        row = []
        for cid in case_ids:
            runs = by_model[model].get(cid, [])
            rate = sum(runs) / len(runs) if runs else 0
            row.append(rate)
        data.append(row)

    fig, ax = plt.subplots(figsize=(12, 5))
    im = ax.imshow(data, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(range(len(case_ids)))
    ax.set_xticklabels([f"Case {c}" for c in case_ids], rotation=45, ha="right")
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models)

    # Annotate cells
    for i in range(len(models)):
        for j in range(len(case_ids)):
            val = data[i][j]
            color = "white" if val < 0.5 else "black"
            ax.text(j, i, f"{val:.0%}", ha="center", va="center", color=color, fontsize=9)

    plt.colorbar(im, ax=ax, label="Success Rate")
    ax.set_title("Model × Test Case Success Rate")
    plt.tight_layout()
    plt.savefig(ANALYSIS_DIR / "heatmap.png", dpi=150)
    plt.close()
    print(f"Saved: {ANALYSIS_DIR / 'heatmap.png'}")


def generate_bar_chart(metrics: dict) -> None:
    """Generate bar chart: success rate by difficulty level."""
    models = list(metrics.keys())
    levels = ["L1", "L2", "L3", "L4"]
    level_keys = ["success_rate_L1", "success_rate_L2", "success_rate_L3", "restraint_L4"]

    x = range(len(levels))
    width = 0.8 / len(models)

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, model in enumerate(models):
        values = [metrics[model][k] for k in level_keys]
        offset = (i - len(models) / 2 + 0.5) * width
        ax.bar([xi + offset for xi in x], values, width, label=model)

    ax.set_xlabel("Difficulty Level")
    ax.set_ylabel("Success Rate (%)")
    ax.set_title("Success Rate by Difficulty Level")
    ax.set_xticks(list(x))
    ax.set_xticklabels(levels)
    ax.legend()
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.set_ylim(0, 105)
    plt.tight_layout()
    plt.savefig(ANALYSIS_DIR / "success_by_level.png", dpi=150)
    plt.close()
    print(f"Saved: {ANALYSIS_DIR / 'success_by_level.png'}")


def generate_error_pies(metrics: dict) -> None:
    """Generate pie charts: error distribution per model."""
    models = list(metrics.keys())
    fig, axes = plt.subplots(1, len(models), figsize=(5 * len(models), 5))
    if len(models) == 1:
        axes = [axes]

    labels = ["A", "B", "C", "D", "E", "F"]
    colors = ["#e74c3c", "#e67e22", "#f1c40f", "#3498db", "#9b59b6", "#95a5a6"]

    for ax, model in zip(axes, models):
        dist = metrics[model]["error_distribution"]
        values = [dist.get(l, 0) for l in labels]
        if sum(values) == 0:
            ax.text(0.5, 0.5, "No errors", ha="center", va="center", transform=ax.transAxes)
        else:
            non_zero = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
            ax.pie(
                [v for _, v, _ in non_zero],
                labels=[l for l, _, _ in non_zero],
                colors=[c for _, _, c in non_zero],
                autopct="%1.0f%%",
                startangle=90,
            )
        ax.set_title(model)

    plt.suptitle("Error Distribution by Model")
    plt.tight_layout()
    plt.savefig(ANALYSIS_DIR / "error_distribution.png", dpi=150)
    plt.close()
    print(f"Saved: {ANALYSIS_DIR / 'error_distribution.png'}")


def save_metrics_json(metrics: dict, run_id: str) -> None:
    """Save metrics as JSON for further analysis."""
    path = ANALYSIS_DIR / f"metrics_{run_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"Saved: {path}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_results.py results/<run_id>.json")
        sys.exit(1)

    results_path = Path(sys.argv[1])
    if not results_path.exists():
        print(f"File not found: {results_path}")
        sys.exit(1)

    data = load_json(results_path)
    test_cases = load_test_cases()
    results = data["results"]
    run_id = data["metadata"]["run_id"]

    print(f"Analyzing {len(results)} results from run {run_id}...")

    metrics = compute_metrics(results, test_cases)
    print_summary_table(metrics)

    generate_heatmap(results, test_cases)
    generate_bar_chart(metrics)
    generate_error_pies(metrics)
    save_metrics_json(metrics, run_id)

    print("\nAnalysis complete!")


if __name__ == "__main__":
    main()
