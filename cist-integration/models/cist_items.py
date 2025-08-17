"""
CIST (Cognitive Impairment Screening Test) 문항 정의

음성 대화 기반으로 평가 가능한 CIST 문항들을 정의합니다.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class CognitiveDomain(Enum):
    """인지 기능 영역 분류"""
    ORIENTATION = "orientation"  # 지남력
    MEMORY = "memory"  # 기억력  
    ATTENTION = "attention"  # 주의력
    EXECUTIVE = "executive"  # 집행기능
    LANGUAGE = "language"  # 언어기능


class TaskType(Enum):
    """과제 유형 분류"""
    QUESTION_ANSWER = "question_answer"  # 질문-답변
    REPETITION = "repetition"  # 따라하기
    RECALL = "recall"  # 회상하기
    GENERATION = "generation"  # 생성하기
    COMPREHENSION = "comprehension"  # 이해하기


@dataclass
class CISTItem:
    """CIST 개별 문항 정의"""
    id: str
    domain: CognitiveDomain
    task_type: TaskType
    name: str
    description: str
    max_score: int
    natural_integration_strategy: str  # 자연스러운 통합 전략
    evaluation_criteria: Dict[str, Any]
    example_questions: List[str]


class CISTItemsRegistry:
    """CIST 문항 레지스트리"""
    
    def __init__(self):
        self.items = self._initialize_items()
    
    def _initialize_items(self) -> Dict[str, CISTItem]:
        """음성 대화 가능한 CIST 문항들 초기화"""
        
        items = {}
        
        # === 지남력 (5점) ===
        items["orientation_time"] = CISTItem(
            id="orientation_time",
            domain=CognitiveDomain.ORIENTATION,
            task_type=TaskType.QUESTION_ANSWER,
            name="시간 지남력",
            description="오늘 날짜(연, 월, 일, 요일)를 정확히 말할 수 있는지 평가",
            max_score=4,
            natural_integration_strategy="사진의 배경이나 상황과 연관지어 자연스럽게 날짜를 물어보기",
            evaluation_criteria={
                "year": 1,
                "month": 1, 
                "day": 1,
                "weekday": 1
            },
            example_questions=[
                "이 사진을 보니 옛날 생각이 나시네요. 그런데 어르신, 오늘이 몇 년도인지 아세요?",
                "오늘이 며칠인지 기억하세요?",
                "오늘이 무슨 요일인지 아시나요?"
            ]
        )
        
        items["orientation_place"] = CISTItem(
            id="orientation_place", 
            domain=CognitiveDomain.ORIENTATION,
            task_type=TaskType.QUESTION_ANSWER,
            name="장소 지남력",
            description="현재 계신 장소를 정확히 말할 수 있는지 평가",
            max_score=1,
            natural_integration_strategy="대화 중 자연스럽게 현재 위치에 대해 물어보기",
            evaluation_criteria={
                "location": 1
            },
            example_questions=[
                "어르신께서 지금 어디에 계신지 알고 계세요?",
                "지금 이곳이 어디인지 말씀해 주세요."
            ]
        )
        
        # === 기억력 (10점) ===
        items["memory_registration"] = CISTItem(
            id="memory_registration",
            domain=CognitiveDomain.MEMORY,
            task_type=TaskType.REPETITION,
            name="기억 등록",
            description="문장을 듣고 바로 따라 말할 수 있는지 평가",
            max_score=5,
            natural_integration_strategy="사진 설명 중 특정 문장을 기억하도록 요청",
            evaluation_criteria={
                "immediate_repetition": 5
            },
            example_questions=[
                "이 문장을 잘 들으시고 그대로 따라 해보세요: '빨간 꽃이 정원에서 예쁘게 피었습니다'",
                "제가 말하는 문장을 기억해 두세요: '파란 하늘 아래 하얀 구름이 떠다닙니다'"
            ]
        )
        
        items["memory_recall"] = CISTItem(
            id="memory_recall",
            domain=CognitiveDomain.MEMORY,
            task_type=TaskType.RECALL,
            name="기억 회상",
            description="이전에 들었던 문장을 다시 말할 수 있는지 평가",
            max_score=5,
            natural_integration_strategy="대화 중간에 이전 문장을 기억하는지 확인",
            evaluation_criteria={
                "delayed_recall": 5
            },
            example_questions=[
                "아까 제가 말씀드린 문장을 기억하세요? 다시 한 번 말씀해 주세요.",
                "처음에 말씀드린 그 문장, 혹시 기억나세요?"
            ]
        )
        
        # === 주의력 (3점) ===
        items["attention_forward"] = CISTItem(
            id="attention_forward",
            domain=CognitiveDomain.ATTENTION,
            task_type=TaskType.REPETITION,
            name="숫자 바로 따라말하기",
            description="숫자 순서를 듣고 그대로 따라 말할 수 있는지 평가",
            max_score=2,
            natural_integration_strategy="사진 속 숫자나 년도와 연관지어 자연스럽게 제시",
            evaluation_criteria={
                "digit_span_forward": 2
            },
            example_questions=[
                "제가 말하는 숫자를 그대로 따라해 보세요: 5-8-2",
                "이 숫자들을 순서대로 말해보세요: 1-9-4-7"
            ]
        )
        
        items["attention_backward"] = CISTItem(
            id="attention_backward",
            domain=CognitiveDomain.ATTENTION,
            task_type=TaskType.REPETITION,
            name="숫자 거꾸로 말하기",
            description="숫자 순서를 듣고 거꾸로 말할 수 있는지 평가",
            max_score=1,
            natural_integration_strategy="놀이처럼 재미있게 거꾸로 말하기 도전",
            evaluation_criteria={
                "digit_span_backward": 1
            },
            example_questions=[
                "이번엔 거꾸로 말해보세요. 제가 '3-7'이라고 하면 '7-3'이라고 해주세요.",
                "거꾸로 하는 게임해볼까요? 2-5-9를 거꾸로 말해보세요."
            ]
        )
        
        # === 집행기능 (2점) ===
        items["executive_verbal_fluency"] = CISTItem(
            id="executive_verbal_fluency",
            domain=CognitiveDomain.EXECUTIVE,
            task_type=TaskType.GENERATION,
            name="언어 추론 (범주 유창성)",
            description="과일이나 채소 이름을 최대한 많이 말할 수 있는지 평가",
            max_score=2,
            natural_integration_strategy="사진 속 음식이나 자연과 연관지어 자연스럽게 유도",
            evaluation_criteria={
                "fruits_vegetables_count": {
                    "0-5": 0,
                    "6-9": 1, 
                    "10+": 2
                }
            },
            example_questions=[
                "이 사진을 보니 맛있는 음식이 생각나네요. 과일 이름을 아시는 대로 말씀해 보세요.",
                "채소 종류를 많이 아시나요? 아는 채소 이름을 말해보세요."
            ]
        )
        
        # === 언어기능 (2점) ===
        items["language_naming"] = CISTItem(
            id="language_naming",
            domain=CognitiveDomain.LANGUAGE,
            task_type=TaskType.QUESTION_ANSWER,
            name="이름대기",
            description="사진 속 사물의 이름을 정확히 말할 수 있는지 평가",
            max_score=1,
            natural_integration_strategy="사진 속 객체들을 자연스럽게 지목하며 이름 묻기",
            evaluation_criteria={
                "object_naming": 1
            },
            example_questions=[
                "이 사진에서 보이는 이것은 무엇인가요?",
                "여기 보이는 물건의 이름이 뭔지 아세요?"
            ]
        )
        
        items["language_comprehension"] = CISTItem(
            id="language_comprehension",
            domain=CognitiveDomain.LANGUAGE,
            task_type=TaskType.COMPREHENSION,
            name="이해력",
            description="지시사항을 듣고 이해할 수 있는지 평가",
            max_score=1,
            natural_integration_strategy="대화 중 자연스러운 요청이나 부탁으로 제시",
            evaluation_criteria={
                "instruction_following": 1
            },
            example_questions=[
                "잠깐만 '안녕하세요'라고 말씀해 주세요.",
                "'고맙습니다'라고 한 번 말해보시겠어요?"
            ]
        )
        
        return items
    
    def get_items_by_domain(self, domain: CognitiveDomain) -> List[CISTItem]:
        """특정 인지 영역의 문항들 반환"""
        return [item for item in self.items.values() if item.domain == domain]
    
    def get_total_possible_score(self) -> int:
        """총 가능 점수 계산"""
        return sum(item.max_score for item in self.items.values())
    
    def get_item(self, item_id: str) -> Optional[CISTItem]:
        """특정 문항 반환"""
        return self.items.get(item_id)


# 전역 레지스트리 인스턴스
cist_registry = CISTItemsRegistry()