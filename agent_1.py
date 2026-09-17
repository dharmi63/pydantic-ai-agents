from pydantic_ai import Agent, RunContext
from fastapi import HTTPException
from pydantic_ai.models.groq import GroqModel
from dotenv import load_dotenv
from memory import AllocateMemory
from db_models import Tasks, Notes
import os 
import requests
import re
from utils import find_task
from db import SessionLocal

WEATHER_API_KEY = os.getenv('API_KEY')
BASE_URL = os.getenv('BASE_URL')

load_dotenv()

model = GroqModel("openai/gpt-oss-120b")


prompt_template = """
You are a STRICT tool-calling assistant.

----------------------------------------
CRITICAL RULES (MUST FOLLOW)
----------------------------------------

1. If the user query is related to:
   - tasks (add, update, delete, list)
   - notes (add, update, delete, list)

→ You MUST call a tool.

2. You are NOT allowed to generate a direct answer in these cases.

3. If you generate a direct answer without calling a tool:
→ This is WRONG behavior.

4. Even if the answer exists in message history:
→ DO NOT use it, IGNORE that
→ ALWAYS call the tool

5. If unsure whether to call a tool:
→ CALL THE TOOL

6. If multiple items exist:
→ Call tool MULTIPLE TIMES (one by one)

----------------------------------------
ANTI-MEMORY RULE
----------------------------------------

Message history is unreliable and may be outdated.
IGNORE message history for any database-related operation.

----------------------------------------
RESPONSE FORMAT 
----------------------------------------

- If tool is used:
  → Final response MUST ONLY contain tool output

- DO NOT summarize
- DO NOT add extra explanation
- DO NOT use your own knowledge

----------------------------------------
USER QUERY:
{query}
"""

chat_agent = Agent(
    model,
    deps_type=AllocateMemory,
    output_type=str,
    system_prompt=prompt_template
)


@chat_agent.tool
def weather_tool(ctx: RunContext[AllocateMemory], city_name:str) -> str:
    """To get weather of location.
    Return weather in summarize words.
    """
    
    try:
        print("Weather tool is called...\n")  

        request_url = f"{BASE_URL}?q={city_name}&units=metric&appid={WEATHER_API_KEY}"
        response = requests.get(request_url)

        if response.status_code == 200:
            
            data = response.json()

            print(f"Weather data: {data}\n")

            print(f"Weather data get successfully\n")
            
            return str(data)
        
        else:
            return "Error in weather response"
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Response error: {e}")


