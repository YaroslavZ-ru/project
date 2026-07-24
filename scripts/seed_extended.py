"""scripts/seed_extended.py -- импорт расширенного набора понятий в БД."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

API_URL = "http://localhost:8000/v1/save_concept"


def seed():
    data_path = Path(__file__).parent.parent / "data" / "extended_seed.json"
    if not data_path.exists():
        print(f"Файл не найден: {data_path}")
        return

    with open(data_path, encoding="utf-8") as f:
        concepts = json.load(f)

    print(f"Загружено {len(concepts)} понятий из {data_path.name}")
    print()

    success = 0
    errors = 0

    for i, concept in enumerate(concepts, 1):
        term = concept["term"]
        domain = concept["domain"]
        params = concept.get("parameters", [])

        try:
            r = httpx.post(API_URL, json={
                "term": term,
                "domain": domain,
                "parameters": params,
            }, timeout=10)

            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "ok":
                    print(f"[{i:2d}] OK: {term} ({domain})")
                    success += 1
                else:
                    print(f"[{i:2d}] ОШИБКА: {term} - {data}")
                    errors += 1
            else:
                print(f"[{i:2d}] HTTP {r.status_code}: {term}")
                errors += 1

        except Exception as e:
            print(f"[{i:2d}] ИСКЛЮЧЕНИЕ: {term} - {e}")
            errors += 1

    print()
    print(f"Итого: {success} успешно, {errors} ошибок")


if __name__ == "__main__":
    seed()
