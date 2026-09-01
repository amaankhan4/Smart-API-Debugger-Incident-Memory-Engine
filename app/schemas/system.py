from datetime import datetime

from pydantic import BaseModel, computed_field


class VectorQuota(BaseModel):
    """Remaining Upstash Vector allowance for the current UTC day."""

    queries_used: int
    queries_limit: int
    updates_used: int
    updates_limit: int
    queries_exhausted: bool
    updates_exhausted: bool
    resets_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def exhausted(self) -> bool:
        return self.queries_exhausted or self.updates_exhausted