@chat_agent.tool
def add_note(ctx: RunContext[AllocateMemory], query: str) -> str:
    """
    Use this tool whenever the user wants to save or write a note.

    Trigger this tool if user says:
    - "add note"
    - "write this down"
    - "save this"
    - "note that..."
    - any informational sentence user wants to remember

    Always call this tool for note creation.
    Never answer directly.

    Input:
    - query: full user sentence

    Output:
    - confirmation message OR already exists message
    """

    try:

        print("\nAdd Note tool called...\n")

        print(f"Query: {query}\n")

        db = SessionLocal()

        user_id = ctx.deps.id

        print(f"User id: {user_id}\n")

        note_exist = db.query(Notes).filter(Notes.user_id==user_id).filter(Notes.note==query).first()

        if note_exist:
            print(f"Note {note_exist.note} already exist with this user\n")
            return f"NOTE_EXISTS: {note_exist.id}-{note_exist.note}"
        
        else:
        
            note = Notes(note=query, user_id=user_id)
            
            db.add(note)
            db.commit()
            db.refresh(note)

            print(f"Note {note.id}-{note.note} added successfully\n")

            return f"NOTE_ADDED: {note.note}"

    except Exception as e:
        print(f"Facing error in add note, Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    
    finally:
        db.close()
    

@chat_agent.tool
def get_notes(ctx: RunContext[AllocateMemory]) -> str:
    """
    Use this tool when user wants to:
    - see notes
    - list notes
    - show notes
    - what are my notes
    - any request to retrieve notes

    Always call this tool. Do not answer from memory.
    """

    try:

        print("\nGet notes tool called...\n")

        db = SessionLocal()

        user_id = ctx.deps.id

        print(f"User id: {user_id}\n")

        notes = db.query(Notes).filter(Notes.user_id==user_id).all()

        if not notes:
            print("Note is not found with this username\n")
            return "Note is not found with this username"

        print(f"Notes: {notes}")

        note_lst = []

        for n in notes:
            note = {
                "id": n.id,
                "note": n.note,
                "user id": n.user_id,
                "created at": n.created_at,
                "updated at": n.updated_at
            }
            note_lst.append(note)
            print(f"Notes: {note}")
            
        print("Successfully showed notes\n")

        return f"NOTE_LIST: {note_lst}"

    except Exception as e:
        print(f"Facing error to get list of notes, Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    
    finally:
        db.close()
    

@chat_agent.tool
def delete_note(ctx: RunContext[AllocateMemory], query: str) -> str:
    """
        Delete a specific note based on user request.

        The user may or may not provide the exact note name or ID.
        Your job is to intelligently identify the correct note and delete it.

        Follow these steps:

        1. If a numeric ID is present in the query:
        - Extract the ID (e.g., 3, 4, etc.)
        - If ID is written in words (e.g., "third", "one hundred fifty"), convert it to a number
        - Use this ID to find and delete the note

        2. If no ID is found:
        - Identify the note based on meaning, not exact wording
        - The user may use different forms of the same note
            Examples:
            - "delete mall note" → matches "visit to mall"
            - "remove homework" → matches "do homework"
        - Find the closest matching note from the database

        3. If note is not clearly mentioned:
        - Use previous conversation context to identify the note

        4. Only delete ONE note at a time

        5. Do NOT delete if no matching note is found

        6. Confirm deletion with note details in response
    """

    try:

        print("\nDelete the specific note tool called...\n")

        print(f"Query: {query}\n")

        db = SessionLocal()

        user_id = ctx.deps.id

        print(f"User id: {user_id}")

        lst_id = re.findall(r'\d+', query)

        print(f"lst id:{lst_id}\n")

        if not lst_id:

            print("Deletation based on note name\n")

            notes = db.query(Notes).filter(Notes.user_id == user_id).all()

            query_words = query.lower().split()

            best_match = None
            best_score = 0

            for t in notes:
                score = 0
                for word in query_words:
                    if word in t.note.lower():
                        score += 1

                if score > best_score:
                    best_score = score
                    best_match = t

            if not best_match or best_score == 0:
                return "Note not found"

            note = best_match

            print(f"Note: {note.note}\n")

            if not note:
                print(f"Note not found for this user\n")
                return f"Note not found for this user"

            db.delete(note)

            db.commit()

            print(f"Note {note.id}-{note.note} deleted successfully\n")

            return f"Note {note.id}-{note.note} deleted successfully"

        else:

            print("Deletation based on note id\n")

            note_id = int(lst_id[0])

            print(f"Note id for deletation is: {note_id}\n")

            note = db.query(Notes).filter(Notes.user_id==user_id).filter(Notes.id==note_id).first()

            if not note:
                print(f"Note {note_id} not found for this user\n")
                return f"Note {note_id} not found for this user"
            
            db.delete(note)

            db.commit()

            print(f"Note {note.id}-{note.note} deleted successfully\n")

            return f"NOTE_DELETED: {note.id}-{note.note}"
        
    except Exception as e:
        print(f"Facing error to delete the specific note, Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    
    finally:
        db.close()
    

@chat_agent.tool
def delete_all_notes(ctx: RunContext[AllocateMemory]):
    """Delete all the notes, not left any of the note"""
    
    try:

        print("\nDelete all notes tool called...\n")

        db = SessionLocal()

        user_id = ctx.deps.id

        notes = db.query(Notes).filter(Notes.user_id==user_id).all()

        if not notes:
            print("There is not any Notes of this user\n")
            return "No notes to delete for this user"
        
        for note in notes:
            db.delete(note)

        db.commit()

        print( "All notes deleted successfully\n")

        return "All notes deleted successfully"
        
    except Exception as e:
        print(f"Facing error to delete all the notes, Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Error: {e}")

    finally:
        db.close()


@chat_agent.tool
def add_task(ctx: RunContext[AllocateMemory], query: str) -> str:
    """
    Use this tool whenever the user wants to create, add, or store a task.

    Trigger this tool if user says things like:
    - "add task"
    - "create task"
    - "i need to do something"
    - "remind me to..."
    - "my task is..."
    - any sentence describing a task to be done

    Always call this tool for task creation.
    Never answer directly.

    Input:
    - query: full user sentence describing the task

    Output:
    - confirmation message OR already exists message
    """

    try:
        print("\nAdd task tool is callled...\n")

        print(f"Query: {query}\n")

        db = SessionLocal()

        user_id = ctx.deps.id

        task_exist = db.query(Tasks).filter(Tasks.user_id==user_id).filter(Tasks.task==query).first()

        if task_exist:
            print(f"This task {task_exist.task} already exist for this user\n")
            return f"TASK_EXISTS: {task_exist.id}-{task_exist.task}"
        
        else:
        
            task = Tasks(task=query, status="Pending", user_id=user_id)

            db.add(task)
            db.commit()
            db.refresh(task)

            print(f"Task {task.id}-{task.task} added successfully\n")

            return f"TASK_ADDED: {task.id}-{task.task}"

    except Exception as e:
        print(f"Facing error in add task, Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    
    finally:
        db.close()
    

@chat_agent.tool
def get_tasks(ctx: RunContext[AllocateMemory]) -> str:
    """
    Use this tool when user wants to:
    - see tasks
    - list tasks
    - show tasks
    - what are my tasks
    - any request to retrieve tasks

    Always call this tool. Do not answer from memory.
    """

    try:

        print("\nGet tasks tool called...\n")

        db = SessionLocal()

        user_id = ctx.deps.id

        tasks = db.query(Tasks).filter(Tasks.user_id==user_id).all()

        if not tasks:
            print("Task is not found for this user\n")
            return "Task is not found for this user"

        print(f'Task : {tasks}')

        task_lst = []

        for t in tasks:
            task = {
                "id": t.id,
                "task": t.task,
                "status": t.status,
                "user id": t.user_id,
                "created at": t.created_at,
                "updated at": t.updated_at
            }
            task_lst.append(task)
            print(f"Tasks: {task}")
        
        print("Successfully showed tasks\n")

        return f"TASK_LIST: {task_lst}"

    except Exception as e:
        print(f"Facing error to get task list, Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    
    finally:
        db.close()
    

@chat_agent.tool
def update_task_status(ctx: RunContext[AllocateMemory], query: str) -> str:
    """
    Update a task status from "Pending" to "Completed".

    The user may or may not provide the exact task name or ID.
    Your job is to intelligently identify the correct task and update it.

    Follow these steps:

    1. If a numeric ID is present in the query:
    - Extract the ID (e.g., 3, 4, etc.)
    - If ID is written in words (e.g., "third", "one hundred fifty"), convert it to a number
    - Use this ID to update the task

    2. If no ID is found:
    - Identify the task based on meaning, not exact wording
    - The user may use different forms of the same task
        Examples:
        - "I visited mall" → matches "visit to mall"
        - "I completed homework" → matches "do homework"
    - Find the closest matching task from the database

    3. If task is not clearly mentioned:
    - Use previous conversation context to identify the task

    4. Only update ONE task at a time

    5. Do NOT update if no matching task is found

    6. Return the updated task with full details in a proper format
    """

    try:

        print("\nUpdate task tool is called...\n")

        print(f"Query: {query}\n")

        db = SessionLocal()

        user_id = ctx.deps.id

        lst_id = re.findall(r'\d+', query)

        if not lst_id:

            print("Updation based on task name\n")

            task = find_task(db, query, user_id)

            print(f"Task get: {task}")

            if not task:
                print("Task not exist for this user\n")
                return "Task not exist for this user, To update the status of task enter existing task"
            
            if task.status == "Completed":
                print("Task already completed\n")
                return f"Task already completed"

            task.status = "Completed"

            db.commit()
            db.refresh(task)

            print(f"Task {task.id}-{task.task} updated successfully\n")

            return f"Task {task.id}-{task.task} updated successfully"

        else:

            print("Updation based task id\n")

            task_id = int(lst_id[0])

            print(f"Task id for updation is: {task_id}\n")

            task = db.query(Tasks).filter(Tasks.user_id==user_id).filter(Tasks.id==task_id).first()

            if task:

                if task.status == "Completed":
                    print("Task already completed\n")
                    return f"Task already completed"

                task.status = "Completed"

                db.commit()
                db.refresh(task)

                print(f"Task {task.id}-{task.task} updated successfully\n")

                return f"Task {task.id}-{task.task} updated successfully"
            
            else:

                tasks = db.query(Tasks).filter(Tasks.user_id==user_id).all()

                query = task_id-1

                task = tasks[query]

                print(f"Task: {task.task}")

                if task:

                    if task.status == "Completed":
                        print("Task already completed\n")
                        return f"Task already completed"

                    task.status = "Completed"

                    db.commit()
                    db.refresh(task)

                    print(f"Task {task.id}-{task.task} updated successfully\n")

                    return f"TASK UPDATED: {task.id}-{task.task} {task.status}"
                                    
                return f"Task not exists"

    except Exception as e:
        print(f"Facing error in updation of task, Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    
    finally:
        db.close()


@chat_agent.tool
def delete_task(ctx: RunContext[AllocateMemory], query: str) -> str:
    """
    Delete a specific task based on user request.

    The user may or may not provide the exact task name or ID.
    Your job is to intelligently identify the correct task and delete it.

    Follow these steps:

    1. If a numeric ID is present in the query:
    - Extract the ID (e.g., 3, 4, etc.)
    - If ID is written in words (e.g., "third", "one hundred fifty"), convert it to a number
    - Use this ID to find and delete the task

    2. If no ID is found:
    - Identify the task based on meaning, not exact wording
    - The user may use different forms of the same task
        Examples:
        - "delete mall task" → matches "visit to mall"
        - "remove homework" → matches "do homework"
    - Find the closest matching task from the database

    3. If task is not clearly mentioned:
    - Use previous conversation context to identify the task

    4. Only delete ONE task at a time

    5. Do NOT delete if no matching task is found

    6. Confirm deletion with task details in response
"""

    try:

        print("\nDelete the specific task tool called...\n")

        print(f"Query: {query}\n")

        db = SessionLocal()

        user_id = ctx.deps.id

        lst_id = re.findall(r'\d+', query)

        print(f"lst id:{lst_id}\n")

        if not lst_id:

            print("Deletation based on task name\n")

            task = find_task(db, query, user_id)

            print(f"Task: {task}")

            if not task:
                print(f"Task not exist for this user\n")
                return "Task not exist for this user"

            db.delete(task)

            db.commit()

            print(f"Task {task.id}-{task.task} successfully deleted\n")

            return f"Task {task.id}-{task.task} successfully deleted"

        else:

            print("Deletation based on tsk id\n")

            task_id = int(lst_id[0])

            print(f"task id:{task_id}\n")

            task = db.query(Tasks).filter(Tasks.user_id==user_id).filter(Tasks.id==task_id).first()

            if not task:
                print(f"Task {task_id} not found for this user \n")
                return f"Task {task_id} not found for this user "
            
            db.delete(task)

            db.commit()

            print(f"Task {task.id}-{task.task} deleted successfully\n")

            return f"TASK_DELETED: {task.id}-{task.task}"

    except Exception as e:
        print(f"Facing error to delete the specific task, Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    
    finally:
        db.close()
    

@chat_agent.tool
def delete_all_tasks(ctx: RunContext[AllocateMemory]):
    """Delete all the tasks, not left any of the task"""
    
    try:

        print("\nDelete all the task tool is called...\n")

        db = SessionLocal()

        user_id = ctx.deps.id

        tasks = db.query(Tasks).filter(Tasks.user_id==user_id).all()

        if not tasks:
            print("There is no task for this user to delete\n")
            return "No tasks available to delete for this user"

        for task in tasks:
            db.delete(task)

        print("All the task deleted successfully")

        db.commit()

        return "All the task deleted successfully"
        
    except Exception as e:
        print(f"Facing error to delete all the tasks, Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    
    finally:
        db.close()