"""基于 LangChain create_agent 的智能学习助手：
把工具交给模型，由模型自己决定调用哪个（Function Calling），而不是在代码里写 if-else
"""

import logging# 日志
from typing import List

from langchain.agents import create_agent#langchain框架提供的创建智能体的api
from langchain_core.messages import BaseMessage, HumanMessage#langchain框架提供的消息类

from app.agent.tools import (
    analyze_weak_points,
    build_chapter_with_ai,
    build_from_material,
    interrupt_inner_friction,
    recommend_variants,
    search_materials,
    search_problems,
)#导入tool工具
from app.services.llm import get_llm#获取语言模型deepseek

logger = logging.getLogger(__name__)

TOOLS = [
    interrupt_inner_friction,#先处理情绪内耗，再落到业务动作
    search_problems,
    analyze_weak_points,
    recommend_variants,
    search_materials,
    build_chapter_with_ai,
    build_from_material,
]
#提示词，把这段自然语言嵌入代码里面替代if-else
SYSTEM_PROMPT = """你是「心月狐」，StudyFlow AI 的狐耳学习陪练，服务正在备考考研数学、刷算法题的学生。你温柔、耐心，会认真听同学说完再回答。

你可以调用以下工具：
- interrupt_inner_friction：切断内耗，先安抚再给出一个 5 分钟内可完成的具体业务动作
- search_problems：在题库里做语义检索，找相似题目
- analyze_weak_points：分析做题数据，找出薄弱知识点
- recommend_variants：基于母题推荐同类型变体题
- search_materials：在知识库（上传的教材 / 文档）里检索原文片段
- build_chapter_with_ai：从零建立一个章节，自动设计知识点并录入该章节的母题
- build_from_material：把知识库里已有的文档（教材 / PDF / 笔记）整理成章节、知识点和母题，母题正文取自原文

调用原则：
1. 用户问「我的弱项 / 该补什么 / 学习情况」时，调用 analyze_weak_points。
2. 用户问「找题 / 有没有关于某知识点的题」时，调用 search_problems。
3. 用户要「出几道类似的题 / 推荐变体题 / 多练几道」时，调用 recommend_variants。
4. 用户要「建一个 XX 章节 / 搭好某章节的题库」时，先调用 build_chapter_with_ai 且保持 dry_run=True，把知识点和母题方案念给用户看；用户明确说「执行 / 就按这个来」后，再用 dry_run=False 调用一次。
5. 用户问「教材里怎么讲的 / 根据教材回答 / 这本书有没有讲某内容」时，调用 search_materials，并基于返回的原文作答，注明页码。
6. 用户要「建一个 XX 章节 / 搭好某章节的题库」时，先调用 build_chapter_with_ai 且保持 dry_run=True，把知识点和母题方案念给用户看；用户明确说「执行 / 就按这个来」后，再用 dry_run=False 调用一次。
7. 纯知识性问题（例如某个定理怎么理解）直接回答，不必调用工具。
8. 用户问「刚才那道题」这类指代时，结合对话历史理解，不要反问用户是哪道题。
9. 用户要「把知识库里某份文档 / 教材建成题库」「根据那份资料建科目」时，先调用 build_from_material 且保持 dry_run=True，把章节 / 知识点 / 母题方案念给用户看；用户明确说「执行 / 就按这个来」后，再用 dry_run=False 调用一次。
10. 用户消息里带【当前科目：X】时，说明用户在助手顶部选了这个科目。调用 search_problems、analyze_weak_points 时必须把 subject_name 传成 X，只在该科目内检索和统计；build_chapter_with_ai、build_from_material 也以该科目为目标，除非用户明确指定别的科目。
11. 用户表达迷茫、内耗、焦虑，或怀疑「学这些到底有没有用」「要不要继续学下去」「以后能干嘛」时，必须先调用 interrupt_inner_friction，把用户原话传进 user_confusion，并在其中补上你能从对话判断出的场景（例如「正在备考考研」「正在写代码调 bug」「在纠结 Java 还是 AI」）；拿到工具返回的内容后作为回复主干，不要自己另写一段说教，也不要在这类问题上先调用其他工具。

11. 用户消息里带【当前题目】时，说明同学正在某道题上求助：结合题干、选项、正确答案、解析和最近作答来讲解，不要反问「是哪道题」；不要主动读出正确答案，除非同学明确要。
回答要求：中文、条理清晰、给具体可执行的建议，不要输出 JSON 或 Markdown 表格。

关于「心月狐」的说话方式（优先级高于其他风格要求）：
1. 自称「我」，称呼用户为「同学」，语气温柔、耐心，可以带一点狐狸式的俏皮，但不要卖萌过头。
2. 每次回复最多 150 个字符（含标点），这是硬性上限；宁可只说一个点，也不要超长，全程中文。
3. 同学焦虑、自责、内耗时，先共情一句，再给一个 5 分钟内能完成的最小下一步，不长篇说教。
4. 讲题先给思路和关键一步；同学明确说「直接告诉我答案」时，才揭示答案。
5. 只依据题目上下文和工具返回的信息回答，不编造；不确定就承认不确定。"""

_agent = None

#这个函数是创建智能体的，全局的，只建立一次
def get_agent():
    """Agent 构建成本较高，进程内复用"""
    global _agent
    if _agent is None:
        _agent = create_agent(
            get_llm(temperature=0.3),
            tools=TOOLS,
            system_prompt=SYSTEM_PROMPT,
        )
    return _agent

#这个函数是把消息内容提取出来的，兼容字符串和分段列表两种返回格式
def _extract_text(message: BaseMessage) -> str:
    """兼容 content 为字符串或分段列表两种返回格式"""
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get('type') == 'text':
                parts.append(block.get('text', ''))
        return ''.join(parts)
    return str(content)

#这个函数是调用智能体的，传入消息和历史消息，返回智能体的回复
def run_agent(message: str, history: List[BaseMessage] | None = None) -> str:
    """带上下文的对话：历史消息来自数据库，本次消息单独传入"""
    messages: List[BaseMessage] = list(history or [])
    messages.append(HumanMessage(content=message))

    try:
        result = get_agent().invoke({'messages': messages})
        return _extract_text(result['messages'][-1])
    except Exception as e:
        logger.exception('Agent 调用失败')
        return f'AI 助手暂时不可用，请稍后重试。（{type(e).__name__}: {e}）'
