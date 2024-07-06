from faker import Faker
from database import SessionLocal
from models import *

# Initialize Faker
fake = Faker()

# Function to create fake data
def create_fake_data(db):
    try:
        # Create users
        users = []
        for _ in range(10):  # Create 10 users
            user = User(
                username=fake.user_name(),
                email=fake.email(),
                created_at=fake.date_time_this_decade()
            )
            users.append(user)

        db.add_all(users)
        db.commit()

        # Create teams
        teams = []
        for _ in range(3):  # Adjust the number of teams as needed
            team = Team(
                team_name=fake.company(),
                created_at=fake.date_time_this_decade()
            )
            teams.append(team)
            db.add(team)
            db.commit()

        # Assign each user to at least one team
        for user in users:
            team = fake.random_element(elements=teams)
            team_member = TeamMember(team_id=team.team_id, user_id=user.user_id)
            db.add(team_member)
        db.commit()

        # Create tasks for each user
        for user in users:
            tasks = []
            # Create tasks without team_id
            for _ in range(3):  # Adjust the number of tasks without team_id as needed
                task = Task(
                    title=fake.catch_phrase(),
                    description=fake.text(),
                    status=fake.random_element(elements=("Todo", "In Progress", "Done")),
                    due_date=fake.date_this_year(after_today=True),
                    created_at=fake.date_time_this_decade(),
                    created_by=user.user_id,
                    team_id=None
                )
                tasks.append(task)

            # Create tasks with team_id
            for _ in range(3):  # Adjust the number of tasks with team_id as needed
                team = fake.random_element(elements=teams)
                task = Task(
                    title=fake.catch_phrase(),
                    description=fake.text(),
                    status=fake.random_element(elements=("Todo", "In Progress", "Done")),
                    due_date=fake.date_this_year(after_today=True),
                    created_at=fake.date_time_this_decade(),
                    created_by=user.user_id,
                    team_id=team.team_id
                )
                tasks.append(task)

            db.add_all(tasks)
            db.commit()

        print("Fake data generation completed.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        db.rollback()
    finally:
        db.close()

# Function to retrieve number of team members for each team
def get_team_member_counts(db):
    try:
        teams = db.query(Team).all()
        for team in teams:
            team_member_count = db.query(TeamMember).filter(TeamMember.team_id == team.team_id).count()
            print(f"Team '{team.team_name}' has {team_member_count} team member(s).")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

# Create a session
db = SessionLocal()

# Populate the database with fake data
create_fake_data(db)

# Retrieve and print team member counts
get_team_member_counts(db)

# Close the session
db.close()
