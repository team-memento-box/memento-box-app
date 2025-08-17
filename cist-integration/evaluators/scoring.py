"""
CIST 점수 계산 및 평가 로직
"""

import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from models.cist_items import cist_registry, CognitiveDomain
from schemas.evaluation import ItemResponse, DomainScore, CISTEvaluation, EvaluationStatus


class CISTScorer:
    """CIST 점수 계산기"""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, api_key: Optional[str] = None, model: str = "gpt-4.1-nano"):
        if llm:
            self.llm = llm
        elif api_key:
            self.llm = ChatOpenAI(temperature=0.1, model=model, api_key=api_key)
        else:
            self.llm = None  # LLM 없이 기본 평가만 수행
        self.registry = cist_registry
    
    def evaluate_response(self, item_id: str, user_response: str, 
                         context: Optional[Dict] = None) -> ItemResponse:
        """개별 문항 응답 평가"""
        
        item = self.registry.get_item(item_id)
        if not item:
            raise ValueError(f"Unknown item_id: {item_id}")
        
        # 문항별 특화된 평가 로직
        if item_id == "orientation_time":
            return self._evaluate_time_orientation(user_response, context)
        elif item_id == "orientation_place":
            return self._evaluate_place_orientation(user_response, context)
        elif item_id == "memory_registration":
            return self._evaluate_memory_registration(user_response, context)
        elif item_id == "memory_recall":
            return self._evaluate_memory_recall(user_response, context)
        elif item_id == "attention_forward":
            return self._evaluate_attention_forward(user_response, context)
        elif item_id == "attention_backward":
            return self._evaluate_attention_backward(user_response, context)
        elif item_id == "executive_verbal_fluency":
            return self._evaluate_verbal_fluency(user_response, context)
        elif item_id == "language_naming":
            return self._evaluate_naming(user_response, context)
        elif item_id == "language_comprehension":
            return self._evaluate_comprehension(user_response, context)
        else:
            return self._evaluate_with_llm(item_id, user_response, context)
    
    def _evaluate_time_orientation(self, response: str, context: Optional[Dict] = None) -> ItemResponse:
        """시간 지남력 평가"""
        current_date = datetime.now()
        
        # 연도, 월, 일, 요일 추출
        year_match = re.search(r'20\d{2}|19\d{2}', response)
        month_match = re.search(r'(\d{1,2})월|(\d{1,2})-|/(\d{1,2})', response) 
        day_match = re.search(r'(\d{1,2})일|(\d{1,2})번째', response)
        
        # 요일 키워드 검색
        weekdays = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
        weekday_found = any(day in response for day in weekdays)
        
        score = 0
        details = {}
        
        if year_match and int(year_match.group()) == current_date.year:
            score += 1
            details['year'] = 'correct'
        
        if month_match:
            month_num = None
            for group in month_match.groups():
                if group:
                    month_num = int(group)
                    break
            if month_num == current_date.month:
                score += 1
                details['month'] = 'correct'
        
        if day_match:
            day_num = None
            for group in day_match.groups():
                if group:
                    day_num = int(group)
                    break  
            if day_num == current_date.day:
                score += 1
                details['day'] = 'correct'
        
        if weekday_found:
            current_weekday = weekdays[current_date.weekday()]
            if current_weekday in response:
                score += 1
                details['weekday'] = 'correct'
        
        return ItemResponse(
            item_id="orientation_time",
            user_response=response,
            raw_score=score,
            max_score=4,
            evaluation_details=details,
            status=EvaluationStatus.COMPLETED
        )
    
    def _evaluate_place_orientation(self, response: str, context: Optional[Dict] = None) -> ItemResponse:
        """장소 지남력 평가"""
        
        if self.llm:
            # LLM을 사용하여 장소 답변의 적절성 평가
            system_prompt = """
            사용자가 현재 위치에 대해 답변했습니다. 
            답변이 구체적이고 현실적인 장소를 언급했는지 평가해주세요.
            
            점수 기준:
            - 1점: 구체적인 장소명 또는 장소 유형을 정확히 언급 (예: "집", "병원", "요양원", "서울 강남구")
            - 0점: 모름, 부정확하거나 모호한 답변
            
            JSON 형태로 {"score": 0 또는 1, "reason": "평가 근거"} 반환해주세요.
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"사용자 응답: {response}")
            ]
            
            result = self.llm.invoke(messages)
            
            try:
                import json
                evaluation = json.loads(result.content)
                score = evaluation.get("score", 0)
                reason = evaluation.get("reason", "")
            except:
                score = 1 if any(keyword in response for keyword in ['집', '병원', '요양원', '센터']) else 0
                reason = "키워드 기반 평가"
        else:
            # LLM 없이 키워드 기반 평가
            score = 1 if any(keyword in response for keyword in ['집', '병원', '요양원', '센터', '댁', '가정']) else 0
            reason = "키워드 기반 평가 (LLM 없음)"
        
        return ItemResponse(
            item_id="orientation_place",
            user_response=response,
            raw_score=score,
            max_score=1,
            evaluation_details={"reason": reason},
            status=EvaluationStatus.COMPLETED
        )
    
    def _evaluate_memory_registration(self, response: str, context: Optional[Dict] = None) -> ItemResponse:
        """기억 등록 평가"""
        target_sentence = context.get("target_sentence", "") if context else ""
        
        if not target_sentence:
            return ItemResponse(
                item_id="memory_registration",
                user_response=response,
                raw_score=0,
                max_score=5,
                evaluation_details={"error": "target_sentence not provided"},
                status=EvaluationStatus.COMPLETED
            )
        
        # 문장 유사도 계산 (간단한 버전)
        target_words = target_sentence.split()
        response_words = response.split()
        
        matching_words = 0
        for word in target_words:
            if word in response:
                matching_words += 1
        
        # 순서도 고려한 점수 계산
        similarity_ratio = matching_words / len(target_words) if target_words else 0
        score = min(5, int(similarity_ratio * 5))
        
        return ItemResponse(
            item_id="memory_registration", 
            user_response=response,
            raw_score=score,
            max_score=5,
            evaluation_details={
                "target_sentence": target_sentence,
                "matching_words": matching_words,
                "total_words": len(target_words),
                "similarity_ratio": similarity_ratio
            },
            status=EvaluationStatus.COMPLETED
        )
    
    def _evaluate_memory_recall(self, response: str, context: Optional[Dict] = None) -> ItemResponse:
        """기억 회상 평가 (기억 등록과 동일한 로직)"""
        return self._evaluate_memory_registration(response, context)
    
    def _evaluate_attention_forward(self, response: str, context: Optional[Dict] = None) -> ItemResponse:
        """숫자 바로 따라말하기 평가"""
        target_digits = context.get("target_digits", "") if context else ""
        
        # 응답에서 숫자만 추출
        response_digits = re.findall(r'\d', response)
        target_digit_list = re.findall(r'\d', target_digits)
        
        # 순서와 정확성 모두 확인
        correct = response_digits == target_digit_list
        score = 2 if correct else 0
        
        return ItemResponse(
            item_id="attention_forward",
            user_response=response,
            raw_score=score,
            max_score=2,
            evaluation_details={
                "target_digits": target_digit_list,
                "response_digits": response_digits,
                "correct": correct
            },
            status=EvaluationStatus.COMPLETED
        )
    
    def _evaluate_attention_backward(self, response: str, context: Optional[Dict] = None) -> ItemResponse:
        """숫자 거꾸로 말하기 평가"""
        target_digits = context.get("target_digits", "") if context else ""
        
        response_digits = re.findall(r'\d', response)
        target_digit_list = re.findall(r'\d', target_digits)
        target_reversed = target_digit_list[::-1]
        
        correct = response_digits == target_reversed
        score = 1 if correct else 0
        
        return ItemResponse(
            item_id="attention_backward",
            user_response=response,
            raw_score=score,
            max_score=1,
            evaluation_details={
                "target_digits": target_digit_list,
                "target_reversed": target_reversed,
                "response_digits": response_digits,
                "correct": correct
            },
            status=EvaluationStatus.COMPLETED
        )
    
    def _evaluate_verbal_fluency(self, response: str, context: Optional[Dict] = None) -> ItemResponse:
        """언어 유창성 평가 (과일/채소 개수)"""
        
        # 과일/채소 키워드 리스트
        fruits = ['사과', '배', '포도', '감', '귤', '오렌지', '바나나', '딸기', '수박', '참외', '복숭아', '자두', '살구', '체리', '키위', '파인애플', '망고', '레몬']
        vegetables = ['배추', '무', '당근', '양파', '마늘', '생강', '고추', '피망', '토마토', '오이', '가지', '호박', '감자', '고구마', '옥수수', '콩', '시금치', '상추']
        
        all_produce = fruits + vegetables
        
        # 응답에서 과일/채소 개수 세기
        found_items = []
        for item in all_produce:
            if item in response:
                found_items.append(item)
        
        count = len(set(found_items))  # 중복 제거
        
        # 점수 계산
        if count >= 10:
            score = 2
        elif count >= 6:
            score = 1
        else:
            score = 0
        
        return ItemResponse(
            item_id="executive_verbal_fluency",
            user_response=response,
            raw_score=score,
            max_score=2,
            evaluation_details={
                "found_items": found_items,
                "count": count
            },
            status=EvaluationStatus.COMPLETED
        )
    
    def _evaluate_naming(self, response: str, context: Optional[Dict] = None) -> ItemResponse:
        """이름대기 평가"""
        target_object = context.get("target_object", "") if context else ""
        
        # 간단한 키워드 매칭으로 평가
        correct = target_object.lower() in response.lower() if target_object else False
        score = 1 if correct else 0
        
        return ItemResponse(
            item_id="language_naming",
            user_response=response,
            raw_score=score,
            max_score=1,
            evaluation_details={
                "target_object": target_object,
                "correct": correct
            },
            status=EvaluationStatus.COMPLETED
        )
    
    def _evaluate_comprehension(self, response: str, context: Optional[Dict] = None) -> ItemResponse:
        """이해력 평가"""
        instruction = context.get("instruction", "") if context else ""
        expected_response = context.get("expected_response", "") if context else ""
        
        # 지시사항을 제대로 따랐는지 확인
        followed = expected_response.lower() in response.lower() if expected_response else True
        score = 1 if followed else 0
        
        return ItemResponse(
            item_id="language_comprehension",
            user_response=response,
            raw_score=score,
            max_score=1,
            evaluation_details={
                "instruction": instruction,
                "expected_response": expected_response,
                "followed": followed
            },
            status=EvaluationStatus.COMPLETED
        )
    
    def _evaluate_with_llm(self, item_id: str, response: str, context: Optional[Dict] = None) -> ItemResponse:
        """LLM을 사용한 일반적인 평가"""
        item = self.registry.get_item(item_id)
        
        if not self.llm:
            # LLM이 없으면 기본 점수 반환
            return ItemResponse(
                item_id=item_id,
                user_response=response,
                raw_score=0,
                max_score=item.max_score,
                evaluation_details={"reason": "LLM 평가기 없음"},
                status=EvaluationStatus.COMPLETED
            )
        
        system_prompt = f"""
        CIST 인지기능 평가를 수행합니다.
        
        평가 문항: {item.name}
        설명: {item.description}  
        최대 점수: {item.max_score}
        평가 기준: {item.evaluation_criteria}
        
        사용자의 응답을 평가하여 0부터 {item.max_score}점 사이의 점수를 부여해주세요.
        JSON 형태로 {{"score": 점수, "reason": "평가 근거"}} 반환해주세요.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"사용자 응답: {response}")
        ]
        
        result = self.llm.invoke(messages)
        
        try:
            import json
            evaluation = json.loads(result.content)
            score = min(item.max_score, max(0, evaluation.get("score", 0)))
            reason = evaluation.get("reason", "")
        except:
            score = 0
            reason = "LLM 평가 실패"
        
        return ItemResponse(
            item_id=item_id,
            user_response=response,
            raw_score=score,
            max_score=item.max_score,
            evaluation_details={"reason": reason},
            status=EvaluationStatus.COMPLETED
        )
    
    def calculate_domain_scores(self, evaluation: CISTEvaluation) -> Dict[CognitiveDomain, DomainScore]:
        """영역별 점수 계산"""
        domain_scores = {}
        
        for domain in CognitiveDomain:
            domain_items = self.registry.get_items_by_domain(domain)
            
            total_score = 0
            max_score = 0
            completed_items = 0
            
            for item in domain_items:
                max_score += item.max_score
                
                if item.id in evaluation.item_responses:
                    response = evaluation.item_responses[item.id]
                    if response.status == EvaluationStatus.COMPLETED:
                        total_score += response.raw_score
                        completed_items += 1
            
            percentage = (total_score / max_score * 100) if max_score > 0 else 0
            
            domain_scores[domain] = DomainScore(
                domain=domain,
                total_score=total_score,
                max_score=max_score,
                percentage=percentage,
                items_completed=completed_items,
                items_total=len(domain_items)
            )
        
        return domain_scores
    
    def calculate_total_score(self, evaluation: CISTEvaluation) -> Tuple[int, float]:
        """전체 점수 계산"""
        total_score = sum(
            response.raw_score 
            for response in evaluation.item_responses.values()
            if response.status == EvaluationStatus.COMPLETED
        )
        
        max_score = self.registry.get_total_possible_score()
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        return total_score, percentage