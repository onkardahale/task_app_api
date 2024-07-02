from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from models import *
from database import get_db, init_db
from pydantic import BaseModel, EmailStr
from datetime import datetime

app = FastAPI()

# Initialize the database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Pydantic models for request/response
class UserCreate(BaseModel):
    username: str
    email: EmailStr

class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    uid: str
    created_at: datetime

    class Config:
        from_attributes = True

class TeamCreate(BaseModel):
    team_name: str

class TeamResponse(BaseModel):
    team_id: int
    team_name: str
    created_at: datetime

    class Config:
        from_attributes = True

class TagCreate(BaseModel):
    name: str
    user_id: int
    team_id: Optional[int] = None

class TagResponse(BaseModel):
    tag_id: int
    name: str
    user_id: int
    team_id: Optional[int] = None

    class Config:
        from_attributes = True
        
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: str
    due_date: Optional[date] = None
    created_by: int
    team_id: Optional[int] = None

class PersonalTaskResponse(BaseModel):
    task_id: int
    title: str
    description: Optional[str]
    status: str
    due_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    #created_by: Optional[int]
    #team: Optional[TeamResponse]
    #assignees: List[UserResponse] = []
    tags: List[TagResponse] = []

    class Config:
        from_attributes = True

class TeamTaskResponse(BaseModel):
    task_id: int
    title: str
    description: Optional[str]
    status: str
    due_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int]
    team: TeamResponse
    assignees: List[UserResponse] = []
    tags: List[TagResponse] = []

    class Config:
        from_attributes = True

# Get personal Tasks by specific User 
@app.get("/tasks/{uid}", response_model=List[PersonalTaskResponse])
def get_tasks_by_uid(uid: str, db: Session = Depends(get_db)):
    # Lookup the user in the User table by uid
    user = db.query(User).filter(User.uid == uid).first()
    
    # If the user is not found, raise a 404 error
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Query the Task table for tasks created by this user and team is null
    tasks = db.query(Task).filter(
        Task.created_by == user.user_id,
        or_(Task.team_id == None, Task.team_id == '')
    ).all()

    task_responses = []

    # Iterate through tasks to create TaskResponse objects
    for task in tasks:
        
        # Create a TaskResponse object from the Task ORM model
        task_response = PersonalTaskResponse.from_orm(task)
        if task.team:
            task_response.team = TeamResponse.from_orm(task.team)

        # Query tags associated with the current task and serialize them
        tags = db.query(Tag).join(TaskTag).filter(TaskTag.task_id == task.task_id).all()
        task_response.tags = [TagResponse.from_orm(tag) for tag in tags]

        # Append the task_response to the list
        task_responses.append(task_response)
    
    # Return the list of tasks with all related data
    return task_responses
