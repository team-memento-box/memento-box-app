from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from db.database import Base
from sqlalchemy.orm import relationship

class AnomaliesReport(Base):
    
    """
    anomalies_reports 테이블 모델

    """
    __tablename__ = 'anomalies_reports'
    __table_args__ = {
        #"schema": "", # 파일명
        #"mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4", 
        "mysql_collate": "utf8mb4_general_ci" 
    }
    # 이상현상 id
    id = Column(UUID(as_uuid=True), primary_key=True)
    # 관계 대화 회기 id
    conv_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id'))
    # 이상대화 내용
    event_report = Column(Text, nullable=True)
    # 이상대화 구간
    event_interval = Column(String, nullable=True)
    # Conversation ↔ AnomaliesReport
    conv_report = relationship("Conversation", back_populates="report")