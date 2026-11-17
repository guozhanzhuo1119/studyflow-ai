"""给现有 problems / variants 表补 content 列，保留已有数据不重建表"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import engine
from sqlalchemy import text

UPLOADS_DIR = Path(__file__).resolve().parent.parent / 'uploads'
UPLOADS_DIR.mkdir(exist_ok=True)
print(f'上传目录已就绪：{UPLOADS_DIR}')


def has_column(conn, table: str, col: str) -> bool:
    row = conn.execute(text(
        "SELECT COUNT(*) AS n FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {'t': table, 'c': col}).fetchone()
    return row.n > 0


with engine.begin() as conn:
    for table in ('problems', 'variants'):
        if has_column(conn, table, 'content'):
            print(f'{table}.content 已存在，跳过')
        else:
            conn.execute(text(
                f"ALTER TABLE {table} ADD COLUMN content TEXT NULL COMMENT '题目正文 Markdown，可嵌入图片'"
            ))
            print(f'已添加 {table}.content')

print('完成')
