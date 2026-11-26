"""The split lock (E1). Moved to fjordvik_service.common.lock in phase 3; this name stays so
phase 2's imports don't change."""

from ..common.lock import LockError, check_lock, write_lock

__all__ = ["LockError", "check_lock", "write_lock"]
