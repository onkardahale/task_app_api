from fastapi import FastAPI
from datetime import datetime
from sqlalchemy import Table, create_engine, Column, Integer, String, ForeignKey, Date, DateTime
from sqlalchemy.orm import sessionmaker,  relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import UniqueConstraint
import hashlib

# SQLAlchemy Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI Setup
app = FastAPI()

from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    uid = Colmun(String(10), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class Team(Base):
    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TeamMember(Base):
    __tablename__ = "team_members"

    team_id = Column(Integer, ForeignKey("teams.team_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)

    team = relationship("Team", backref="team_members")
    user = relationship("User", backref="team_members")

class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String)  # Change to Text if needed
    status = Column(String(20), nullable=False)
    due_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.user_id"))
    team_id = Column(Integer, ForeignKey("teams.team_id"))

    creator = relationship("User", backref="created_tasks")
    team = relationship("Team", backref="tasks")

class TaskAssignee(Base):
    __tablename__ = "task_assignees"

    task_id = Column(Integer, ForeignKey("tasks.task_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)

    task = relationship("Task", backref="task_assignees")
    user = relationship("User", backref="assigned_tasks")

class Tag(Base):
    __tablename__ = "tags"

    tag_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    team_id = Column(Integer, ForeignKey("teams.team_id"))

    UniqueConstraint('name', 'user_id', 'team_id')

    creator = relationship("User", backref="tags")
    team = relationship("Team", backref="tags")

class TaskTag(Base):
    __tablename__ = "task_tags"

    task_id = Column(Integer, ForeignKey("tasks.task_id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.tag_id"), primary_key=True)

    task = relationship("Task", backref="task_tags")
    tag = relationship("Tag", backref="task_tags")
