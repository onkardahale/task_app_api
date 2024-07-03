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
    tags: List[int] = []
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
class AuthRequest(BaseModel):
    uid: str
class AddAssignedMembers(BaseModel):
    task_id: int
    assignees: List[int]
    
# Auth endpoint to check if user exists
@app.post("/auth", response_model=UserResponse, status_code=200)
def authenticate_user(auth_request: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.uid == auth_request.uid).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_orm(user)

# Get personal Tasks by specific User 
@app.get("/tasks/{uid}", response_model=List[PersonalTaskResponse], status_code=200)
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

# Create a new personal task
@app.post("/tasks", response_model=PersonalTaskResponse, status_code=201)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == task.created_by).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    new_task = Task(
        title=task.title,
        description=task.description,
        status=task.status,
        due_date=task.due_date,
        created_by=task.created_by,
        team_id=task.team_id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    for tag_id in task.tags:
        tag = db.query(Tag).filter(Tag.tag_id == tag_id).first()
        if tag is None:
            raise HTTPException(status_code=404, detail=f"Tag with id {tag_id} not found")
        task_tag = TaskTag(task_id=new_task.task_id, tag_id=tag_id)
        db.add(task_tag)

    db.commit()
    db.refresh(new_task)

    return PersonalTaskResponse.from_orm(new_task)

# Create a team task
@app.post("/team-tasks", response_model=TeamTaskResponse, status_code=201)
def create_team_task(task: TaskCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == task.created_by).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    team = db.query(Team).filter(Team.team_id == task.team_id).first()
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    new_task = Task(
        title=task.title,
        description=task.description,
        status=task.status,
        due_date=task.due_date,
        created_by=task.created_by,
        team_id=task.team_id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    # Prepare response with team and tags information
    team_task_response = TeamTaskResponse.from_orm(new_task)
    team_task_response.team = TeamResponse.from_orm(team)

    for tag_id in task.tags:
        tag = db.query(Tag).filter(Tag.tag_id == tag_id).first()
        if tag is None:
            raise HTTPException(status_code=404, detail=f"Tag with id {tag_id} not found")
        task_tag = TaskTag(task_id=new_task.task_id, tag_id=tag_id)
        db.add(task_tag)

    db.commit()
    db.refresh(new_task)

    return team_task_response

# Get tasks from a specific team
@app.get("/team-tasks/{team_id}", response_model=list[TeamTaskResponse], status_code=200)
def get_team_tasks(team_id: int, db: Session = Depends(get_db)):
    # Query the team to ensure it exists
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Query tasks where team_id is not null and matches the provided team_id
    tasks = db.query(Task).filter(Task.team_id == team_id).all()

    # Serialize tasks into TeamTaskResponse
    team_task_responses = []
    for task in tasks:
        team_task_response = TeamTaskResponse.from_orm(task)
        # Optionally fetch associated team, assignees, and tags
        team_task_response.team = TeamResponse.from_orm(task.team) if task.team else None
        
        # Serialize assignees
        team_task_response.assignees = []
        for assignee in task.assignees:
            user = db.query(User).filter(User.user_id == assignee.user_id).first()
            if user:
                team_task_response.assignees.append(UserResponse(
                    user_id=user.user_id,
                    username=user.username,
                    email=user.email,
                    uid=user.uid,
                    created_at=user.created_at
                ))
        
        # Serialize tags
        team_task_response.tags = []
        for tag in task.tags:
            team_task_response.tags.append(TagResponse.from_orm(tag))
        
        team_task_responses.append(team_task_response)

    return team_task_responses

# Delete task endpoint
@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    return None

# Create a new tag
@app.post("/tags", response_model=TagResponse, status_code=201)
def create_tag(tag: TagCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == tag.user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if tag.team_id:
        team = db.query(Team).filter(Team.team_id == tag.team_id).first()
        if team is None:
            raise HTTPException(status_code=404, detail="Team not found")

    new_tag = Tag(
        name=tag.name,
        user_id=tag.user_id,
        team_id=tag.team_id
    )
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)

    return TagResponse.from_orm(new_tag)

# Delete tag endpoint
@app.delete("/tags/{tag_id}", status_code=204)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = db.query(Tag).filter(Tag.tag_id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    db.delete(tag)
    db.commit()
    return None

@app.get("/teams/{uid}", response_model=list[TeamResponse], status_code=200)
def get_teams_by_uid(uid: str, db: Session = Depends(get_db)):
    # Query the user based on uid
    user = db.query(User).filter(User.uid == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Retrieve teams that the user belongs to
    teams = user.teams

    # Serialize teams into TeamResponse
    team_responses = [TeamResponse.from_orm(team) for team in teams]

    return team_responses

@app.post("/tasks/assignees", status_code=201)
def add_task_assignees(
    assigned_members: AddAssignedMembers,
    db: Session = Depends(get_db)
):
    # Check if the task exists
    task = db.query(Task).filter(Task.task_id == assigned_members.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Assign new assignees to the task
    for user_id in assigned_members.assignees:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
        
        task_assignee = TaskAssignee(task_id=assigned_members.task_id, user_id=user_id)
        db.add(task_assignee)
    
    # Commit the transaction
    db.commit()
    
    return {"message": f"Assigned members added to Task {assigned_members.task_id}"}

@app.delete("/tasks/{task_id}/assignees/{user_id}", status_code=200)
def remove_task_assignee(
    task_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    # Check if the task exists
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if the user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if the user is assigned to the task
    task_assignee = db.query(TaskAssignee).filter(
        TaskAssignee.task_id == task_id,
        TaskAssignee.user_id == user_id
    ).first()
    if not task_assignee:
        raise HTTPException(status_code=404, detail="User is not assigned to this task")
    
    # Delete the task assignee relationship
    db.delete(task_assignee)
    db.commit()
    
    return {"message": f"User {user_id} removed from Task {task_id}"}
