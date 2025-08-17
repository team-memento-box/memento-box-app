"""
CIST 평가를 담당하는 에이전트
"""

from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from datetime import datetime

from schemas.evaluation import CISTEvaluation, EvaluationSummary, ItemResponse
from evaluators.scoring import CISTScorer
from models.cist_items import CognitiveDomain


class EvaluationAgent:
    """CIST 평가 에이전트"""
    
    def __init__(self, llm: ChatOpenAI, scorer: CISTScorer):
        self.llm = llm
        self.scorer = scorer
        
    async def generate_evaluation_summary(self, evaluation: CISTEvaluation) -> EvaluationSummary:
        """평가 요약 생성"""
        
        total_score, percentage = self.scorer.calculate_total_score(evaluation)
        domain_scores = self.scorer.calculate_domain_scores(evaluation)
        
        # 영역별 점수 추출
        orientation_score = domain_scores.get(CognitiveDomain.ORIENTATION, type('obj', (object,), {'total_score': 0})).total_score
        memory_score = domain_scores.get(CognitiveDomain.MEMORY, type('obj', (object,), {'total_score': 0})).total_score
        attention_score = domain_scores.get(CognitiveDomain.ATTENTION, type('obj', (object,), {'total_score': 0})).total_score
        executive_score = domain_scores.get(CognitiveDomain.EXECUTIVE, type('obj', (object,), {'total_score': 0})).total_score
        language_score = domain_scores.get(CognitiveDomain.LANGUAGE, type('obj', (object,), {'total_score': 0})).total_score
        
        # 위험도 평가
        risk_level = self._assess_risk_level(percentage)
        recommendations = await self._generate_recommendations(domain_scores, total_score)
        
        return EvaluationSummary(
            conversation_id=evaluation.conversation_id,
            total_score=total_score,
            max_score=evaluation.max_total_score,
            percentage=percentage,
            orientation_score=orientation_score,
            memory_score=memory_score,
            attention_score=attention_score,
            executive_score=executive_score,
            language_score=language_score,
            risk_level=risk_level,
            recommendations=recommendations,
            completed_at=datetime.now()
        )
    
    def _assess_risk_level(self, percentage: float) -> str:
        """위험도 평가"""
        
        if percentage >= 80:
            return "low"
        elif percentage >= 60:
            return "moderate"
        else:
            return "high"
    
    async def _generate_recommendations(self, 
                                      domain_scores: Dict[CognitiveDomain, Any],
                                      total_score: int) -> List[str]:
        """개선 권고사항 생성"""
        
        recommendations = []
        
        # 영역별 권고사항
        for domain, score_info in domain_scores.items():
            if score_info.percentage < 60:  # 60% 미만인 영역
                if domain == CognitiveDomain.ORIENTATION:
                    recommendations.append("시간과 장소에 대한 인식을 돕는 일상적인 대화를 늘려보세요.")
                elif domain == CognitiveDomain.MEMORY:
                    recommendations.append("간단한 기억 게임이나 과거 추억 대화를 자주 나누어 보세요.")
                elif domain == CognitiveDomain.ATTENTION:
                    recommendations.append("숫자나 단어를 반복하는 간단한 집중력 훈련을 해보세요.")
                elif domain == CognitiveDomain.EXECUTIVE:
                    recommendations.append("카테고리별 단어 찾기 게임을 통해 사고력을 향상시켜 보세요.")
                elif domain == CognitiveDomain.LANGUAGE:
                    recommendations.append("사물의 이름 말하기나 간단한 지시 따르기 연습을 해보세요.")
        
        # 전체적인 권고사항
        if total_score < 15:  # 22점 만점 중 15점 미만
            recommendations.append("전문적인 인지기능 평가를 받아보시는 것을 권합니다.")
        
        if not recommendations:
            recommendations.append("현재 인지기능 상태가 양호합니다. 꾸준한 대화와 활동을 유지하세요.")
        
        return recommendations
    
    def analyze_conversation_patterns(self, evaluation: CISTEvaluation) -> Dict[str, Any]:
        """대화 패턴 분석"""
        
        patterns = {
            "response_consistency": 0.0,  # 응답 일관성
            "topic_adherence": 0.0,  # 주제 유지도
            "cognitive_fluctuation": 0.0,  # 인지적 변동성
            "engagement_level": 0.0  # 참여도
        }
        
        # 응답이 있는 문항들 분석
        completed_responses = [
            response for response in evaluation.item_responses.values()
            if response.status == "completed"
        ]
        
        if completed_responses:
            # 응답 길이의 일관성
            response_lengths = [len(r.user_response.split()) for r in completed_responses]
            if response_lengths:
                length_variance = sum((l - sum(response_lengths)/len(response_lengths))**2 for l in response_lengths) / len(response_lengths)
                patterns["response_consistency"] = max(0.0, 1.0 - length_variance / 100.0)
            
            # 참여도 (응답 완성도)
            patterns["engagement_level"] = len(completed_responses) / len(evaluation.item_responses) if evaluation.item_responses else 0.0
            
            # 기본값 설정
            patterns["topic_adherence"] = 0.7  # 기본적으로 양호한 것으로 가정
            patterns["cognitive_fluctuation"] = 0.3  # 기본적으로 낮은 변동성으로 가정
        
        return patterns
    
    async def generate_detailed_report(self, evaluation: CISTEvaluation) -> str:
        """상세 평가 보고서 생성"""
        
        summary = await self.generate_evaluation_summary(evaluation)
        patterns = self.analyze_conversation_patterns(evaluation)
        
        system_prompt = f"""
        치매 선별검사(CIST) 결과를 바탕으로 상세한 평가 보고서를 작성해주세요.
        
        평가 결과:
        - 총점: {summary.total_score}/{summary.max_score}점 ({summary.percentage:.1f}%)
        - 지남력: {summary.orientation_score}점
        - 기억력: {summary.memory_score}점  
        - 주의력: {summary.attention_score}점
        - 집행기능: {summary.executive_score}점
        - 언어기능: {summary.language_score}점
        - 위험도: {summary.risk_level}
        
        대화 패턴:
        - 응답 일관성: {patterns['response_consistency']:.2f}
        - 주제 유지도: {patterns['topic_adherence']:.2f}  
        - 인지적 변동성: {patterns['cognitive_fluctuation']:.2f}
        - 참여도: {patterns['engagement_level']:.2f}
        
        다음 구조로 보고서를 작성해주세요:
        
        1. 전반적 평가
        2. 영역별 세부 평가
        3. 대화 중 관찰된 특징
        4. 권고사항
        5. 추후 관리 방향
        
        의료진이 아닌 가족이나 돌봄제공자가 이해하기 쉽게 작성해주세요.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "상세 평가 보고서를 작성해주세요."}
        ]
        
        # langchain 메시지 형식으로 변환 필요한 경우를 대비한 대안
        try:
            response = await self.llm.ainvoke(system_prompt + "\n\n상세 평가 보고서를 작성해주세요.")
            return response.content
        except:
            # 기본 보고서 반환
            return self._generate_basic_report(summary, patterns)
    
    def _generate_basic_report(self, summary: EvaluationSummary, patterns: Dict[str, Any]) -> str:
        """기본 평가 보고서 생성 (LLM 실패 시 대안)"""
        
        report = f"""
