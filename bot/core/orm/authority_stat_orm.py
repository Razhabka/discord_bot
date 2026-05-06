from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .base_async_orm import AsyncORM
from core.models import AuthorityStatistic


class AuthorityStatORM(AsyncORM):

    def __init__(self):
        super().__init__()

    async def replace_snapshot_data(
        self,
        session: AsyncSession,
        snapshot_overall_ms: int,
        snapshot_date: str,
        rows: list[tuple[str, int]]
    ) -> None:
        await session.execute(
            delete(AuthorityStatistic).where(
                AuthorityStatistic.snapshot_overall_ms == snapshot_overall_ms
            )
        )
        for nickname, auto_without_cape in rows:
            await self.insert_data(
                session,
                AuthorityStatistic,
                snapshot_overall_ms=snapshot_overall_ms,
                snapshot_date=snapshot_date,
                nickname=nickname,
                auto_without_cape=auto_without_cape
            )

    async def _get_snapshot_overall_ms_for_date(
        self,
        session: AsyncSession,
        target_date: str
    ) -> int | None:
        stmt = (
            select(func.max(AuthorityStatistic.snapshot_overall_ms))
            .where(AuthorityStatistic.snapshot_date <= target_date)
        )
        return (await session.execute(stmt)).scalar()

    async def _get_first_snapshot_for_exact_date(
        self,
        session: AsyncSession,
        target_date: str
    ) -> int | None:
        stmt = (
            select(func.min(AuthorityStatistic.snapshot_overall_ms))
            .where(AuthorityStatistic.snapshot_date == target_date)
        )
        return (await session.execute(stmt)).scalar()

    async def _get_last_snapshot_for_exact_date(
        self,
        session: AsyncSession,
        target_date: str
    ) -> int | None:
        stmt = (
            select(func.max(AuthorityStatistic.snapshot_overall_ms))
            .where(AuthorityStatistic.snapshot_date == target_date)
        )
        return (await session.execute(stmt)).scalar()

    async def get_delta_for_period(
        self,
        session: AsyncSession,
        date_from: str,
        date_to: str,
        limit: int = 25
    ) -> tuple[list[tuple[str, int, int, int]], tuple[int, int] | None]:
        # Start boundary: first snapshot of date_from day (if exists),
        # otherwise the latest snapshot not later than date_from.
        start_snapshot = await self._get_first_snapshot_for_exact_date(
            session=session,
            target_date=date_from
        )
        if start_snapshot is None:
            start_snapshot = await self._get_snapshot_overall_ms_for_date(
                session=session,
                target_date=date_from
            )

        # End boundary: last snapshot of date_to day (if exists),
        # otherwise the latest snapshot not later than date_to.
        end_snapshot = await self._get_last_snapshot_for_exact_date(
            session=session,
            target_date=date_to
        )
        if end_snapshot is None:
            end_snapshot = await self._get_snapshot_overall_ms_for_date(
                session=session,
                target_date=date_to
            )

        if start_snapshot is None or end_snapshot is None:
            return [], None

        if start_snapshot > end_snapshot:
            return [], (start_snapshot, end_snapshot)

        start_rows_stmt = (
            select(AuthorityStatistic.nickname, AuthorityStatistic.auto_without_cape)
            .where(AuthorityStatistic.snapshot_overall_ms == start_snapshot)
        )
        end_rows_stmt = (
            select(AuthorityStatistic.nickname, AuthorityStatistic.auto_without_cape)
            .where(AuthorityStatistic.snapshot_overall_ms == end_snapshot)
        )

        start_rows = await session.execute(start_rows_stmt)
        end_rows = await session.execute(end_rows_stmt)

        start_map = {row[0]: int(row[1]) for row in start_rows.all()}
        end_map = {row[0]: int(row[1]) for row in end_rows.all()}

        result_rows: list[tuple[str, int, int, int]] = []
        for nickname, end_value in end_map.items():
            start_value = start_map.get(nickname, 0)
            delta_value = end_value - start_value
            result_rows.append((nickname, delta_value, start_value, end_value))

        result_rows.sort(key=lambda row: row[1], reverse=True)
        return result_rows[:limit], (start_snapshot, end_snapshot)

    async def get_snapshot_dates(
        self,
        session: AsyncSession,
        start_snapshot: int,
        end_snapshot: int
    ) -> tuple[str | None, str | None]:
        start_date_stmt = (
            select(AuthorityStatistic.snapshot_date)
            .where(AuthorityStatistic.snapshot_overall_ms == start_snapshot)
            .limit(1)
        )
        end_date_stmt = (
            select(AuthorityStatistic.snapshot_date)
            .where(AuthorityStatistic.snapshot_overall_ms == end_snapshot)
            .limit(1)
        )
        start_date = (await session.execute(start_date_stmt)).scalar()
        end_date = (await session.execute(end_date_stmt)).scalar()
        return start_date, end_date

    async def get_period_meta(
        self,
        session: AsyncSession,
        date_from: str,
        date_to: str
    ) -> tuple[int, int]:
        total_rows_stmt = (
            select(func.count(AuthorityStatistic.id))
            .where(
                AuthorityStatistic.snapshot_date >= date_from,
                AuthorityStatistic.snapshot_date <= date_to
            )
        )
        snapshots_stmt = (
            select(func.count(func.distinct(AuthorityStatistic.snapshot_overall_ms)))
            .where(
                AuthorityStatistic.snapshot_date >= date_from,
                AuthorityStatistic.snapshot_date <= date_to
            )
        )
        total_rows = int((await session.execute(total_rows_stmt)).scalar() or 0)
        snapshots = int((await session.execute(snapshots_stmt)).scalar() or 0)
        return total_rows, snapshots


authority_stat_orm = AuthorityStatORM()
