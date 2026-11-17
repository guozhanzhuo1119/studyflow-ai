"""Agent 可调用的工具集合：LLM 通过 Function Calling 自行决定调用哪个工具"""

from typing import Dict, List

from langchain_core.tools import tool

from app import SessionLocal
from app.models.material import Material
from app.models.problem import Chapter, KnowledgePoint, Problem, Subject
from app.rag.retriever import semantic_search
from app.services.chapter_builder import build_chapter
from app.services.builder import build_from_material as build_material
from app.services.llm import get_llm
from app.services.materials import search_chunks
from app.services.recommend import recommend_variants as recommend_variants_service

DIFFICULTY_LABELS = {'easy': '简单', 'medium': '中等', 'hard': '困难'}

DEFUSE_PROMPT = """你是一名极度理性的认知教练。用户现在陷入了“决策瘫痪”和“意义迷茫”。
用户的迷茫原话是：{user_confusion}

请你严格按照以下三步进行回复：
1. 【正常化迷茫】：告诉他，面对未知觉得“有没有用”、“该怎么办”极其正常。
2. 【降维聚焦】：指出问题太宏大。让他做一道微观选择题：“咱们现在不去想‘选哪条路’，就问你现在这一刻，你是想 A. 查点具体资料，B. 找人倾诉，还是 C. 先睡一觉？”
3. 【业务落地行动（关键）】：**绝不能只给喝水/跑步这种泛泛的建议！必须给出一个基于他当前（考研/编程/刷题）场景的、5分钟内能完成的微小业务动作。**
   - 比如：如果是纠结“考研有没有用”，建议：“现在去查一下目标院校近三年的报录比，或者只做一页数学错题。”
   - 如果是纠结“代码怎么调都不对”，建议：“不要看全局了，现在只把报错的那一行代码单独摘出来，发给我或者搜一下。”
   - 如果是纠结“Java还是AI”，建议：“现在去招聘软件上，分别搜这两个岗位，各截三张JD图。”

要求：语气理性、坚定、像一刀切断乱麻的教练。字数在 180 字以内。"""


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
def analyze_weak_points(subject_name: str = '') -> str:
    """分析用户当前题库的做题情况，找出掌握薄弱的知识点并给出复习建议。当用户问「我的弱项是什么」「该补哪里」「学习情况怎么样」时调用。
    subject_name 传当前科目名（如「计算机网络」「力扣hot100」）则只统计该科目；留空则统计全部。"""
    with SessionLocal() as db:
        query = (
            db.query(Problem, KnowledgePoint.name, Chapter.name, Subject.name)
            .join(KnowledgePoint, Problem.knowledge_point_id == KnowledgePoint.id)
            .outerjoin(Chapter, KnowledgePoint.chapter_id == Chapter.id)
            .outerjoin(Subject, Chapter.subject_id == Subject.id)
        )
        if subject_name:
            query = query.filter(Subject.name.like(f'%{subject_name}%'))
        rows = query.all()
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
def search_problems(query: str, top_k: int = 5, subject_name: str = '') -> str:
    """在题库中进行语义检索（向量相似度，不是关键词匹配），查找与 query 意思相近的题目。当用户想找某类题目、或想确认题库里有没有讲某个知识点的题时调用。
    subject_name 传当前科目名则只在该科目内检索；留空则全库检索。"""
    fetch_k = min(max(top_k, 1), 10)
    results = semantic_search(query, top_k=fetch_k if not subject_name else min(fetch_k * 4, 40))
    if subject_name:
        keyword = subject_name.replace(' ', '').lower()
        results = [
            item for item in results
            if keyword in (item.get('subject_name') or '').replace(' ', '').lower()
        ][:fetch_k]
    if not results:
        scope = f'「{subject_name}」科目里' if subject_name else ''
        return f'{scope}没有找到与「{query}」语义相近的题目。'
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


@tool
def search_materials(query: str, material_title: str = '', top_k: int = 3) -> str:
    """在知识库（上传的教材 PDF / 文档）里检索原文片段，返回书名、页码和原文。
    当用户问「教材里怎么讲的」「这本书有没有讲某内容」「根据教材回答」时调用。
    material_title 留空表示在所有文档里找；填书名的一部分可限定范围。"""
    with SessionLocal() as db:
        material_id = None
        if material_title.strip():
            material = (
                db.query(Material)
                .filter(Material.title.like(f'%{material_title.strip()}%'))
                .first()
            )
            if not material:
                return f'知识库里没有标题包含「{material_title}」的文档，请先在知识库页面上传。'
            material_id = material.id

        rows = search_chunks(db, query, material_id=material_id, top_k=min(max(top_k, 1), 5))

    if not rows:
        return f'知识库里没有检索到与「{query}」相关的内容。可以换个说法，或确认文档已上传且不是扫描版。'

    lines = [f'在知识库中检索「{query}」，命中 {len(rows)} 段原文：']
    for index, row in enumerate(rows, 1):
        content = row['content'].replace('\n', ' ')
        if len(content) > 500:
            content = content[:500] + '…'
        lines.append(f"{index}. 《{row['material']}》第 {row['page_no']} 页：{content}")
    return '\n'.join(lines)


