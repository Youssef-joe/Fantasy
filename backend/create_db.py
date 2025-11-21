from .database import engine, Base
from .models import Team, Player, Fixture, PlayerStats

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
