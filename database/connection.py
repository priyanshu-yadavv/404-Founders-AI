"""
404 FOUNDERS — Database Connection & Lifecycle Manager
Manages SQLite connection pooling, WAL mode, foreign key constraints,
atomic transactions, and automated migration execution.
"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import threading
from typing import Generator, Optional

from database.schema import apply_migrations


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "memory.db"


class DatabaseManager:
    """
    Thread-safe SQLite database manager.
    Enforces ACID transactions, WAL mode, and automatic schema migration.
    """

    _instance: Optional["DatabaseManager"] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        if db_path is None:
            self.db_path = DEFAULT_DB_PATH
        elif db_path == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = Path(db_path)

        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._local = threading.local()
        # Initialize schema and run migrations on startup
        with self.get_connection() as conn:
            apply_migrations(conn)

    @classmethod
    def get_instance(cls, db_path: Optional[Path | str] = None) -> "DatabaseManager":
        """Singleton accessor for application-wide database manager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db_path=db_path)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (useful for isolated unit test fixtures)."""
        with cls._lock:
            cls._instance = None

    def _create_connection(self) -> sqlite3.Connection:
        """Create and configure a new SQLite connection."""
        db_target = str(self.db_path)
        conn = sqlite3.connect(db_target, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        # Performance and safety pragmas
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        if self.db_path != ":memory:":
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.execute("PRAGMA busy_timeout = 5000;")
        cursor.close()
        return conn

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding a thread-local SQLite connection with automatic commit/rollback."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = self._create_connection()

        conn = self._local.conn
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def close(self) -> None:
        """Close connection for current thread."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    def backup_to_file(self, target_path: Path | str) -> int:
        """Perform online atomic database backup to destination file."""
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        dest_conn = sqlite3.connect(str(target_path))
        with self.get_connection() as src_conn:
            src_conn.backup(dest_conn)
        dest_conn.close()
        return target_path.stat().st_size
