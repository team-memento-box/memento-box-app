from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from db.database import Base
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime, timezone, timedelta

class Photo(Base):
    """
    photos 테이블 모델
    """
    __tablename__ = 'photos'
    __table_args__ = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci" 
    }

    # 사진 id
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # 사진명 (원본 파일명)
    name = Column(String, nullable=True)
    # 사진 저장소 주소 (Azure Blob Storage URL)
    url = Column(Text)
    # 연도
    year = Column(Integer)
    # 계절
    season = Column(String)
    # 설명
    description = Column(Text, nullable = True)
    # 요약 텍스트
    summary_text = Column(JSON, nullable=True)
    # 요약 음성
    summary_voice = Column(JSON, nullable=True)
    # 관계 가족 id
    family_id = Column(UUID(as_uuid=True), ForeignKey('families.id'))
    # 업로드 일자
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=9))))
    # Family ↔ Photo 
    family = relationship("Family", back_populates="photos")
    # Photo ↔ Conversation 
    conversations = relationship("Conversation", back_populates="photo", cascade="all, delete-orphan")
    