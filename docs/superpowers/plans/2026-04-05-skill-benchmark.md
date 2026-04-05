# Skill Benchmark — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать воспроизводимый бенчмарк для кроссмодельного тестирования AI-скилла `incoming-request-handler` на 4 моделях через OpenRouter.

**Architecture:** Python-скрипт прогоняет 10 тестовых обращений через OpenRouter API (OpenAI-совместимый формат) с multi-step tool calling loop. Моки фиксируют ответы инструментов. Отдельный скрипт анализирует результаты и генерирует метрики + визуализации.

**Tech Stack:** Python 3.11+, openai SDK, python-dotenv, matplotlib (анализ)

---

## Структура файлов

```
test_skill/
├── SKILL.md                        # Скилл (уже есть)
├── experiment-plan.md              # План эксперимента (уже есть)
├── tools/
│   └── tool_definitions.json       # OpenAI function calling definitions
├── mocks/
│   └── tool_responses.json         # Фиксированные ответы инструментов
├── tests/
│   └── test_cases.json             # 10 обращений с эталонами
├── scripts/
│   ├── run_benchmark.py            # Прогон бенчмарка
│   └── analyze_results.py          # Анализ результатов + визуализации
├── results/                        # Сырые результаты (генерируется)
├── analysis/                       # Графики и таблицы (генерируется)
├── .env                            # OPENROUTER_API_KEY (не коммитить)
├── .gitignore
├── requirements.txt
└── README.md
```

**Ответственность каждого файла:**

| Файл | Что делает |
|------|-----------|
| `tools/tool_definitions.json` | Описание 3 инструментов в формате OpenAI function calling |
| `mocks/tool_responses.json` | Детерминированные ответы инструментов для каждого тест-кейса |
| `tests/test_cases.json` | 10 обращений + эталоны: ожидаемый тип, приоритет, tool calls, проверки |
| `scripts/run_benchmark.py` | Multi-step tool calling loop через OpenRouter. Один файл, ~250 строк |
| `scripts/analyze_results.py` | Расчёт 8 метрик, классификация ошибок, генерация таблиц и графиков |

---

## Учтённые замечания

1. **Обращение 10** — убран `create_task` из мока. Оставлен только `classify_issue`.
2. **`analyze_results.py`** — добавлен в структуру как отдельный скрипт анализа.
3. **Обращение 8 (две проблемы)** — мок возвращает одинаковый ответ при любом вызове `create_task`. Скрипт поддерживает множественные вызовы одного инструмента.
4. **`keywords` формат** — оставлен как `string` (так в SKILL.md: "2-4 ключевых слова через запятую"). Анализ не будет штрафовать за формат keywords, только за факт вызова.

---

### Task 1: Инициализация проекта

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `.env.example`

- [ ] **Step 1: Инициализировать git-репозиторий**

Run: `cd /home/alex2061/projects/test_skill && git init`

- [ ] **Step 2: Создать .gitignore**

```
.env
results/
analysis/
__pycache__/
*.pyc
.venv/
```

- [ ] **Step 3: Создать requirements.txt**

```
openai>=1.0.0
python-dotenv>=1.0.0
matplotlib>=3.8.0
```

- [ ] **Step 4: Создать .env.example**

```
OPENROUTER_API_KEY=sk-or-...your-key-here
```

- [ ] **Step 5: Создать директории**

```bash
mkdir -p tools mocks tests scripts results analysis
```

- [ ] **Step 6: Установить зависимости**

```bash
pip install -r requirements.txt
```

- [ ] **Step 7: Commit**

```bash
git add .gitignore requirements.txt .env.example SKILL.md experiment-plan.md
git commit -m "chore: init project structure"
```

---

### Task 2: Tool Definitions

**Files:**
- Create: `tools/tool_definitions.json`

- [ ] **Step 1: Создать tool_definitions.json**

```json
[
  {
    "type": "function",
    "function": {
      "name": "classify_issue",
      "description": "Определяет тип обращения пользователя",
      "parameters": {
        "type": "object",
        "properties": {
          "description": {
            "type": "string",
            "description": "Полный текст обращения пользователя"
          }
        },
        "required": ["description"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "search_duplicates",
      "description": "Ищет похожие тикеты в базе по ключевым словам",
      "parameters": {
        "type": "object",
        "properties": {
          "keywords": {
            "type": "string",
            "description": "2-4 ключевых слова через запятую"
          }
        },
        "required": ["keywords"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "create_task",
      "description": "Создаёт задачу в трекере",
      "parameters": {
        "type": "object",
        "properties": {
          "title": {
            "type": "string",
            "description": "Краткое название задачи (5-10 слов)"
          },
          "type": {
            "type": "string",
            "enum": ["bug", "feature_request", "complaint"],
            "description": "Тип задачи"
          },
          "priority": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low"],
            "description": "Приоритет задачи"
          },
          "description": {
            "type": "string",
            "description": "Подробное описание задачи"
          },
          "duplicate_ids": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "ID похожих тикетов из search_duplicates, если найдены"
          }
        },
        "required": ["title", "type", "priority", "description"]
      }
    }
  }
]
```

