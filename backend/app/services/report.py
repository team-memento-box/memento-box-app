from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from db.models.anomaly_report import AnomalyReport
from db.models.conversation import Conversation
from db.models.photo import Photo
from schemas.report import AnomalyReportResponse, AnomalyReportListResponse


async def get_anomaly_reports(
    db: AsyncSession,
    family_id: UUID  # 로그인한 유저의 family_id를 외부에서 주입 받는다고 가정
) -> dict:
    """
    해당 가족(family_id)의 모든 이상 보고서를 최신순으로 조회합니다.
    """
    try:
        stmt = (
            select(AnomalyReport)
            .join(AnomalyReport.conversation)
            .join(Conversation.photo)
            .options(
                joinedload(AnomalyReport.conversation).joinedload(Conversation.photo)
            )
            .where(Photo.family_id == family_id)
            .order_by(Conversation.created_at.desc())
        )

        result = await db.execute(stmt)
        reports = result.scalars().all()

        # 응답 구성
        return AnomalyReportListResponse(
            status="ok",
            data=[
                AnomalyReportResponse(
                    reportId=r.id,
                    convId=r.conv_id,
                    anomalyReport=r.anomaly_report,
                    anomalyTurn=r.anomaly_turn,
                    created_at=r.conversation.created_at,
                    imageUrl=r.conversation.photo.url
                )
                for r in reports
            ]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리포트 조회 실패: {str(e)}")
    

async def get_anomaly_report_detail(
    db: AsyncSession,
    report_id: UUID,
    family_id: UUID
) -> AnomalyReportResponse:
    """
    특정 이상 보고서의 상세 정보를 조회합니다.
    """
    try:
        stmt = (
            select(AnomalyReport)
            .join(AnomalyReport.conversation)
            .join(Conversation.photo)
            .where(
                AnomalyReport.id == report_id,
                Photo.family_id == family_id
            )
            .options(
                joinedload(AnomalyReport.conversation).joinedload(Conversation.photo)
            )
        )

        result = await db.execute(stmt)
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="리포트를 찾을 수 없거나 접근 권한이 없습니다.")

        return AnomalyReportResponse(
            reportId=report.id,
            convId=report.conv_id,
            anomalyReport=report.anomaly_report,
            anomalyTurn=report.anomaly_turn,
            created_at=report.conversation.created_at,
            imageUrl=report.conversation.photo.url
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리포트 조회 실패: {str(e)}")
    

    