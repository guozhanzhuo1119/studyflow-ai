"""一次性脚本：清空旧的两层结构（categories -> problems），重建五层表

用法：
    python scripts/reset_hierarchy.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app import engine
from app.models.problem import Base
from app.rag.vector_store import INDEX_PATH, META_PATH

# 先删子表再删父表
DROP_ORDER = [
    'variants',
    'problems',
    'knowledge_points',
    'chapters',
    'subjects',
    'categories',
]


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text('SET FOREIGN_KEY_CHECKS = 0'))
        for table in DROP_ORDER:
            conn.execute(text(f'DROP TABLE IF EXISTS {table}'))
            print(f'已删除表 {table}')
        conn.execute(text('SET FOREIGN_KEY_CHECKS = 1'))

    Base.metadata.create_all(bind=engine)
    print('已重建表：', ', '.join(sorted(Base.metadata.tables)))

    for path in (INDEX_PATH, META_PATH):
        if path.exists():
            path.unlink()
            print(f'已删除索引文件 {path.name}')

    print('完成')


if __name__ == '__main__':
    main()