- [ ] **Step 2: Проверить валидность JSON**

```bash
python3 -c "import json; json.load(open('tools/tool_definitions.json')); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add tools/tool_definitions.json
git commit -m "feat: add tool definitions (OpenAI function calling format)"
```

---

### Task 3: Моки инструментов

**Files:**
- Create: `mocks/tool_responses.json`

Ключевые решения:
- Мок для кейса 8 — `create_task` возвращает один и тот же ответ при повторных вызовах (скрипт вызовет мок дважды).
- Кейс 10 — нет `create_task` в моке (в идеале модель не должна его вызывать; если вызовет — скрипт вернёт fallback-ответ и зафиксирует лишний вызов).
- Каждый мок привязан к номеру test_case, не к параметрам вызова.

- [ ] **Step 1: Создать tool_responses.json**

```json
{
  "1": {
    "classify_issue": {"type": "bug"},
    "search_duplicates": {"results": []},
    "create_task": {"id": 5001, "status": "created"}
  },
  "2": {
    "classify_issue": {"type": "feature_request"},
    "search_duplicates": {"results": []},
    "create_task": {"id": 5002, "status": "created"}
  },
  "3": {
    "classify_issue": {"type": "bug"},
    "search_duplicates": {"results": [{"id": 4890, "title": "Кнопка сохранения не работает в Safari"}]},
    "create_task": {"id": 5003, "status": "created"}
  },
  "4": {
    "classify_issue": {"type": "bug"},
    "search_duplicates": {"results": []},
    "create_task": {"id": 5004, "status": "created"}
  },
  "5": {
    "classify_issue": {"type": "feature_request"},
    "search_duplicates": {"results": [{"id": 4200, "title": "Интеграция с мессенджерами"}]},
    "create_task": {"id": 5005, "status": "created"}
  },
  "6": {
    "classify_issue": {"type": "bug"},
    "search_duplicates": {"results": []},
    "create_task": {"id": 5006, "status": "created"}
  },
  "7": {
    "classify_issue": {"type": "bug"},
    "search_duplicates": {"results": [{"id": 4519, "title": "Массовая проблема авторизации"}]},
    "create_task": {"id": 5007, "status": "created"}
  },
  "8": {
    "classify_issue": {"type": "bug"},
    "search_duplicates": {"results": []},
    "create_task": {"id": 5008, "status": "created"}
  },
  "9": {
    "classify_issue": {"type": "question"},
    "search_duplicates": {"results": []}
  },
  "10": {
    "classify_issue": {"type": "question"},
    "search_duplicates": {"results": []}
  },
  "_fallback": {
    "classify_issue": {"type": "unknown"},
    "search_duplicates": {"results": []},
    "create_task": {"id": 9999, "status": "created"}
  }
}
```

Примечания:
- Кейсы 9, 10 — нет `create_task` в моке. Если модель его вызовет, скрипт использует `_fallback`.
- `_fallback` — запасной ответ для любого незапланированного вызова (логируется как аномалия).

- [ ] **Step 2: Проверить валидность JSON**

```bash
python3 -c "import json; json.load(open('mocks/tool_responses.json')); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add mocks/tool_responses.json
git commit -m "feat: add mock tool responses for all 10 test cases"
```

---

### Task 4: Тестовые обращения с эталонами

**Files:**
- Create: `tests/test_cases.json`

Каждый тест-кейс содержит:
- `text` — текст обращения
- `level` — уровень сложности (1-4)
- `expected_type` — ожидаемый тип (или `null` если классификация не требуется)
- `allowed_priorities` — допустимые приоритеты (массив)
- `expected_tool_sequence` — ожидаемая последовательность вызовов
- `expected_duplicate_ids` — ожидаемые ID дубликатов в create_task
- `expect_no_create_task` — true если create_task НЕ должен быть вызван
- `expect_multi_issue` — true если обращение содержит несколько проблем
- `notes` — описание ловушки или особенности
- `repeats` — количество повторов (20 для ключевых, 5 для остальных)

