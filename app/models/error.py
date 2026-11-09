"""错因分类：枚举定义、SQLAlchemy 实体、Pydantic 校验模型。

六个错因类型按"最早断掉的一环"优先级互斥，枚举值必须与规格里的 code 保持完全一致，
任何新增或重命名都要同步改三处：本文件 ErrorType、下游 services/error.py 的标签建议逻辑、
以及 routers/error.py 返回给前端的 errorTypes 字典。
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# --------------------------------------------------------------------------- 枚举

class ErrorType(str, Enum):
    """六类错因，按决策树优先级从小到大。

    互斥判定规则：取"最早断掉的一环"，priority 数字小者优先。
    边界提示（避免模型漂移）：
      - READ vs IDENTIFY：READ 是"连要输出什么都不知道"；IDENTIFY 是"知道要做什么但选不出方法"
      - IDENTIFY vs DECOMPOSE：IDENTIFY 是"没方向"；DECOMPOSE 是"有方向但不知道改哪"
      - DECOMPOSE vs OPERATE：DECOMPOSE 是"说不出 = 母题 + 改 XX"；OPERATE 是"思路对但写错"
      - OPERATE vs BOUNDARY：OPERATE 是"主逻辑挂了"；BOUNDARY 是"主逻辑过了但特例没覆盖"
      - BOUNDARY vs EFFICIENCY：BOUNDARY 是"挂在内容正确性"；EFFICIENCY 是"内容都对但太慢/太占"
    """
    READ = 'READ'
    IDENTIFY = 'IDENTIFY'
    DECOMPOSE = 'DECOMPOSE'
    OPERATE = 'OPERATE'
    BOUNDARY = 'BOUNDARY'
    EFFICIENCY = 'EFFICIENCY'


class ErrorTag(str, Enum):
    """子标签，目前只有 OPERATE 可挂 SYNTAX"""
    SYNTAX = 'SYNTAX'


class RemedyStatus(str, Enum):
    PENDING = '待补'
    DONE = '已补'


ERROR_TYPE_META = {
    ErrorType.READ:       {'name': '读题错',    'priority': 1, 'signal': '看题解后第一反应是「原来问的是这个」',
                            'remedy': '练审题：圈输入范围、输出要求、特殊条件'},
    ErrorType.IDENTIFY:   {'name': '识别错',    'priority': 2, 'signal': '看题解前完全没方向，看后才知道「原来是这个套路」',
                            'remedy': '补「题面信号 → 模板」对照表，回看母题触发条件'},
    ErrorType.DECOMPOSE:  {'name': '拆解错',    'priority': 3, 'signal': '方向对了，但卡在「具体怎么改」',
                            'remedy': '做母题-变体差异对照，强制写一句话拆解'},
    ErrorType.OPERATE:    {'name': '操作错',    'priority': 4, 'signal': '看题解发现「我思路没错，就是写错了」',
                            'remedy': '默写原子操作；单独记语言坑'},
    ErrorType.BOUNDARY:   {'name': '边界错',    'priority': 5, 'signal': '样例过了，提交挂在小数据或特例上',
                            'remedy': '列边界清单，每道题写完强制过一遍'},
    ErrorType.EFFICIENCY: {'name': '效率错',    'priority': 6, 'signal': '答案对但超时/超内存',
                            'remedy': '补复杂度分析，记「这题该用什么复杂度」'},
}

# 结构化输出给前端展示的字典（路由层直接 import 使用）
ERROR_TYPES_FOR_API = [
    {'code': et.value, 'name': meta['name'], 'priority': meta['priority'],
     'signal': meta['signal'], 'remedy': meta['remedy']}
    for et, meta in ERROR_TYPE_META.items()
]


# --------------------------------------------------------------------------- SQLAlchemy

class ErrorAnalysis(Base):
    """单道错题归因记录。

    与 Problem 是弱关联：problem_id 存字符串即可，允许题目被删后仍保留归因历史。
    若同一 problem_id 可能多次归因（比如先判 READ 后更精确判 DECOMPOSE），用 id 做主键，
    problem_id 建索引方便按题查。
    """
    __tablename__ = 'error_analyses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(String(36), index=True, nullable=False, comment='关联 Problem.id，字符串非外键')
    problem_title = Column(String(200), nullable=False)
    topic = Column(String(100))
    mother_problem = Column(String(200))
    error_type = Column(String(20), nullable=False)          # ErrorType.value
    tag = Column(String(20), nullable=True)                  # ErrorTag.value，仅 OPERATE 可填
    specific_behavior = Column(String(200), nullable=False)
    first_break_point = Column(String(20), nullable=False)   # 冗余字段，目前恒等于 error_type
    decomposition_sentence = Column(String(300), nullable=True)
    remedy_status = Column(String(20), nullable=False, default='待补')
    remedy_action = Column(String(300))
    user_note = Column(Text)
    reviewed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    identify_latency_sec = Column(Integer, nullable=True)     # 从看到题到说出「这是 XX 母题」的秒数

    __table_args__ = (
        Index('ix_error_analyses_created_at', 'created_at'),
    )


# --------------------------------------------------------------------------- Pydantic

_DECOMPOSE_KEYWORDS = ('=', '母题', '改')


class ErrorAnalysisCreate(BaseModel):
    """创建归因的请求体，字段约束严格按规格文档。"""
    problem_id: str
    problem_title: str = Field(..., max_length=200)
    topic: Optional[str] = None
    mother_problem: Optional[str] = None
    error_type: ErrorType
    tag: Optional[ErrorTag] = None
    specific_behavior: str = Field(..., max_length=50)
    first_break_point: Optional[ErrorType] = None
    decomposition_sentence: Optional[str] = None
    remedy_status: RemedyStatus = RemedyStatus.PENDING
    remedy_action: Optional[str] = None
    user_note: Optional[str] = None
    identify_latency_sec: Optional[int] = Field(None, ge=0)
    reviewed: bool = False

    @model_validator(mode='after')
    def _enforce_cross_field_rules(self):
        """跨字段约束（用 after 模式，保证默认值也能被校验到）：
        1) tag 仅在 OPERATE 下可填
        2) first_break_point 缺省时等于 error_type
        3) DECOMPOSE 必须写拆解句，且含「=」「母题」「改」三关键词；其他类型不许填
        """
        if self.tag is not None and self.error_type != ErrorType.OPERATE:
            raise ValueError('tag 仅在 error_type=OPERATE 时可填')

        if self.first_break_point is None:
            self.first_break_point = self.error_type

        if self.error_type == ErrorType.DECOMPOSE:
            if not self.decomposition_sentence:
                raise ValueError('DECOMPOSE 类必须填写 decomposition_sentence')
            missing = [kw for kw in _DECOMPOSE_KEYWORDS if kw not in self.decomposition_sentence]
            if missing:
                raise ValueError(
                    f'拆解句必须同时含「=」「母题」「改」三关键词，缺少：{"".join(missing)}'
                )
        elif self.decomposition_sentence:
            raise ValueError('仅 DECOMPOSE 类可填写 decomposition_sentence')

        return self


class ErrorAnalysisOut(BaseModel):
    """返回给前端的完整归因"""
    model_config = {'from_attributes': True}

    id: int
    problem_id: str
    problem_title: str
    topic: Optional[str] = None
    mother_problem: Optional[str] = None
    error_type: str
    error_type_name: str
    tag: Optional[str] = None
    specific_behavior: str
    first_break_point: str
    decomposition_sentence: Optional[str] = None
    remedy_status: str
    remedy_action: Optional[str] = None
    user_note: Optional[str] = None
    reviewed: bool
    created_at: datetime
    identify_latency_sec: Optional[int] = None


class ErrorAnalysisUpdate(BaseModel):
    """允许部分字段更新（复盘时改 reviewed、remedy_status 等）"""
    reviewed: Optional[bool] = None
    remedy_status: Optional[RemedyStatus] = None
    remedy_action: Optional[str] = None
    user_note: Optional[str] = None


class DecisionStep(BaseModel):
    """决策树单步返回"""
    step: int
    question: str
    # 两个分支对应上一步用户的回答；首步无 step 依赖
    yes_go_to: Optional[int] = None
    no_go_to: Optional[int] = None
    result_if_yes: Optional[str] = None   # ErrorType.value
    result_if_no: Optional[str] = None


class StatisticsOut(BaseModel):
    """统计口径：练习模式只返回四项；模拟模式附加 accuracy/avgTime/stability。"""
    error_distribution: dict
    identify_latency_avg_sec: Optional[float]
    decomposition_coverage: str
    remedy_pending_count: int
    # 以下三个字段，若该用户尚未进入模拟模式则为 null
    accuracy: Optional[float] = None
    avg_time_sec: Optional[float] = None
    stability: Optional[float] = None
