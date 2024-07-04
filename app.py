from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from models import *
from database import get_db, init_db
from pydantic import BaseModel, EmailStr

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
    email: EmailStr
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
    uid: str
    team_id: Optional[int] = None
    tags: Optional[List[str]] = None
class PersonalTaskResponse(BaseModel):
    task_id: int
    title: str
    description: Optional[str]
    status: str
    due_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int]
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
    team: Optional[TeamResponse]
    assignees: List[UserResponse] = []
    tags: List[TagResponse] = []

    class Config:
        from_attributes = True

class AuthRequest(BaseModel):
    uid: str

class AddAssignedMembers(BaseModel):
    task_id: int
    assignees: List[int]

class TeamMemberResponse(BaseModel):
    user_id: int
    username: str
    email: EmailStr

    class Config:
        from_attributes = True
class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    tags: Optional[List[str]] = None
    assignee: Optional[List[int]] = None 

# Auth endpoint to check if user exists
@app.post("/auth", response_model=UserResponse, status_code=200)
def authenticate_user(auth_request: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.uid == auth_request.uid).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_orm(user)

# Get personal tasks by specific user
@app.get("/tasks/{uid}", response_model=List[PersonalTaskResponse], status_code=200)
def get_tasks_by_uid(uid: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.uid == uid).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    tasks = db.query(Task).filter(
        Task.created_by == user.user_id,
        or_(Task.team_id == None, Task.team_id == '')
    ).all()
    task_responses = []
    for task in tasks:
        task_response = PersonalTaskResponse.from_orm(task)
        tags = db.query(Tag).join(TaskTag).filter(TaskTag.task_id == task.task_id).all()
        task_response.tags = [TagResponse.from_orm(tag) for tag in tags]
        task_responses.append(task_response)
    return task_responses

# Create a new personal task
@app.post("/tasks", response_model= PersonalTaskResponse, status_code=200)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.uid == task.uid).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    new_task = Task(
        title=task.title,
        description=task.description,
        status=task.status,
        due_date=task.due_date,
        created_by=user.user_id,
        team_id=task.team_id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    if task.tags is not None:
        for tag_name in task.tags:
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                new_tag = Tag(name=tag_name, user_id=new_task.created_by)
                db.add(new_tag)
                db.flush()
            task_tag = TaskTag(task_id = new_task.task_id, tag_id=new_tag.tag_id)
            db.add(task_tag)

    db.commit()
    db.refresh(new_task)

    return PersonalTaskResponse.from_orm(new_task)

# Update personal task
@app.put("/tasks/{task_id}", response_model=PersonalTaskResponse, status_code=200)
def update_task(task: TaskUpdate, task_id: int, db: Session = Depends(get_db)):
    task_to_update = db.query(Task).filter(Task.task_id == task_id).first()
    if not task_to_update:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Update fields if provided
    if task.title is not None:
        task_to_update.title = task.title
    if task.description is not None:
        task_to_update.description = task.description
    if task.status is not None:
        task_to_update.status = task.status
    if task.due_date is not None:
        task_to_update.due_date = task.due_date

    # Update tags if provided
    if task.tags is not None:
        db.query(TaskTag).filter(TaskTag.task_id == task_id).delete()
        for tag_name in task.tags:
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                new_tag = Tag(name=tag_name, user_id=task_to_update.created_by)
                db.add(new_tag)
                db.flush()
                tag = new_tag
            task_tag = TaskTag(task_id=task_id, tag_id=tag.tag_id)
            db.add(task_tag)

    # Update assignees if provided
    if task.assignee is not None:
        db.query(TaskAssignee).filter(TaskAssignee.task_id == task_id).delete()
        for user_id in task.assignee:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                task_assignee = TaskAssignee(task_id=task_id, user_id=user_id)
                db.add(task_assignee)

    db.commit()
    db.refresh(task_to_update)

    return TeamTaskResponse.from_orm(task_to_update)

# Delete task endpoint
@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return None

# Create User
@app.post("/user", response_model=UserResponse, status_code = 200)
def create_user(user : UserCreate, db: Session = Depends(get_db)):
    check_user = db.query(User).filter(User.email == user.email).first() 

    if check_user is not None:
        raise HTTPException(status_code=409, detail="User already exists!")
    new_user = User(username=user.username, email=user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.from_orm(new_user)


# Get tasks from a specific team
@app.get("/team-tasks/{team_id}", response_model=list[TeamTaskResponse], status_code=200)
def get_team_tasks(team_id: int, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    tasks = db.query(Task).filter(Task.team_id == team_id).all()
    team_task_responses = []
    for task in tasks:
        team_task_response = TeamTaskResponse.from_orm(task)
        team_task_response.team = TeamResponse.from_orm(task.team) if task.team else None
        team_task_response.assignees = [UserResponse.from_orm(assignee) for assignee in task.assignees]
        team_task_response.tags = [TagResponse.from_orm(tag) for tag in task.tags]
        team_task_responses.append(team_task_response)
    return team_task_responses

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
    new_tag = Tag(name=tag.name, user_id=tag.user_id, team_id=tag.team_id)
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    return TagResponse.from_orm(new_tag)

# Get teams by user ID
@app.get("/teams/{uid}", response_model=list[TeamResponse], status_code=200)
def get_teams_by_uid(uid: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.uid == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    teams = user.teams
    team_responses = [TeamResponse.from_orm(team) for team in teams]
    return team_responses

# Add task assignees
@app.post("/tasks/assignees", status_code=201)
def add_task_assignees(assigned_members: AddAssignedMembers, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.task_id == assigned_members.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for user_id in assigned_members.assignees:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
        task_assignee = TaskAssignee(task_id=assigned_members.task_id, user_id=user_id)
        db.add(task_assignee)
    db.commit()
    return {"message": f"Assigned members added to Task {assigned_members.task_id}"}

# Remove task assignee
@app.delete("/tasks/{task_id}/assignees/{user_id}", status_code=200)
def remove_task_assignee(task_id: int, user_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    task_assignee = db.query(TaskAssignee).filter(TaskAssignee.task_id == task_id, TaskAssignee.user_id == user_id).first()
    if not task_assignee:
        raise HTTPException(status_code=404, detail="User is not assigned to this task")
    db.delete(task_assignee)
    db.commit()
    return {"message": f"User {user_id} removed from Task {task_id}"}


# Get members by team_id
@app.get("/teams/{team_id}/members", response_model=List[TeamMemberResponse], status_code=200)
def get_team_members(team_id: int, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    members = db.query(User).join(TeamMember).filter(TeamMember.team_id == team_id).all()
    if not members:
        raise HTTPException(status_code=404, detail="No members found for this team")

    member_responses = [TeamMemberResponse.from_orm(member) for member in members]
    return member_responses
