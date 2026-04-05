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
