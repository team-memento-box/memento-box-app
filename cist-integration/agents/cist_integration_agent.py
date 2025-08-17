"""
CIST 문항을 자연스럽게 대화에 통합하는 에이전트
"""

from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from datetime import datetime
import random

from models.cist_items import cist_registry, CognitiveDomain


class CISTIntegrationAgent:
    """CIST 문항 통합 에이전트"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.registry = cist_registry
        
    async def assess_integration_opportunity(self, 
                                           conversation_history: List[Dict[str, str]],
                                           photo_analysis: Dict[str, Any],
                                           pending_items: List[str]) -> Dict[str, Any]:
        """현재 대화 맥락에서 CIST 문항 통합 기회 평가"""
        
        if not pending_items:
            return {"recommended_item": None, "strategy": None, "confidence": 0.0}
        
        # 최근 대화 내용 분석
        recent_messages = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
        conversation_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
        
        # 각 pending 문항에 대해 통합 가능성 평가
        best_item = None
        best_score = 0.0
        best_strategy = None
        
        for item_id in pending_items:
            item = self.registry.get_item(item_id)
            if not item:
                continue
                
            opportunity_score, strategy = await self._evaluate_integration_opportunity(
                item, conversation_context, photo_analysis
            )
            
            if opportunity_score > best_score:
                best_score = opportunity_score
                best_item = item_id
                best_strategy = strategy
        
        # 임계값 이상인 경우에만 추천
        if best_score > 0.6:
            evaluation_context = await self._prepare_evaluation_context(best_item, photo_analysis)
            
            return {
                "recommended_item": best_item,
                "strategy": best_strategy,
                "confidence": best_score,
                "evaluation_context": evaluation_context
            }
        
        return {"recommended_item": None, "strategy": None, "confidence": best_score}
    
    async def _evaluate_integration_opportunity(self, 
                                              item,
                                              conversation_context: str,
                                              photo_analysis: Dict[str, Any]) -> tuple[float, str]:
        """개별 문항의 통합 기회 평가"""
        
        system_prompt = f"""
        현재 대화 맥락에서 다음 CIST 문항을 자연스럽게 통합할 수 있는지 평가해주세요.
        
        CIST 문항 정보:
        - 이름: {item.name}
        - 설명: {item.description}
        - 자연스러운 통합 전략: {item.natural_integration_strategy}
        - 예시 질문들: {', '.join(item.example_questions[:2])}
        
        사진 정보:
        - 내용: {photo_analysis.get('caption', '')}
        - 분위기: {photo_analysis.get('mood', '')}
        - 객체들: {', '.join(photo_analysis.get('objects', []))}
        
        평가 기준:
        1. 현재 대화 흐름과의 자연스러운 연결 가능성
        2. 사진 내용과의 관련성
        3. 어르신에게 부담스럽지 않은 방식으로 제시 가능한지
        
        결과를 JSON으로 반환:
        {{
            "opportunity_score": 0.0-1.0,
            "recommended_strategy": "natural_transition|direct_question|game_like|storytelling",
            "reasoning": "평가 근거"
        }}
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"현재 대화 맥락:\n{conversation_context}")
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            import json
            result = json.loads(response.content)
            return result.get("opportunity_score", 0.0), result.get("recommended_strategy", "natural_transition")
        except:
            # 기본적인 휴리스틱 평가
            return self._basic_opportunity_assessment(item, conversation_context, photo_analysis)
    
    def _basic_opportunity_assessment(self, item, conversation_context: str, photo_analysis: Dict[str, Any]) -> tuple[float, str]:
        """기본적인 기회 평가 (LLM 실패 시 대안)"""
        
        score = 0.3  # 기본 점수
        
        # 문항별 특화 평가
        if item.domain == CognitiveDomain.ORIENTATION:
            if any(keyword in conversation_context.lower() for keyword in ['날짜', '시간', '언제', '오늘', '장소', '어디']):
                score += 0.4
        
        elif item.domain == CognitiveDomain.MEMORY:
            if any(keyword in conversation_context.lower() for keyword in ['기억', '생각', '옛날', '과거']):
                score += 0.3
        
        elif item.domain == CognitiveDomain.ATTENTION:
            if len(conversation_context) > 200:  # 충분한 대화가 진행된 경우
                score += 0.2
        
        elif item.domain == CognitiveDomain.EXECUTIVE:
            if any(keyword in conversation_context.lower() for keyword in ['음식', '과일', '채소', '먹다']):
                score += 0.4
        
        elif item.domain == CognitiveDomain.LANGUAGE:
            if photo_analysis.get('objects'):
                score += 0.3
        
        return min(1.0, score), "natural_transition"
    
    async def integrate_cist_item(self, 
                                item_id: str,
                                strategy: str,
                                conversation_context: Dict[str, Any]) -> str:
        """CIST 문항을 자연스럽게 통합한 질문 생성"""
        
        item = self.registry.get_item(item_id)
        if not item:
            return "죄송합니다. 다음 질문을 준비하고 있어요."
        
        history = conversation_context.get("history", [])
        photo_analysis = conversation_context.get("photo_analysis", {})
        
        recent_context = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in history[-4:] if history
        ])
        
        system_prompt = f"""
        CIST 인지기능 평가 문항을 자연스러운 대화에 녹여서 질문을 만들어주세요.
        
        문항 정보:
        - 이름: {item.name}
        - 설명: {item.description}
        - 통합 전략: {item.natural_integration_strategy}
        - 예시 질문: {random.choice(item.example_questions)}
        
        사진 정보:
        - 내용: {photo_analysis.get('caption', '')}
        - 분위기: {photo_analysis.get('mood', '')}
        
        통합 전략: {strategy}
        
        요구사항:
        1. 기존 대화 흐름에서 자연스럽게 이어지도록
        2. 어르신이 부담스럽지 않게 친근한 톤으로
        3. 사진이나 이전 대화 내용과 연결해서
        4. 평가 목적을 드러내지 말고 자연스러운 대화처럼
        5. 2-3문장 이내로 간결하게
        
        특별 지침:
        - 지남력: 사진이나 추억과 연관지어 날짜/장소 물어보기
        - 기억력: "제가 말씀드린 것 기억하세요?" 형태보다는 자연스러운 반복 요청
        - 주의력: 게임이나 놀이 형태로 제시
        - 집행기능: 사진 속 음식이나 자연과 연관지어
        - 언어기능: 사진 속 사물을 자연스럽게 지목하며
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"최근 대화 맥락:\n{recent_context}")
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # 특별한 문항의 경우 추가 처리
        integrated_question = response.content
        
        if item_id == "memory_registration":
            # 기억할 문장 추가
            memory_sentence = self._generate_memory_sentence(photo_analysis)
            integrated_question += f" 잠깐, 이 문장을 잘 기억해 두세요: '{memory_sentence}'"
        
        return integrated_question
    
    def _generate_memory_sentence(self, photo_analysis: Dict[str, Any]) -> str:
        """기억 과제용 문장 생성"""
        
        sentences = [
            "빨간 장미가 정원에서 아름답게 피었습니다",
            "파란 하늘 아래 하얀 구름이 천천히 떠다닙니다", 
            "작은 새가 나무 위에서 즐겁게 노래합니다",
            "따뜻한 햇살이 창문으로 들어옵니다",
            "고양이가 방석 위에서 편안히 잠을 잡니다"
        ]
        
        # 사진 내용과 연관된 문장이 있다면 우선 선택
        caption = photo_analysis.get('caption', '').lower()
        if '꽃' in caption or '정원' in caption:
            return sentences[0]
        elif '하늘' in caption or '구름' in caption:
            return sentences[1]
        elif '새' in caption or '나무' in caption:
            return sentences[2]
        
        return random.choice(sentences)
    
    async def _prepare_evaluation_context(self, item_id: str, photo_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """평가를 위한 컨텍스트 준비"""
        
        context = {}
        
        if item_id == "memory_registration" or item_id == "memory_recall":
            context["target_sentence"] = self._generate_memory_sentence(photo_analysis)
        
        elif item_id == "attention_forward" or item_id == "attention_backward":
            # 숫자 시퀀스 생성
            if item_id == "attention_forward":
                context["target_digits"] = "5-8-2"
            else:
                context["target_digits"] = "3-7"
        
        elif item_id == "language_naming":
            # 사진 속 객체 중 하나 선택
            objects = photo_analysis.get('objects', [])
            if objects:
                context["target_object"] = random.choice(objects)
        
        elif item_id == "language_comprehension":
            instructions = [
                ("안녕하세요라고 말해보세요", "안녕하세요"),
                ("고맙습니다라고 해보세요", "고맙습니다"),
                ("네라고 대답해보세요", "네")
            ]
            instruction, expected = random.choice(instructions)
            context["instruction"] = instruction
            context["expected_response"] = expected
        
        return context