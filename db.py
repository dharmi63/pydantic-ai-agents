from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE = "postgresql://postgres:0202@localhost:5432/ai_agents"

engine = create_engine(DATABASE, echo=False)

SessionLocal = sessionmaker(bind=engine, autoflush=True, autocommit=False)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()