@tool
def build_chapter_with_ai(
    subject_name: str,
    chapter_name: str,
    problem_count: int = 8,
    dry_run: bool = True,
) -> str:
    """从零建立一个章节：自动设计知识点结构，并把该章节的经典母题录入题库。
    当用户说「建立一个 XX 章节」「给我建一个栈的章节」「帮我搭好某章节的题库」时调用。
    subject_name 传已有科目名（如「力扣hot100」），chapter_name 传要建的章节名（如「栈」）。
    dry_run=True 只返回结构方案，不写库；用户确认后要以 dry_run=False 再调用一次才会真正建。"""
    with SessionLocal() as db:
        result = build_chapter(
            db,
            subject_name,
            chapter_name,
            problem_count=min(max(problem_count, 3), 20),
            dry_run=dry_run,
        )

    if not result['ok']:
        return result['message']

    lines = [
        f"章节结构方案：{result['subject']} / {result['chapter']}"
        f"（{'章节已存在' if result['chapter_exists'] else '将新建章节'}）",
        '',
    ]
    for index, knowledge_point in enumerate(result['knowledge_points'], 1):
        lines.append(f"{index}. {knowledge_point['name']}（{len(knowledge_point['problems'])} 题）")
        for title in knowledge_point['problems']:
            mark = '（题库已有，将跳过）' if title in knowledge_point['duplicated'] else ''
            lines.append(f"   - {title}{mark}")
    lines.append('')
    lines.append('划分依据：' + (result['note'] or '按解题套路划分'))
    lines.append('')
    if result['dry_run']:
        total = sum(len(kp['problems']) for kp in result['knowledge_points'])
        lines.append(f'当前是预览，共 {total} 道母题，未写入数据库。确认后回复「执行」，我再建章节。')
    else:
        lines.append(
            f"已执行：新建章节 {result['created_chapter']}，"
            f"新建知识点 {len(result['created_knowledge_points'])} 个，"
            f"新增母题 {result['created_problems']} 道，"
            f"跳过重复 {result['skipped_problems']} 道。"
        )
    return '\n'.join(lines)


@tool
def build_from_material(
    material_title: str,
    subject_name: str,
    chapter_hint: str = '',
    max_problems: int = 15,
    dry_run: bool = True,
) -> str:
    """根据知识库里的文档（PDF / TXT / Markdown）自动建立题库：
    从原文里整理出章节、知识点和母题，母题正文直接取自原文。
    当用户说「把某份资料建成题库」「根据这份教材建科目」「把文档内容录入系统」时调用。
    material_title 传知识库中的文档标题（可只写关键词），subject_name 传目标科目名（不存在会自动新建），
    chapter_hint 用于限定只处理文档的某一部分（如「第三章 栈和队列」），可留空。
    dry_run=True 只返回方案不写库；用户确认后再用 dry_run=False 调用一次才会真正建。"""
    with SessionLocal() as db:
        result = build_material(
            db,
            material_title,
            subject_name,
            chapter_hint=chapter_hint,
            max_problems=min(max(max_problems, 3), 40),
            dry_run=dry_run,
        )

    if not result['ok']:
        return result['message']

    total = sum(
        len(kp['problems'])
        for chapter in result['chapters']
        for kp in chapter['knowledge_points']
    )
    lines = [
        f"文档建题方案：{result['material']} → 科目「{result['subject']}」"
        f"（{'科目已存在' if result['subject_exists'] else '将新建科目'}）",
        '',
    ]
    for index, chapter in enumerate(result['chapters'], 1):
        lines.append(f"{index}. 章节：{chapter['name']}")
        for knowledge_point in chapter['knowledge_points']:
            lines.append(f"   - 知识点：{knowledge_point['name']}（{len(knowledge_point['problems'])} 题）")
            for item in knowledge_point['problems']:
                lines.append(f"     · {item['title']}（{item['chars']} 字，{item['source'] or '未标来源'}）")
    lines.append('')
    lines.append('划分依据：' + (result['note'] or '按文档原文的小节结构划分'))
    lines.append('')
    if result['dry_run']:
        lines.append(f'当前是预览，共 {total} 道母题，未写入数据库。确认后回复「执行」，我再建。')
    else:
        lines.append(
            f"已执行：新建科目 {result['created_subject']}，"
            f"新建章节 {len(result['created_chapters'])} 个，"
            f"新建知识点 {len(result['created_knowledge_points'])} 个，"
            f"新增母题 {result['created_problems']} 道，"
            f"跳过重复 {result['skipped_problems']} 道。"
        )
    return '\n'.join(lines)


@tool
def interrupt_inner_friction(user_confusion: str) -> str:
    """当用户陷入内耗、决策瘫痪、怀疑「学这个到底有没有用」「要不要继续学下去」时调用：
    先切断情绪内耗，再给出一个 5 分钟内能完成的具体业务动作。
    user_confusion 传用户的迷茫原话；如果对话里能看出他正在备考、刷题或写代码，
    把场景一并带上，例如「（正在写代码调 bug）他觉得自己根本不适合编程」。"""
    prompt = DEFUSE_PROMPT.format(user_confusion=user_confusion)
    content = get_llm(temperature=0.4).invoke(prompt).content
    return content if isinstance(content, str) else str(content)
