"""
Database models and connection management for PostgreSQL.
Optional - the system works without it for basic functionality.
"""
import logging
from typing import Optional, AsyncGenerator
from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, Date, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.future import select

from src.config import get_settings

logger = logging.getLogger(__name__)

Base = declarative_base()


# ============================================================
# DATABASE MODELS
# ============================================================

class Matter(Base):
    """Legal matter/case database model."""
    __tablename__ = "matters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    matter_id = Column(String(50), unique=True, nullable=False, index=True)
    client_name = Column(String(200), nullable=False)
    matter_type = Column(String(100), nullable=False)
    jurisdiction = Column(String(100), nullable=False)
    responsible_attorney = Column(String(200))
    opposing_parties = Column(JSON, default=list)
    contract_value = Column(Float)
    open_date = Column(Date, default=date.today)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = relationship("Document", back_populates="matter", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="matter", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntry", back_populates="matter", cascade="all, delete-orphan")


class Document(Base):
    """Document database model."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(50), unique=True, nullable=False, index=True)
    matter_id = Column(String(50), ForeignKey("matters.matter_id"), nullable=False)
    document_name = Column(String(200), nullable=False)
    document_type = Column(String(100))
    file_path = Column(String(500))
    file_size = Column(Integer)
    word_count = Column(Integer)
    created_by = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    matter = relationship("Matter", back_populates="documents")


class Deadline(Base):
    """Deadline database model."""
    __tablename__ = "deadlines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deadline_id = Column(String(50), unique=True, nullable=False, index=True)
    matter_id = Column(String(50), ForeignKey("matters.matter_id"), nullable=False)
    description = Column(Text, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    urgency = Column(String(50), default="important")
    category = Column(String(100))
    court_rule_reference = Column(String(200))
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    matter = relationship("Matter", back_populates="deadlines")


class TimeEntry(Base):
    """Time entry database model for billing."""
    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String(50), unique=True, nullable=False, index=True)
    matter_id = Column(String(50), ForeignKey("matters.matter_id"), nullable=False)
    timekeeper_id = Column(String(50), nullable=False)
    timekeeper_name = Column(String(200), nullable=False)
    date = Column(Date, nullable=False)
    hours = Column(Float, nullable=False)
    description = Column(Text, nullable=False)
    billing_code = Column(String(50))
    billable = Column(Boolean, default=True)
    rate = Column(Float)
    is_invoiced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    matter = relationship("Matter", back_populates="time_entries")


class Invoice(Base):
    """Invoice database model."""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(50), unique=True, nullable=False, index=True)
    matter_id = Column(String(50), ForeignKey("matters.matter_id"), nullable=False)
    invoice_number = Column(String(50), nullable=False)
    billing_period_start = Column(Date)
    billing_period_end = Column(Date)
    total_hours = Column(Float)
    total_fees = Column(Float)
    total_expenses = Column(Float)
    total_amount = Column(Float)
    status = Column(String(50), default="draft")
    invoice_html_path = Column(String(500))
    invoice_pdf_path = Column(String(500))
    sent_at = Column(DateTime)
    paid_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    matter = relationship("Matter")


class User(Base):
    """User database model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    role = Column(String(50), default="attorney")  # attorney, paralegal, admin
    firm_id = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    hashed_password = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)


class Firm(Base):
    """Law firm database model."""
    __tablename__ = "firms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    firm_id = Column(String(50), unique=True, nullable=False, index=True)
    firm_name = Column(String(200), nullable=False)
    jurisdiction = Column(String(100), nullable=False)
    practice_areas = Column(JSON, default=list)
    billing_increment = Column(Float, default=0.1)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# DATABASE CONNECTION
# ============================================================

class DatabaseManager:
    """
    Async database connection manager.
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL
        """
        settings = get_settings()
        self.database_url = database_url or settings.database_async_url or settings.database_url

        # Convert sync URL to async if needed
        if self.database_url and not self.database_url.startswith("postgresql+asyncpg"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )

        self.engine = None
        self.async_session_maker = None
        self._initialized = False

    async def connect(self):
        """Initialize database connection."""
        if self._initialized:
            return

        if not self.database_url:
            logger.warning("No database URL provided. Running without database.")
            self._initialized = True
            return

        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_pre_ping=True,
            )

            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self._initialized = True
            logger.info("Database connection established")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self._initialized = True  # Continue without database

    async def disconnect(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session.

        Yields:
            AsyncSession instance
        """
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized")

        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    # ============================================================
    # MATTER OPERATIONS
    # ============================================================

    async def get_matter(self, matter_id: str) -> Optional[Matter]:
        """Get matter by ID."""
        if not self.async_session_maker:
            return None

        async with self.async_session_maker() as session:
            result = await session.execute(
                select(Matter).where(Matter.matter_id == matter_id)
            )
            return result.scalar_one_or_none()

    async def create_matter(self, matter_data: dict) -> Matter:
        """Create new matter."""
        async with self.async_session_maker() as session:
            matter = Matter(**matter_data)
            session.add(matter)
            await session.commit()
            await session.refresh(matter)
            return matter

    async def update_matter(self, matter_id: str, updates: dict) -> Optional[Matter]:
        """Update matter."""
        async with self.async_session_maker() as session:
            matter = await self.get_matter(matter_id)
            if matter:
                for key, value in updates.items():
                    setattr(matter, key, value)
                await session.commit()
                await session.refresh(matter)
            return matter

    async def delete_matter(self, matter_id: str) -> bool:
        """Delete matter."""
        async with self.async_session_maker() as session:
            matter = await self.get_matter(matter_id)
            if matter:
                await session.delete(matter)
                await session.commit()
                return True
            return False

    # ============================================================
    # DEADLINE OPERATIONS
    # ============================================================

    async def get_deadlines_by_matter(self, matter_id: str) -> list[Deadline]:
        """Get all deadlines for a matter."""
        if not self.async_session_maker:
            return []

        async with self.async_session_maker() as session:
            result = await session.execute(
                select(Deadline)
                .where(Deadline.matter_id == matter_id)
                .order_by(Deadline.due_date)
            )
            return result.scalars().all()

    async def create_deadline(self, deadline_data: dict) -> Deadline:
        """Create new deadline."""
        async with self.async_session_maker() as session:
            deadline = Deadline(**deadline_data)
            session.add(deadline)
            await session.commit()
            await session.refresh(deadline)
            return deadline

    # ============================================================
    # TIME ENTRY OPERATIONS
    # ============================================================

    async def get_time_entries(
        self,
        matter_id: str,
        start_date: date,
        end_date: date,
    ) -> list[TimeEntry]:
        """Get time entries for a matter in date range."""
        if not self.async_session_maker:
            return []

        async with self.async_session_maker() as session:
            result = await session.execute(
                select(TimeEntry)
                .where(TimeEntry.matter_id == matter_id)
                .where(TimeEntry.date >= start_date)
                .where(TimeEntry.date <= end_date)
                .order_by(TimeEntry.date)
            )
            return result.scalars().all()

    async def create_time_entry(self, entry_data: dict) -> TimeEntry:
        """Create new time entry."""
        async with self.async_session_maker() as session:
            entry = TimeEntry(**entry_data)
            session.add(entry)
            await session.commit()
            await session.refresh(entry)
            return entry


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get or create database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def init_database():
    """Initialize database connection."""
    db_manager = get_database_manager()
    await db_manager.connect()


async def close_database():
    """Close database connection."""
    db_manager = get_database_manager()
    await db_manager.disconnect()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    db_manager = get_database_manager()
    async for session in db_manager.get_session():
        yield session
