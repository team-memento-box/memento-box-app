"""
자연스러운 대화를 담당하는 에이전트
"""

from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage


class ConversationAgent:
    """자연스러운 대화 에이전트"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        
    def _build_conversation_prompt(self, photo_analysis: Dict[str, Any]) -> str:
        """대화용 시스템 프롬프트 구성"""
        
        caption = photo_analysis.get("caption", "")
        mood = photo_analysis.get("mood", "")
        objects = photo_analysis.get("objects", [])
        people_count = photo_analysis.get("people_count", 0)
        
        objects_text = ", ".join(objects) if objects else "다양한 요소들"
        
        prompt = f"""너는 치매 어르신과 대화하는 친근하고 따뜻한 요양보호사입니다.

=== 사진 정보 ===
- 주요 내용: {caption}
- 분위기: {mood}  
- 주요 요소들: {objects_text}
- 사람 수: {people_count}명

=== 대화 원칙 ===
1. 어르신을 존중하고 공경하는 말투 사용
2. 친근하고 따뜻한 분위기 유지
3. 사진과 관련된 추억이나 경험에 대해 대화
4. 어르신의 답변에 충분히 공감하고 반응
5. 적절한 길이의 자연스러운 응답 (2-3문장)
6. 치매 증상을 고려하여 이해하기 쉽게 대화
7. 반복되는 질문이나 답변에도 인내심 있게 대응

=== 대화 목표 ===
- 사진 속 내용에 대해 어르신의 기억과 경험 듣기
- 즐겁고 의미 있는 대화 시간 만들기
- 어르신이 편안하게 이야기할 수 있는 분위기 조성
"""
        return prompt
    
    async def generate_response(self, 
                              user_message: str,
                              photo_analysis: Dict[str, Any],
                              conversation_history: List[Dict[str, str]]) -> str:
        """자연스러운 대화 응답 생성"""
        
        system_prompt = self._build_conversation_prompt(photo_analysis)
        
        # 대화 히스토리를 메시지로 변환 (최근 10개만)
        messages = [SystemMessage(content=system_prompt)]
        
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        
        for msg in recent_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # 현재 사용자 메시지 추가
        messages.append(HumanMessage(content=user_message))
        
        response = await self.llm.ainvoke(messages)
        return response.content
    
    async def generate_initial_question(self, photo_analysis: Dict[str, Any]) -> str:
        """첫 대화 질문 생성"""
        
        caption = photo_analysis.get("caption", "사진")
        mood = photo_analysis.get("mood", "따뜻한")
        
        system_prompt = f"""
        치매 어르신과의 첫 대화를 시작하는 따뜻하고 친근한 질문을 만들어주세요.
        
        사진 정보:
        - 내용: {caption}
        - 분위기: {mood}
        
        요구사항:
        - 어르신을 존중하는 공손한 말투
        - 사진과 관련된 자연스러운 질문
        - 어르신의 추억이나 경험을 이끌어낼 수 있는 내용
        - 2문장 이내로 간결하게
        
        예시: "어르신, 이 사진을 보니까 어떤 기분이 드세요? 혹시 비슷한 추억이 있으신가요?"
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="첫 대화 질문을 생성해주세요.")
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content
    
    async def assess_conversation_quality(self, conversation_history: List[Dict[str, str]]) -> Dict[str, float]:
        """대화 품질 평가"""
        
        if not conversation_history:
            return {"engagement": 0.0, "coherence": 0.0, "topic_maintenance": 0.0}
        
        user_messages = [msg["content"] for msg in conversation_history if msg["role"] == "user"]
        
        if not user_messages:
            return {"engagement": 0.0, "coherence": 0.0, "topic_maintenance": 0.0}
        
        system_prompt = """
        치매 어르신과의 대화 품질을 평가해주세요.
        
        평가 기준:
        1. engagement (참여도): 0.0-1.0, 어르신이 얼마나 적극적으로 대화에 참여하는가
        2. coherence (일관성): 0.0-1.0, 어르신의 응답이 얼마나 일관되고 논리적인가  
        3. topic_maintenance (주제 유지): 0.0-1.0, 주제를 얼마나 잘 유지하는가
        
        JSON 형태로 반환: {"engagement": 0.8, "coherence": 0.7, "topic_maintenance": 0.9}
        """
        
        user_responses = "\n".join([f"- {msg}" for msg in user_messages])
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"어르신의 응답들:\n{user_responses}")
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            import json
            quality_scores = json.loads(response.content)
            return quality_scores
        except:
            # 기본값 반환
            return {"engagement": 0.5, "coherence": 0.5, "topic_maintenance": 0.5}