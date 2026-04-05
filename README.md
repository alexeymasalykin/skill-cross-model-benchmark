# Skill Cross-Model Benchmark

Кроссмодельный бенчмарк одного AI-скилла на четырёх моделях. Воспроизводимый эксперимент с открытыми данными.

## Зачем

Скиллы для AI-агентов пишутся под одну модель и никогда не тестируются на других. Мы проверили: один скилл, четыре модели, три уровня инструкций, 640 API-вызовов.

## Модели

| Модель | OpenRouter ID | Цена (input/M) |
|--------|--------------|-----------------|
| Claude Sonnet 4.6 | `anthropic/claude-sonnet-4-6` | ~$3 |
| GPT-4.1 | `openai/gpt-4.1` | ~$2 |
| Gemini 2.5 Pro | `google/gemini-2.5-pro` | ~$2.50 |
| DeepSeek V3.2 | `deepseek/deepseek-chat-v3-0324` | ~$0.25-0.55 |

## Три уровня

| Уровень | System prompt | Что проверяем |
|---------|--------------|---------------|
| **Baseline** | Нет | Модель + tools, без инструкций |
| **Простой промпт** | 3 предложения ([текст](prompts/simple_prompt.txt)) | Задача на человеческом языке |
| **Скилл** | Структурированный документ ([SKILL.md](skill/SKILL.md)) | Правила, таблицы, порядок действий |

## Результаты

| | Claude Sonnet 4.6 | GPT-4.1 | Gemini 2.5 Pro | DeepSeek V3.2 |
|--|:-:|:-:|:-:|:-:|
| Без промпта | 75% | 55% | 15% | 5% |
| Простой промпт | 65% | 75% | 70% | 0% |
| **Скилл** | **77.5%** | **77.5%** | **72.5%** | **61.7%** |

**Ключевые выводы:**

- Простой промпт даёт основной рост для GPT-4.1 и Gemini (+20% и +55%). Скилл добавляет лишь +2.5% сверху
- Claude парадоксально хуже с простым промптом (-10%), но лучше со скиллом
- DeepSeek — главный бенефициар скилла: простой промпт дал 0%, скилл поднял до 61.7%
- Скилл больше всего помогает слабым моделям. Сильные справляются и без него

<!-- Ссылка на статью: TODO -->

## Как запустить

```bash
# Установить зависимости
pip install -r scripts/requirements.txt

# Настроить API-ключ
cp .env.example .env
# Вписать OPENROUTER_API_KEY в .env

# Прогнать со скиллом (все модели, все кейсы)
python scripts/run_benchmark.py

# Прогнать baseline (без system prompt)
python scripts/run_benchmark.py --baseline --cases 1,5,7,9 --repeats-override 5

# Прогнать с простым промптом
python scripts/run_benchmark.py \
  --system-prompt "$(cat prompts/simple_prompt.txt)" \
  --mode-label simple_prompt \
  --cases 1,5,7,9 --repeats-override 5

# Посчитать метрики
python scripts/calculate_metrics.py results/raw/<файл>.json
```

## Опции run_benchmark.py

| Флаг | Описание |
|------|----------|
| `--baseline` | Без system prompt |
| `--system-prompt TEXT` | Произвольный system prompt |
| `--mode-label NAME` | Метка прогона (в имени файла) |
| `--models M1,M2` | Только указанные модели |
| `--cases 1,5,7` | Только указанные тест-кейсы |
| `--repeats-override N` | Переопределить количество повторов |

## Метрики

- **Success rate** — % полностью правильных прогонов (тип + приоритет + tool calls)
- **Tool sequence accuracy** — правильный порядок вызовов инструментов
- **Classification / Priority accuracy** — правильный тип и приоритет
- **Restraint score** — правильные НЕвызовы create_task на вопросах
- **Run-to-run consistency** — стабильность при повторных запусках
- **Duplicate handling** — правильные duplicate_ids
- **Multi-issue detection** — распознавание нескольких проблем в одном обращении

## Структура

```
├── skill/SKILL.md                    # Тестируемый скилл
├── tools/tool_definitions.json       # Описания инструментов (OpenAI format)
├── mocks/tool_responses.json         # Фиксированные ответы инструментов
├── tests/test_cases.json             # 10 обращений с эталонами
├── prompts/
│   ├── simple_prompt.txt             # Простой промпт (3 предложения)
│   └── baseline_note.txt             # Пояснение про baseline
├── scripts/
│   ├── run_benchmark.py              # Прогон бенчмарка
│   ├── calculate_metrics.py          # Расчёт метрик и графики
│   └── requirements.txt              # Зависимости
├── results/
│   ├── raw/                          # Сырые данные прогонов
│   └── metrics/                      # Рассчитанные метрики
├── charts/                           # Графики
└── .env.example                      # Шаблон API-ключа
```

## Лицензия

MIT — форкайте и прогоняйте на своих моделях.
