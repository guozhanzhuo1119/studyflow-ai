"""错因分析业务层：决策树问答、语言坑检测、统计口径、预置映射。

model 层已做白名单校验（ErrorType 枚举、DECOMPOSE 拆解句关键词、tag 仅 OPERATE 可填），
本层补：
  1) 决策树定义与步进（前端逐步问答，后端按回答推导 error_type）
  2) 语言坑关键词检测（OPERATE 类自动建议打 SYNTAX 标签）
  3) 统计口径聚合（四指标 + 模拟模式附加三指标）
  4) 预置 topicTemplates / commonBoundaryChecklist
"""

from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.error import (
    ERROR_TYPE_META,
    ErrorAnalysis,
    ErrorAnalysisOut,
    ErrorType,
    RemedyStatus,
)


# -------------------------------------------------------------------- 语言坑检测

# 与规格 5.4 的关键词表保持一致
SYNTAX_KEYWORDS = ['->', 'nullptr', 'size_t', 'segfault', '空指针', '越界', '未初始化']


def suggest_syntax_tag(specific_behavior: str) -> bool:
    """判断 specific_behavior 是否涉及语言坑，用于给前端一个「建议打 SYNTAX 标签」的提示。

    只做关键词命中，是建议不是强制，最终是否打标签由用户决定。
    """
    if not specific_behavior:
        return False
    lower = specific_behavior.lower()
    return any(kw.lower() in lower for kw in SYNTAX_KEYWORDS)


# -------------------------------------------------------------------- 决策树

# (step, question, 触发结论的回答, 结论类型, 否/未命中时去往的下一步)
# 规格 2 的箭头方向：
#   Q1/Q2 —— 回答「否」即命中
#   Q3~Q6 —— 回答「是」即命中
DECISION_TREE = [
    (1, '读完题，你知道要输出什么吗？', False, ErrorType.READ, 2),
    (2, '你知道该用什么方法/母题吗？', False, ErrorType.IDENTIFY, 3),
    (3, '你知道方法，但不知道怎么落到代码/具体改哪？', True, ErrorType.DECOMPOSE, 4),
    (4, '你知道怎么写，但写出来是错的？', True, ErrorType.OPERATE, 5),
    (5, '写对了，但漏了某种情况（空/单节点/头节点/进位等）？', True, ErrorType.BOUNDARY, 6),
    (6, '都对，但超时/超空间？', True, ErrorType.EFFICIENCY, None),
]

DECISION_STEPS_FOR_API = [
    {
        'step': step,
        'question': question,
        'result_if_match': result.value,
        'match_answer': trigger_answer,   # True=回答「是」命中；False=回答「否」命中
        'next_step': next_step,
    }
    for (step, question, trigger_answer, result, next_step) in DECISION_TREE
]


def apply_decision_tree(answers: List[bool]) -> ErrorType:
    """按一串 yes/no 回答推导 error_type。answers[i] 对应第 i+1 步的回答。

    规则：走到第一个命中即停，不再往下问。
    回答数量不足时，按已走到的位置取该步的结论类型兜底；
    全部走完仍未命中（6 题全「否」属于逻辑不可能）落到 EFFICIENCY。
    """
    tree = {step: (trigger, result, nxt) for (step, _, trigger, result, nxt) in DECISION_TREE}
    step = 1
    idx = 0

    while step is not None:
        trigger, result, next_step = tree[step]
        if idx >= len(answers):
            return result           # 回答不够，用当前步的结论兜底
        if answers[idx] == trigger:
            return result           # 命中，停止
        step = next_step            # 未命中，继续下一问
        idx += 1

    return ErrorType.EFFICIENCY


# -------------------------------------------------------------------- 预置映射

TOPIC_TEMPLATES: Dict[str, Dict[str, str]] = {
    '链表': {
        'LC-206': '三指针反转：prev/curr/nextTemp，先存后改',
        'LC-141': '快慢指针：循环条件 fast && fast->next',
        'LC-21': 'dummy + tail 合并：退出后整段挂剩余',
        'LC-160': '双指针换路：走完自己换到对方链表',
        'dummyDelete': '可能删头节点：dummy.next = head + prev 前驱删除',
    },
}

COMMON_BOUNDARY_CHECKLIST: Dict[str, List[str]] = {
    '链表': ['空链表', '单节点', '删头节点', '找中点后是否断开', '循环条件是否防空指针'],
}


def get_presets(topic: Optional[str] = None) -> dict:
    """返回预置映射，可按知识点过滤。"""
    if topic:
        return {
            'topic_templates': {topic: TOPIC_TEMPLATES.get(topic, {})},
            'common_boundary_checklist': {topic: COMMON_BOUNDARY_CHECKLIST.get(topic, [])},
        }
    return {
        'topic_templates': TOPIC_TEMPLATES,
        'common_boundary_checklist': COMMON_BOUNDARY_CHECKLIST,
    }


# -------------------------------------------------------------------- 统计口径

def build_statistics(db: Session, practice_mode: bool = True) -> dict:
    """练习模式只报四指标；模拟模式额外返回 accuracy/avg_time/stability。

    模拟阶段指标暂时没有数据源（做题记录表还没有用时字段），先返回 None，
    等做题记录补上后再接。
    """
    rows: List[ErrorAnalysis] = db.query(ErrorAnalysis).all()

    distribution = {et.value: 0 for et in ErrorType}
    for row in rows:
        if row.error_type in distribution:
            distribution[row.error_type] += 1

    latencies = [r.identify_latency_sec for r in rows if r.identify_latency_sec is not None]
    latency_avg = round(sum(latencies) / len(latencies), 1) if latencies else None

    # 拆解覆盖率：DECOMPOSE 类里写出拆解句的题数 / DECOMPOSE 类总题数
    decompose_rows = [r for r in rows if r.error_type == ErrorType.DECOMPOSE.value]
    covered = sum(1 for r in decompose_rows if r.decomposition_sentence)
    coverage = f'{covered}/{len(decompose_rows)}' if decompose_rows else '0/0'

    pending = sum(1 for r in rows if r.remedy_status == RemedyStatus.PENDING.value)

    stats = {
        'error_distribution': distribution,
        'identify_latency_avg_sec': latency_avg,
        'decomposition_coverage': coverage,
        'remedy_pending_count': pending,
        'total': len(rows),
    }

    if not practice_mode:
        stats.update({'accuracy': None, 'avg_time_sec': None, 'stability': None})

    return stats


# -------------------------------------------------------------------- 实体 -> DTO

def to_out(row: ErrorAnalysis) -> ErrorAnalysisOut:
    """把 ORM 行转成交付给前端的 DTO，顺带补上中文类型名。"""
    try:
        type_name = ERROR_TYPE_META[ErrorType(row.error_type)]['name']
    except (KeyError, ValueError):
        type_name = row.error_type

    return ErrorAnalysisOut(
        id=row.id,
        problem_id=row.problem_id,
        problem_title=row.problem_title,
        topic=row.topic,
        mother_problem=row.mother_problem,
        error_type=row.error_type,
        error_type_name=type_name,
        tag=row.tag,
        specific_behavior=row.specific_behavior,
        first_break_point=row.first_break_point,
        decomposition_sentence=row.decomposition_sentence,
        remedy_status=row.remedy_status,
        remedy_action=row.remedy_action,
        user_note=row.user_note,
        reviewed=row.reviewed,
        created_at=row.created_at,
        identify_latency_sec=row.identify_latency_sec,
    )
