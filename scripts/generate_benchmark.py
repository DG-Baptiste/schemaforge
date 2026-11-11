"""Generate a deterministic 500–2000-record vacancy benchmark JSONL file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--out", type=Path, default=Path("data/vacancies_500.jsonl"))
    args = parser.parse_args()
    if not 500 <= args.count <= 2000:
        parser.error("--count must be between 500 and 2000")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as stream:
        for index in range(1, args.count + 1):
            row = {
                "id": f"job-{index:04d}",
                "text": (
                    f"Ищем Python-разработчика #{index} в ООО Альфа. "
                    f"Зарплата от {150000 + index} RUB. Навыки: Python, SQL."
                ),
            }
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
