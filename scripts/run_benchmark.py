"""
Skill Benchmark Runner
Прогоняет тестовые обращения через модели via OpenRouter.
Использование: python scripts/run_benchmark.py [--baseline] [--models MODEL1,MODEL2] [--cases 1,5,7]
"""

import json
import os
import sys
import time
import hashlib
import argparse
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

MODELS = [
    "anthropic/claude-sonnet-4-6",
    "openai/gpt-4.1",
    "google/gemini-2.5-pro",
    "deepseek/deepseek-chat-v3-0324",
]

MAX_TOOL_CYCLES = 10


def load_json(path: Path) -> dict | list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_mock_response(
    mocks: dict, test_case_id: str, tool_name: str
) -> dict:
    """Return mock response for a tool call. Falls back to _fallback."""
    case_mocks = mocks.get(test_case_id, mocks.get("_fallback", {}))
    if tool_name in case_mocks:
        return case_mocks[tool_name]
    fallback = mocks.get("_fallback", {})
    return fallback.get(tool_name, {"error": "unknown tool"})


def run_single(
    client: OpenAI,
    model: str,
    system_prompt: str,
    tools: list[dict],
    user_message: str,
    mocks: dict,
    test_case_id: str,
) -> dict:
    """Run one test case through the model. Returns full log."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    tool_calls_log: list[dict] = []
    final_text = ""
    total_tokens = 0
    order = 0
    used_fallback = False

    start_time = time.monotonic()

    for cycle in range(MAX_TOOL_CYCLES):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools if tools else None,
                temperature=0,
                max_tokens=4096,
            )
        except Exception as e:
            return {
                "error": str(e),
                "tool_calls": tool_calls_log,
                "final_text": "",
                "total_tokens": total_tokens,
                "latency_ms": int((time.monotonic() - start_time) * 1000),
                "cycles": cycle + 1,
                "used_fallback": used_fallback,
            }

        choice = response.choices[0]
        if response.usage:
            total_tokens += response.usage.total_tokens

        # Model finished with text
        if choice.finish_reason == "stop" or not choice.message.tool_calls:
            final_text = choice.message.content or ""
            messages.append(choice.message)
            break

        # Model wants to call tools
        messages.append(choice.message)
        for tc in choice.message.tool_calls:
            order += 1
            params = json.loads(tc.function.arguments)
            mock_resp = get_mock_response(mocks, test_case_id, tc.function.name)

            # Track if we used fallback
            case_mocks = mocks.get(test_case_id, {})
            if tc.function.name not in case_mocks:
                used_fallback = True

            tool_calls_log.append({
                "name": tc.function.name,
                "params": params,
                "order": order,
                "mock_response": mock_resp,
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(mock_resp, ensure_ascii=False),
            })
    else:
        final_text = "[MAX_CYCLES_REACHED]"

    latency_ms = int((time.monotonic() - start_time) * 1000)

    return {
        "tool_calls": tool_calls_log,
        "final_text": final_text,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
        "cycles": cycle + 1,
        "used_fallback": used_fallback,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Skill Benchmark Runner")
    parser.add_argument(
        "--baseline", action="store_true",
        help="Run without SKILL.md (baseline mode)",
    )
    parser.add_argument(
        "--models", type=str, default=None,
        help="Comma-separated model IDs (default: all 4)",
    )
    parser.add_argument(
        "--cases", type=str, default=None,
        help="Comma-separated test case IDs (default: all)",
    )
    parser.add_argument(
        "--repeats-override", type=int, default=None,
        help="Override repeat count for all cases",
    )
    args = parser.parse_args()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set in .env")
        sys.exit(1)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    # Load data
    skill_path = BASE_DIR / "SKILL.md"
    skill_content = skill_path.read_text(encoding="utf-8") if not args.baseline else ""
    tools = load_json(BASE_DIR / "tools" / "tool_definitions.json")
    mocks = load_json(BASE_DIR / "mocks" / "tool_responses.json")
    test_cases = load_json(BASE_DIR / "tests" / "test_cases.json")

    # Filter models and cases
    models = args.models.split(",") if args.models else MODELS
    if args.cases:
        case_ids = set(int(x) for x in args.cases.split(","))
        test_cases = [tc for tc in test_cases if tc["id"] in case_ids]

    # Metadata
    mode = "baseline" if args.baseline else "with_skill"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + f"_{mode}"
    metadata = {
        "run_id": run_id,
        "mode": mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "skill_sha256": sha256_file(skill_path) if not args.baseline else None,
        "models": models,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

    all_results: list[dict] = []
    total_runs = sum(
        (args.repeats_override or tc["repeats"]) * len(models)
        for tc in test_cases
    )
    current_run = 0

    for model in models:
        for tc in test_cases:
            repeats = args.repeats_override or tc["repeats"]
            for run_num in range(1, repeats + 1):
                current_run += 1
                case_id = tc["id"]
                print(
                    f"[{current_run}/{total_runs}] "
                    f"model={model.split('/')[-1]} "
                    f"case={case_id} run={run_num}/{repeats}",
                    flush=True,
                )

                result = run_single(
                    client=client,
                    model=model,
                    system_prompt=skill_content,
                    tools=tools,
                    user_message=tc["text"],
                    mocks=mocks,
                    test_case_id=str(case_id),
                )

                all_results.append({
                    "model": model,
                    "test_case": case_id,
                    "run": run_num,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **result,
                })

    # Save results
    output = {"metadata": metadata, "results": all_results}
    output_path = RESULTS_DIR / f"{run_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone! {len(all_results)} runs saved to {output_path}")


if __name__ == "__main__":
    main()
