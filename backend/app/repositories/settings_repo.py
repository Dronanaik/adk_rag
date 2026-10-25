"""Async SQLAlchemy repository for singleton system_settings and database health telemetry."""

import time
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import SystemSetting
from app.schemas.settings import SystemSettingsUpdateRequest


class SettingsRepository:
    """Data access layer for Table 1 (system_settings)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_settings(self) -> SystemSetting:
        """Fetch the singleton system_settings row (id=1), creating defaults if absent."""
        stmt = select(SystemSetting).where(SystemSetting.id == 1)
        result = await self._session.execute(stmt)
        setting = result.scalar_one_or_none()
        if setting is not None:
            return setting

        setting = SystemSetting(
            id=1,
            top_k_chunks=5,
            similarity_threshold=Decimal("0.65"),
            max_kg_hops=2,
            max_agent_steps=5,
            turn_timeout_seconds=30,
            auto_consolidate_memory=True,
            strict_abstention_mode=True,
        )
        self._session.add(setting)
        await self._session.commit()
        await self._session.refresh(setting)
        return setting

    async def update_settings(self, updates: SystemSettingsUpdateRequest) -> SystemSetting:
        """Apply partial or full updates to the singleton system_settings row."""
        setting = await self.get_settings()
        if updates.top_k_chunks is not None:
            setting.top_k_chunks = updates.top_k_chunks
        if updates.similarity_threshold is not None:
            setting.similarity_threshold = Decimal(f"{updates.similarity_threshold:.2f}")
        if updates.max_kg_hops is not None:
            setting.max_kg_hops = updates.max_kg_hops
        if updates.max_agent_steps is not None:
            setting.max_agent_steps = updates.max_agent_steps
        if updates.turn_timeout_seconds is not None:
            setting.turn_timeout_seconds = updates.turn_timeout_seconds
        if updates.auto_consolidate_memory is not None:
            setting.auto_consolidate_memory = updates.auto_consolidate_memory
        if updates.strict_abstention_mode is not None:
            setting.strict_abstention_mode = updates.strict_abstention_mode

        setting.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(setting)
        return setting

    async def measure_db_latency_ms(self) -> float:
        """Execute a lightweight SELECT 1 query and return round-trip latency in milliseconds."""
        start = time.perf_counter()
        await self._session.execute(text("SELECT 1"))
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return round(elapsed_ms, 2)
