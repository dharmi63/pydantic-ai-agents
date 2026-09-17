from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Column, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.ext.mutable import MutableList

class Base(DeclarativeBase):
    pass


class TimeStamp(Base):
    __abstract__ = True

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class User(TimeStamp, Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    notes: Mapped[MutableList['Notes']] = relationship("Notes", back_populates="user", cascade="all,delete", passive_deletes=True)
    tasks: Mapped[MutableList['Tasks']] = relationship("Tasks", back_populates="user", cascade="all,delete", passive_deletes=True) 


class Sessions(TimeStamp, Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    

class Messages(TimeStamp, Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(String)


class Notes(TimeStamp, Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    note: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    user: Mapped[MutableList['User']] = relationship("User", back_populates="notes")


class Tasks(TimeStamp, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    user: Mapped[MutableList['User']] = relationship("User", back_populates="tasks")