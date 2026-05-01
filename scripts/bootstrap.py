from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import sqlite3
from pathlib import Path

from backend.app.core.config import settings


def main() -> None:
    settings.ensure_directories()
    Path('data/seed').mkdir(parents=True, exist_ok=True)
    Path('runtime/outputs').mkdir(parents=True, exist_ok=True)
    Path('runtime/checkpoints').mkdir(parents=True, exist_ok=True)

    seed_path = Path('data/seed/capabilities.json')
    db_path = Path(settings.case_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(seed_path.read_text(encoding='utf-8'))

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute('DROP TABLE IF EXISTS capabilities')
    cursor.execute('DROP TABLE IF EXISTS certifications')
    cursor.execute('DROP TABLE IF EXISTS past_projects')
    cursor.execute('DROP TABLE IF EXISTS staff_capacity')

    cursor.execute(
        'CREATE TABLE capabilities (name TEXT, category TEXT, tags TEXT, evidence TEXT, owner TEXT)'
    )
    cursor.execute(
        'CREATE TABLE certifications (name TEXT, tags TEXT, valid_until TEXT)'
    )
    cursor.execute(
        'CREATE TABLE past_projects (name TEXT, tags TEXT, year INTEGER, value_lkr INTEGER)'
    )
    cursor.execute(
        'CREATE TABLE staff_capacity (role TEXT, availability_pct INTEGER, notes TEXT)'
    )

    cursor.executemany(
        'INSERT INTO capabilities VALUES (?, ?, ?, ?, ?)',
        [
            (
                item['name'],
                item['category'],
                json.dumps(item['tags']),
                item['evidence'],
                item['owner'],
            )
            for item in payload['capabilities']
        ],
    )
    cursor.executemany(
        'INSERT INTO certifications VALUES (?, ?, ?)',
        [
            (
                item['name'],
                json.dumps(item['tags']),
                item['valid_until'],
            )
            for item in payload['certifications']
        ],
    )
    cursor.executemany(
        'INSERT INTO past_projects VALUES (?, ?, ?, ?)',
        [
            (
                item['name'],
                json.dumps(item['tags']),
                item['year'],
                item['value_lkr'],
            )
            for item in payload['past_projects']
        ],
    )
    cursor.executemany(
        'INSERT INTO staff_capacity VALUES (?, ?, ?)',
        [
            (
                item['role'],
                item['availability_pct'],
                item['notes'],
            )
            for item in payload['staff_capacity']
        ],
    )
    connection.commit()
    connection.close()
    print(f'[OK] Seed database written to {db_path}')


if __name__ == '__main__':
    main()
