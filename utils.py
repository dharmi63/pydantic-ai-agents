from db_models import Tasks, Notes
from db import SessionLocal, get_db
import re

db = SessionLocal()

def find_task(db, query, user_id):

    print(f"Query: {query}\n")

    tasks = db.query(Tasks).filter(Tasks.user_id == user_id).all()

    query_words = query.lower().split()

    best_match = None
    best_score = 0

    for t in tasks:
        score = 0
        for word in query_words:
            if word in t.task.lower():
                score += 1

        if score > best_score:
            best_score = score
            best_match = t

    if not best_match or best_score == 0:
        return None

    task = best_match

    print(f"Task: {task}\n")

    return task
