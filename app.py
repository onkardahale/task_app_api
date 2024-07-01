from fastapi import FastAPI
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Date, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import UniqueConstraint

# SQLAlchemy Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI Setup
app = FastAPI()

# Database Models
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class Team(Base):
    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class TeamMember(Base):
    __tablename__ = "team_members"

    team_id = Column(Integer, ForeignKey("teams.team_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)

class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String, nullable=True)
    status = Column(String(20), nullable=False)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(Integer, ForeignKey("users.user_id"))
    assigned_to = Column(Integer, ForeignKey("users.user_id"))
    team_id = Column(Integer, ForeignKey("teams.team_id"))

class Tag(Base):
    __tablename__ = "tags"

    tag_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    team_id = Column(Integer, ForeignKey("teams.team_id"))
    __table_args__ = (UniqueConstraint('name', 'user_id', 'team_id'),)

class TaskTag(Base):
    __tablename__ = "task_tags"

    task_id = Column(Integer, ForeignKey("tasks.task_id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.tag_id"), primary_key=True)

# Dependency Injection
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
