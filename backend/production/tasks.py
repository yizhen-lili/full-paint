import logging

from core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="production.run_job", max_retries=0)
def run_production_job(self, job_id: str) -> None:
    """
    Phase 1 stub：只把 job status 改為 completed。
    Phase 2 起替換為真實 PBN 引擎呼叫。
    """
    import asyncio

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.pool import NullPool

    from core.config import settings
    from production.models import JobStatusEnum, ProductionJob

    async def _run() -> None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await session.execute(
                select(ProductionJob).where(ProductionJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.warning("run_production_job: job %s not found", job_id)
                return
            job.status = JobStatusEnum.processing
            await session.commit()

            job.status = JobStatusEnum.completed
            await session.commit()
        await engine.dispose()

    asyncio.run(_run())


@celery_app.task(bind=True, name="production.run_post_process", max_retries=0)
def run_post_process_job(self, job_id: str, params: dict) -> None:
    """
    Phase 3 stub：post-process 完成後把 status 改回 completed。
    params 傳入但暫不使用；引擎整合 Phase 替換為真實處理邏輯。
    """
    import asyncio

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.pool import NullPool

    from core.config import settings
    from production.models import JobStatusEnum, ProductionJob

    async def _run() -> None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await session.execute(
                select(ProductionJob).where(ProductionJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.warning("run_post_process_job: job %s not found", job_id)
                return
            job.status = JobStatusEnum.completed
            await session.commit()
        await engine.dispose()

    asyncio.run(_run())


@celery_app.task(bind=True, name="production.cancel_batch")
def cancel_batch_remaining(self, batch_id: str) -> None:
    """Cancel all pending jobs in a batch after a failure."""
    import asyncio

    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.pool import NullPool

    from core.config import settings
    from production.models import JobStatusEnum, ProductionJob

    async def _run() -> None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await session.execute(
                update(ProductionJob)
                .where(
                    ProductionJob.batch_id == batch_id,
                    ProductionJob.status == JobStatusEnum.pending,
                )
                .values(status=JobStatusEnum.cancelled)
            )
            await session.commit()
        await engine.dispose()

    asyncio.run(_run())
