"""L2 一次性迁移：给已有的 problems 表补上 AI 单选题字段。

create_all 只建新表、不会给已存在的表加列，所以线上库需要手动跑一次本脚本。
重复执行安全：已存在的列会跳过。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text

from app import engine

COLUMNS = [
    ('type', "VARCHAR(16) DEFAULT 'single'"),
    ('options', 'TEXT'),
    ('answer', 'VARCHAR(8)'),
    ('explanation', 'TEXT'),
    ('difficulty', 'INTEGER DEFAULT 3'),
]


def main() -> int:
    inspector = inspect(engine)
    if 'problems' not in inspector.get_table_names():
        print('problems 表不存在，先启动一次后端让 create_all 建表')
        return 1

    existing = {column['name'] for column in inspector.get_columns('problems')}
    with engine.begin() as connection:
        for name, ddl in COLUMNS:
            if name in existing:
                print(f'跳过 {name}：已存在')
                continue
            connection.execute(text(f'ALTER TABLE problems ADD COLUMN `{name}` {ddl}'))
            print(f'已添加 {name}')

    print('迁移完成，当前列：', ', '.join(sorted(
        column['name'] for column in inspect(engine).get_columns('problems')
    )))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