- [ ] **Step 1: Создать test_cases.json**

```json
[
  {
    "id": 1,
    "level": 1,
    "text": "У нас не работает оплата картой на сайте. Клиенты жалуются, заказы не проходят с утра.",
    "expected_type": "bug",
    "allowed_priorities": ["critical"],
    "expected_tool_sequence": ["classify_issue", "search_duplicates", "create_task"],
    "expected_duplicate_ids": [],
    "expect_no_create_task": false,
    "expect_multi_issue": false,
    "notes": "Прямой кейс: оплата не работает, массовая проблема → critical",
    "repeats": 20
  },
  {
    "id": 2,
    "level": 1,
    "text": "Хотелось бы добавить возможность экспорта отчётов в PDF.",
    "expected_type": "feature_request",
    "allowed_priorities": ["medium", "low"],
    "expected_tool_sequence": ["classify_issue", "search_duplicates", "create_task"],
    "expected_duplicate_ids": [],
    "expect_no_create_task": false,
    "expect_multi_issue": false,
    "notes": "Прямой кейс: запрос фичи",
    "repeats": 5
  },
  {
    "id": 3,
    "level": 1,
    "text": "При нажатии на кнопку 'Сохранить' в профиле ничего не происходит, страница просто перезагружается.",
    "expected_type": "bug",
    "allowed_priorities": ["high", "medium"],
    "expected_tool_sequence": ["classify_issue", "search_duplicates", "create_task"],
    "expected_duplicate_ids": [4890],
    "expect_no_create_task": false,
    "expect_multi_issue": false,
    "notes": "Дубликат найден — модель должна указать duplicate_ids: [4890]",
    "repeats": 5
  },
  {
    "id": 4,
    "level": 2,
    "text": "Мы перешли на новый тариф, но в личном кабинете показывается старая цена. Деньги списались правильно.",
    "expected_type": "bug",
    "allowed_priorities": ["medium", "high"],
    "expected_tool_sequence": ["classify_issue", "search_duplicates", "create_task"],
    "expected_duplicate_ids": [],
    "expect_no_create_task": false,
    "expect_multi_issue": false,
    "notes": "Ловушка: слово 'деньги' но проблема визуальная → НЕ critical",
    "repeats": 5
  },
  {
    "id": 5,
    "level": 2,
    "text": "Ваш конкурент уже давно сделал интеграцию с Telegram. Когда вы сделаете?",
    "expected_type": "feature_request",
    "allowed_priorities": ["medium", "low"],
    "expected_tool_sequence": ["classify_issue", "search_duplicates", "create_task"],
    "expected_duplicate_ids": [4200],
    "expect_no_create_task": false,
    "expect_multi_issue": false,
    "notes": "Ловушка: раздражённый тон → но это feature_request, не complaint. Дубликат [4200]",
    "repeats": 20
  },
  {
    "id": 6,
    "level": 2,
    "text": "Каждый раз когда я загружаю файл больше 50 мб, система виснет на 2 минуты, а потом всё работает.",
    "expected_type": "bug",
    "allowed_priorities": ["medium", "high"],
    "expected_tool_sequence": ["classify_issue", "search_duplicates", "create_task"],
    "expected_duplicate_ids": [],
    "expect_no_create_task": false,
    "expect_multi_issue": false,
    "notes": "Ловушка: 'виснет' но система в итоге работает → НЕ critical",
    "repeats": 5
  },
  {
    "id": 7,
    "level": 3,
    "text": "Не могу войти в систему, пишет 'неверный пароль', хотя я его точно не менял. Коллега рядом тоже не может войти.",
    "expected_type": "bug",
    "allowed_priorities": ["critical"],
    "expected_tool_sequence": ["classify_issue", "search_duplicates", "create_task"],
    "expected_duplicate_ids": [4519],
    "expect_no_create_task": false,
    "expect_multi_issue": false,
    "notes": "Массовая проблема авторизации → critical. Дубликат [4519]",
    "repeats": 20
  },
  {
    "id": 8,
    "level": 3,
    "text": "Мне третий раз за неделю приходит письмо о продлении подписки, хотя я уже продлил. Плюс в мобильном приложении кнопка 'Поддержка' ведёт на 404.",
    "expected_type": "bug",
    "allowed_priorities": ["medium", "high"],
    "expected_tool_sequence": ["classify_issue", "search_duplicates", "create_task", "create_task"],
    "expected_duplicate_ids": [],
    "expect_no_create_task": false,
    "expect_multi_issue": true,
    "notes": "Две разные проблемы — модель должна создать 2 задачи",
    "repeats": 5
  },
  {
    "id": 9,
    "level": 4,
    "text": "Подскажите, какие форматы файлов поддерживает ваша система для импорта?",
    "expected_type": "question",
    "allowed_priorities": [],
    "expected_tool_sequence": ["classify_issue", "search_duplicates"],
    "expected_duplicate_ids": [],
    "expect_no_create_task": true,
    "expect_multi_issue": false,
    "notes": "Вопрос → create_task НЕ должен вызываться",
    "repeats": 20
  },
  {
    "id": 10,
    "level": 4,
    "text": "Спасибо, всё заработало! Можете закрыть мой предыдущий тикет #4521.",
    "expected_type": null,
    "allowed_priorities": [],
    "expected_tool_sequence": [],
    "expected_duplicate_ids": [],
    "expect_no_create_task": true,
    "expect_multi_issue": false,
    "notes": "Благодарность + просьба закрыть тикет. create_task НЕ вызывать. Сообщить что close_task недоступен",
    "repeats": 5
  }
]
```

