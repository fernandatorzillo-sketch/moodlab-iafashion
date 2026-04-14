from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.sync_control import SyncControl


async def get_sync_control(session: AsyncSession, job_name: str) -> SyncControl | None:
    result = await session.execute(
        select(SyncControl).where(SyncControl.job_name == job_name)
    )
    return result.scalar_one_or_none()


async def get_last_reference_value(session: AsyncSession, job_name: str) -> str | None:
    control = await get_sync_control(session, job_name)
    if not control:
        return None
    return control.last_reference_value


async def mark_sync_success(
    session: AsyncSession,
    job_name: str,
    reference_value: str,
    notes: str | None = None,
) -> None:
    control = await get_sync_control(session, job_name)

    if not control:
        control = SyncControl(job_name=job_name)
        session.add(control)

    control.status = "success"
    control.last_success_at = datetime.utcnow()
    control.last_reference_value = reference_value
    control.notes = notes


async def mark_sync_error(
    session: AsyncSession,
    job_name: str,
    notes: str | None = None,
) -> None:
    control = await get_sync_control(session, job_name)

    if not control:
        control = SyncControl(job_name=job_name)
        session.add(control)

    control.status = "error"
    control.notes = notes