# CIST 인지기능 평가 보고서

## 전반적 평가
총 {summary.max_score}점 만점 중 {summary.total_score}점을 획득하여 {summary.percentage:.1f}%의 수행률을 보였습니다.
위험도는 '{summary.risk_level}'로 평가됩니다.

## 영역별 세부 평가
- **지남력**: {summary.orientation_score}점 - 시간과 장소에 대한 인식 능력
- **기억력**: {summary.memory_score}점 - 정보를 기억하고 회상하는 능력  
- **주의력**: {summary.attention_score}점 - 집중하고 정보를 처리하는 능력
- **집행기능**: {summary.executive_score}점 - 계획하고 추론하는 능력
- **언어기능**: {summary.language_score}점 - 언어를 이해하고 표현하는 능력

## 대화 중 관찰된 특징
- 응답 일관성: {patterns['response_consistency']:.0%}
- 주제 유지도: {patterns['topic_adherence']:.0%}
- 참여도: {patterns['engagement_level']:.0%}

## 권고사항
"""
        
        for rec in summary.recommendations:
            report += f"- {rec}\n"
        
        report += f"""
## 추후 관리 방향
정기적인 대화와 인지 활동을 통해 현재 기능을 유지하고 향상시키는 것이 중요합니다.
필요시 전문의와 상담하여 추가적인 평가나 개입을 고려해보세요.

*평가일시: {summary.completed_at.strftime('%Y-%m-%d %H:%M')}*
"""
        
        return report.strip()