- [ ] **Step 2: Проверить валидность JSON и количество кейсов**

```bash
python3 -c "
import json
cases = json.load(open('tests/test_cases.json'))
print(f'Total cases: {len(cases)}')
total = sum(c['repeats'] for c in cases)
print(f'Total runs per model: {total}')
print(f'Total runs (4 models): {total * 4}')
"
```

Expected:
```
Total cases: 10
Total runs per model: 110
Total runs (4 models): 440
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_cases.json
git commit -m "feat: add 10 test cases with expectations (4 difficulty levels)"
```

---

### Task 5: Скрипт прогона бенчмарка

**Files:**
- Create: `scripts/run_benchmark.py`

Требования:
- Максимально простой, без абстракций
- Multi-step tool calling loop (макс 10 циклов)
- Моки по номеру test_case, fallback для незапланированных вызовов
- Поддержка множественных вызовов одного инструмента (кейс 8)
- Baseline-режим (без SKILL.md в system prompt)
- Результаты в JSON (один файл на прогон)
- Прогресс в stdout

- [ ] **Step 1: Создать run_benchmark.py**

```python
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
    "openai/gpt-4o",
    "google/gemini-2.5-pro",
    "deepseek/deepseek-chat",
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
```

- [ ] **Step 2: Проверить синтаксис**

```bash
python3 -c "import py_compile; py_compile.compile('scripts/run_benchmark.py', doraise=True); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Проверить --help**

```bash
python3 scripts/run_benchmark.py --help
```

Expected: вывод справки с описанием аргументов.

- [ ] **Step 4: Commit**

```bash
git add scripts/run_benchmark.py
git commit -m "feat: add benchmark runner with multi-step tool calling loop"
```

---

### Task 6: Скрипт анализа результатов

**Files:**
- Create: `scripts/analyze_results.py`

Метрики из плана:
1. Success rate (полностью правильный прогон)
2. Tool sequence accuracy
3. Classification accuracy
4. Priority accuracy
5. Restraint score (правильные НЕвызовы create_task)
6. Run-to-run consistency
7. Duplicate handling
8. Multi-issue detection

Классификация ошибок: A-F (6 типов).

- [ ] **Step 1: Создать analyze_results.py**

```python
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
        # Could be missing step or reorder
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
```

- [ ] **Step 2: Проверить синтаксис**

```bash
python3 -c "import py_compile; py_compile.compile('scripts/analyze_results.py', doraise=True); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/analyze_results.py
git commit -m "feat: add results analyzer with metrics, error classification, and charts"
```

---

### Task 7: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Создать README.md**

```markdown
# Skill Benchmark: Cross-Model AI Skill Testing

Воспроизводимый эксперимент: как один и тот же AI-скилл работает на разных моделях.

## Что тестируем

Скилл `incoming-request-handler` обрабатывает входящие обращения пользователей: классифицирует, ищет дубликаты, определяет приоритет, создаёт задачу.

10 тестовых обращений, 4 уровня сложности, 4 модели.

## Модели

| Модель | OpenRouter ID |
|--------|--------------|
| Claude Sonnet 4.6 | `anthropic/claude-sonnet-4-6` |
| GPT-4o | `openai/gpt-4o` |
| Gemini 2.5 Pro | `google/gemini-2.5-pro` |
| DeepSeek V3 | `deepseek/deepseek-chat` |

## Быстрый старт

