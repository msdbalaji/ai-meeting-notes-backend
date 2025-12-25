# backend/app/utils.py
from .database import SessionLocal
from . import crud

def seed_test_user():
    db = SessionLocal()
    u = crud.get_user_by_email(db, "alice@example.com")
    if not u:
        crud.create_user(db, email="alice@example.com", full_name="Alice Example", hashed_password="test")
        print("Created test user alice@example.com")
    else:
        print("Test user exists")
    db.close()

if __name__ == "__main__":
    seed_test_user()
