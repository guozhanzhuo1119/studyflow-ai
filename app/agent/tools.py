"""Agent 可调用的工具集合：LLM 通过 Function Calling 自行决定调用哪个工具"""

from typing import Dict, List

from langchain_core.tools import tool

from app import SessionLocal
from app.models.problem import Chapter, KnowledgePoint, Problem, Subject
from app.rag.retriever import semantic_search
from app.services.llm import get_llm
from app.services.recommend import recommend_variants as recommend_variants_service

DIFFICULTY_LABELS = {'easy': '简单', 'medium': '中等', 'hard': '困难'}


def _difficulty_label(value: str | None) -> str:
    return DIFFICULTY_LABELS.get((value or '').lower(), value or '未知')


def _path_text(kp_name: str | None, chapter_name: str | None, subject_name: str | None) -> str:
    return ' / '.join(name for name in (subject_name, chapter_name, kp_name) if name) or '未归类'


def _format_problem(item: Dict, index: int) -> str:
    path = _path_text(
        item.get('knowledge_point_name'),
        item.get('chapter_name'),
        item.get('subject_name'),
    )
    line = (
        f"{index}. {item.get('title')}（层级：{path}，"
        f"来源：{item.get('source') or '未知'}"
    )
    if item.get('score') is not None:
        line += f"，相似度：{item['score']}"
    return line + '）'


@tool
def analyze_weak_points() -> str:
    """分析用户当前题库的做题情况，找出掌握薄弱的知识点并给出复习建议。当用户问「我的弱项是什么」「该补哪里」「学习情况怎么样」时调用。"""
    with SessionLocal() as db:
        rows = (
            db.query(Problem, KnowledgePoint.name, Chapter.name, Subject.name)
            .join(KnowledgePoint, Problem.knowledge_point_id == KnowledgePoint.id)
            .outerjoin(Chapter, KnowledgePoint.chapter_id == Chapter.id)
            .outerjoin(Subject, Chapter.subject_id == Subject.id)
            .all()
        )
        if not rows:
            return '题库中还没有题目，无法分析弱项。请先在知识点下录入题目。'

        stats: Dict[str, Dict[str, int]] = {}
        done_titles: List[str] = []
        for problem, kp_name, chapter_name, subject_name in rows:
            name = _path_text(kp_name, chapter_name, subject_name)
            bucket = stats.setdefault(name, {'total': 0, 'done': 0})
            bucket['total'] += 1
            if (problem.status or '') == 'done':
                bucket['done'] += 1
                done_titles.append(problem.title)

        total = sum(b['total'] for b in stats.values())
        done = sum(b['done'] for b in stats.values())

    summary = [f'题库共 {total} 题，已完成 {done} 题，未完成 {total - done} 题。', '各知识点情况：']
    for name, bucket in sorted(stats.items(), key=lambda kv: kv[1]['done'] / max(kv[1]['total'], 1)):
        rate = bucket['done'] / bucket['total'] * 100
        summary.append(
            f'- {name}：共 {bucket["total"]} 题，完成 {bucket["done"]} 题，完成率 {rate:.0f}%'
        )
    if done_titles:
        summary.append('已完成的题目：' + '、'.join(done_titles[:10]))

    prompt = f"""你是一个学习分析助手。根据用户的刷题数据，分析薄弱知识点并给出可执行的学习建议。

数据：
{chr(10).join(summary)}

请输出：
1. 薄弱知识点排序（结合题量、完成率判断）
2. 每个薄弱点建议重点复习什么
3. 接下来一周的练习建议（具体练什么题、多少道）

用中文，简洁分点，不要输出 JSON。"""

    return get_llm(temperature=0.3).invoke(prompt).content


@tool
def search_problems(query: str, top_k: int = 5) -> str:
    """在题库中进行语义检索（向量相似度，不是关键词匹配），查找与 query 意思相近的题目。当用户想找某类题目、或想确认题库里有没有讲某个知识点的题时调用。"""
    results = semantic_search(query, top_k=min(max(top_k, 1), 10))
    if not results:
        return f'没有找到与「{query}」语义相近的题目。'
    lines = [f'与「{query}」语义最相近的题目：']
    lines.extend(_format_problem(item, i) for i, item in enumerate(results, 1))
    return '\n'.join(lines)


@tool
def recommend_variants(problem_title: str, count: int = 3) -> str:
    """根据题库中的母题推荐同类型变体题，会先做语义检索再让模型生成。当用户说「给我出几道类似的题」「推荐变体题」「多练几道」时调用。problem_title 传题目名称或关键词。"""
    with SessionLocal() as db:
        problem = (
            db.query(Problem).filter(Problem.title == problem_title).first()
            or db.query(Problem).filter(Problem.title.like(f'%{problem_title}%')).first()
        )
        if not problem:
            candidates = semantic_search(problem_title, top_k=1)
            if candidates:
                problem = db.query(Problem).filter(Problem.id == candidates[0]['id']).first()
        if not problem:
            return f'题库中没有找到与「{problem_title}」相关的母题，请先确认题目是否已录入。'

        hierarchy = {
            'knowledge_point_name': None,
            'chapter_name': None,
            'subject_name': None,
        }
        kp = problem.knowledge_point
        if kp:
            hierarchy['knowledge_point_name'] = kp.name
            chapter = kp.chapter
            if chapter:
                hierarchy['chapter_name'] = chapter.name
                if chapter.subject:
                    hierarchy['subject_name'] = chapter.subject.name

        items: List[Dict] = recommend_variants_service(
            problem=problem,
            hierarchy=hierarchy,
            count=min(max(count, 1), 8),
        )

    lines = [f'母题：{problem.title}，推荐变体题如下：']
    for i, item in enumerate(items, 1):
        lines.append(
            f"{i}. {item['title']}（难度：{_difficulty_label(item['difficulty'])}"
            f"{'，来源：' + item['link'] if item.get('link') else ''}）\n"
            f"   推荐理由：{item['reason']}"
        )
    return '\n'.join(lines)
