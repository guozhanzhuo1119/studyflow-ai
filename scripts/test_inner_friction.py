"""测试「切断内耗 + 业务落地动作」工具。

两条路径都跑一遍：
1. 直接调用工具：验证 DEFUSE_PROMPT 本身的效果
2. 走完整 Agent：验证模型会不会主动选中这个工具

运行：在项目根目录执行 python scripts/test_inner_friction.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.agent.analyzer import run_agent
from app.agent.tools import interrupt_inner_friction

QUESTION = (
    '我最近真的不知道该怎么办，感觉学Java和AI都没什么用，'
    '我到底还要不要继续学下去，我以后能干嘛？'
)

# 期望出现的“具体业务动作”关键词，命中任意一个就算通过
ACTION_KEYWORDS = ('JD', '岗位', '招聘', '报录比', '错题', '报错', '截图', '搜')


def check(label: str, reply: str) -> None:
    print(f'\n--- {label} ---\n{reply}\n')
    hit = next((kw for kw in ACTION_KEYWORDS if kw in reply), None)
    if hit:
        print(f'[通过] 包含具体业务动作关键词：{hit}')
    else:
        print('[未通过] 回复里没有具体业务动作，只有情绪安抚')


def main() -> None:
    print('=' * 70)
    print('测试 1：直接调用 interrupt_inner_friction（只验证 prompt）')
    print('=' * 70)
    reply = interrupt_inner_friction.invoke({'user_confusion': QUESTION})
    check('工具原始返回', reply)

    print('\n' + '=' * 70)
    print('测试 2：走完整 Agent（验证模型会不会选中该工具）')
    print('=' * 70)
    reply = run_agent(QUESTION)
    check('Agent 回复', reply)


if __name__ == '__main__':
    main()
