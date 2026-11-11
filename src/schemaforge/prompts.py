"""Prompt templates and few-shot examples for structured extraction."""

from __future__ import annotations

import json
from typing import Any

FEW_SHOT_EXAMPLES: list[tuple[str, dict[str, Any]]] = [
    (
        "Ищем Python-разработчика в ООО Альфа. Зарплата от 180000 до 240000 RUB.",
        {
            "title": "Python-разработчик",
            "company": "ООО Альфа",
            "salary_min": 180000,
            "salary_max": 240000,
            "currency": "RUB",
            "employment_type": "full_time",
            "published_at": None,
            "skills": ["Python"],
        },
    ),
]


def build_messages(
    text: str,
    schema: dict[str, Any],
    mode: str = "schema",
    few_shot: bool = True,
) -> list[dict[str, str]]:
    """Build a provider-neutral extraction prompt."""
    system = (
        "Извлеки только факты из текста вакансии. Верни один JSON-объект. "
        "Не придумывай значения. Если данных нет, используй null или пустой список, "
        "если это разрешено схемой. Даты пиши в ISO-формате YYYY-MM-DD."
    )
    if mode == "free":
        system += " Верни JSON без дополнительных пояснений."
    elif mode == "json":
        system += " Ответ должен быть синтаксически корректным JSON."
    elif mode == "grammar":
        system += " Ответ должен соответствовать грамматике GBNF."
    else:
        system += " Ответ должен точно соответствовать переданной JSON Schema."

    messages = [{"role": "system", "content": system}]
    if few_shot:
        for example_text, example_output in FEW_SHOT_EXAMPLES:
            messages.extend(
                [
                    {"role": "user", "content": example_text},
                    {
                        "role": "assistant",
                        "content": json.dumps(example_output, ensure_ascii=False),
                    },
                ]
            )
    messages.append(
        {
            "role": "user",
            "content": f"Текст вакансии:\n{text}\n\nJSON Schema:\n"
            f"{json.dumps(schema, ensure_ascii=False)}",
        }
    )
    return messages
