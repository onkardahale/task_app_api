from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from faker import Faker
from datetime import datetime, date
from database import Base, SessionLocal, engine
from models import User, Team, Task, Tag, TeamMember, TaskAssignee, TaskTag

# Initialize Faker
fake = Faker()

# Function to create fake data
def create_fake_data(db):
    # Create users
    for _ in range(5):
        user = User(
            username=fake.user_name(),
            email=fake.email(),
            created_at=fake.date_time_this_decade()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create teams
        for _ in range(2):
            team = Team(
                team_name=fake.company(),
                created_at=fake.date_time_this_decade()
            )
            db.add(team)
            db.commit()
            db.refresh(team)

            # Create team members
            team_member = TeamMember(team_id=team.team_id, user_id=user.user_id)
            db.add(team_member)
            db.commit()

            # Create tasks for the team and without team
            for _ in range(3):
                task = Task(
                    title=fake.catch_phrase(),
                    description=fake.text(),
                    status=fake.random_element(elements=("Todo", "In Progress", "Done")),
                    due_date=fake.date_this_year(after_today=True),
                    created_at=fake.date_time_this_decade(),
                    created_by=user.user_id,
                    team_id=team.team_id  # Assign to a team
                )
                db.add(task)
                db.commit()
                db.refresh(task)

                # Assign task to user (as assignee)
                task_assignee = TaskAssignee(task_id=task.task_id, user_id=user.user_id)
                db.add(task_assignee)
                db.commit()

                # Create tags for tasks within the team
                for _ in range(2):
                    tag = Tag(
                        name=fake.word(),
                        user_id=user.user_id,
                        team_id=team.team_id
                    )
                    db.add(tag)
                    db.commit()
                    db.refresh(tag)

                    # Associate tags with tasks
                    task_tag = TaskTag(task_id=task.task_id, tag_id=tag.tag_id)
                    db.add(task_tag)
                    db.commit()

            # Create tasks without a team
            for _ in range(3):
                task = Task(
                    title=fake.catch_phrase(),
                    description=fake.text(),
                    status=fake.random_element(elements=("Todo", "In Progress", "Done")),
                    due_date=fake.date_this_year(after_today=True),
                    created_at=fake.date_time_this_decade(),
                    created_by=user.user_id,
                    team_id=None  # No team assigned
                )
                db.add(task)
                db.commit()
                db.refresh(task)

                # Assign task to user (as assignee)
                task_assignee = TaskAssignee(task_id=task.task_id, user_id=user.user_id)
                db.add(task_assignee)
                db.commit()

                # Create tags for tasks without a team
                for _ in range(2):
                    tag = Tag(
                        name=fake.word(),
                        user_id=user.user_id,
                        team_id=None  # No team assigned
                    )
                    db.add(tag)
                    db.commit()
                    db.refresh(tag)

                    # Associate tags with tasks
                    task_tag = TaskTag(task_id=task.task_id, tag_id=tag.tag_id)
                    db.add(task_tag)
                    db.commit()

    print("Fake data generation completed.")

# Create a session
db = SessionLocal()

# Populate the database with fake data
create_fake_data(db)

# Close the session
db.close()
