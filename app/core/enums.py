import enum


class JobStatus(str, enum.Enum):
    """Controlled statuses for evaluation jobs."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GateOutcome(str, enum.Enum):
    """Quality gate evaluation outcomes."""

    PASS = "pass"
    FAIL = "fail"
