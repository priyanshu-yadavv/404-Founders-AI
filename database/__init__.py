"""
404 FOUNDERS — Database Subsystem
Provides normalized relational storage, versioned schema migrations, and connection pooling.
"""

from database.connection import DatabaseManager
from database.schema import apply_migrations

__all__ = ["DatabaseManager", "apply_migrations"]