```bash
# 1. Клонировать
git clone <repo-url> && cd skill-benchmark

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Настроить API-ключ
cp .env.example .env
# Вписать OPENROUTER_API_KEY в .env

# 4. Прогнать бенчмарк (все модели, все кейсы)
python scripts/run_benchmark.py

# 5. Прогнать baseline (без скилла)
python scripts/run_benchmark.py --baseline --cases 1,5,7,9 --repeats-override 5

# 6. Анализ результатов
python scripts/analyze_results.py results/<run_id>.json
```

## Опции run_benchmark.py

| Флаг | Описание |
|------|----------|
| `--baseline` | Без SKILL.md в system prompt |
| `--models M1,M2` | Только указанные модели |
| `--cases 1,5,7` | Только указанные тест-кейсы |
| `--repeats-override N` | Переопределить количество повторов |

## Метрики

- **Success rate** — % полностью правильных прогонов
- **Tool sequence accuracy** — правильный порядок вызовов
- **Classification / Priority accuracy** — правильный тип и приоритет
- **Restraint score** — правильные НЕвызовы create_task
- **Run-to-run consistency** — стабильность при повторах
- **Duplicate handling** — правильные duplicate_ids
- **Multi-issue detection** — распознавание нескольких проблем

## Структура

```
├── SKILL.md                  # Тестируемый скилл
├── tools/tool_definitions.json   # Описания инструментов
├── mocks/tool_responses.json     # Фиксированные ответы
├── tests/test_cases.json         # 10 обращений с эталонами
├── scripts/run_benchmark.py      # Прогон
├── scripts/analyze_results.py    # Анализ
├── results/                      # Сырые результаты
└── analysis/                     # Графики и метрики
```

## Лицензия

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with quick start and metrics description"
```

---

### Task 8: Dry Run — проверка полного пайплайна

**Files:** нет новых файлов

- [ ] **Step 1: Создать .env с ключом**

Вручную: скопировать `.env.example` в `.env` и вписать ключ OpenRouter.

```bash
cp .env.example .env
# Вписать ключ вручную
```

- [ ] **Step 2: Smoke test — один кейс, одна модель, один повтор**

```bash
python3 scripts/run_benchmark.py --models deepseek/deepseek-chat --cases 1 --repeats-override 1
```

Expected: файл в `results/` с одним результатом, tool_calls содержит classify_issue, search_duplicates, create_task.

- [ ] **Step 3: Проверить структуру результата**

```bash
python3 -c "
import json
from pathlib import Path
results_dir = Path('results')
latest = sorted(results_dir.glob('*.json'))[-1]
data = json.load(open(latest))
r = data['results'][0]
print(f'Model: {r[\"model\"]}')
print(f'Case: {r[\"test_case\"]}')
print(f'Tools: {[tc[\"name\"] for tc in r[\"tool_calls\"]]}')
print(f'Tokens: {r[\"total_tokens\"]}')
print(f'Latency: {r[\"latency_ms\"]}ms')
"
```

- [ ] **Step 4: Smoke test анализа**

```bash
python3 scripts/analyze_results.py results/$(ls results/ | sort | tail -1)
```

Expected: таблица метрик в stdout, файлы в `analysis/` (heatmap.png, success_by_level.png, error_distribution.png, metrics JSON).

- [ ] **Step 5: Проверить графики**

```bash
ls -la analysis/
```

Expected: 4 файла (3 PNG + 1 JSON).

- [ ] **Step 6: Финальный commit**

```bash
git add -A
git commit -m "chore: verify pipeline works end-to-end"
```

---

### Task 9: Полный прогон эксперимента

**Files:** нет новых файлов

- [ ] **Step 1: Прогон baseline**

```bash
python3 scripts/run_benchmark.py --baseline --cases 1,5,7,9 --repeats-override 5
```

Expected: ~20 запусков (4 кейса × 5 повторов) на каждую из 4 моделей = 80 запусков.

- [ ] **Step 2: Основной прогон**

```bash
python3 scripts/run_benchmark.py
```

Expected: 440 запусков (110 на модель). Время: ~1-2 часа.

- [ ] **Step 3: Анализ baseline**

```bash
python3 scripts/analyze_results.py results/<baseline_run_id>.json
```

- [ ] **Step 4: Анализ основного прогона**

```bash
python3 scripts/analyze_results.py results/<main_run_id>.json
```

- [ ] **Step 5: Сравнить baseline vs with_skill**

Вручную сопоставить метрики из двух JSON в `analysis/`. Если разница success rate < 10% — скилл не оправдывает себя.

- [ ] **Step 6: Commit результатов**

```bash
git add results/ analysis/
git commit -m "data: add benchmark results and analysis"
```
