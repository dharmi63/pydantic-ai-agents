from fastapi import FastAPI, Depends, HTTPException, status
import uvicorn
import logfire
from agent_1 import chat_agent
from memory import AllocateMemory
from sqlalchemy.orm import Session
from db_models import User, Base, Sessions
from session import save_messages, get_session_history
from db import engine
from models import ChatRequest
from db import get_db

logfire.configure()
logfire.instrument_pydantic_ai()

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.post("/create-user/", status_code=status.HTTP_201_CREATED)
def create_user(name:str, db: Session = Depends(get_db)):

    try:

        print("\nUser creation method called...\n")

        user_name = db.query(User).filter(User.name==name).first()

        if user_name:
            print(f"User name {user_name.name} already exists\n")
            raise HTTPException(status_code=409, detail=f"User name {user_name.name} already exists")

        user = User(name=name)

        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"User: {user.id} {user.name} created\n")

        return user

    except Exception as e:
        print(f"Facing error in user creation, Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
    

@app.get("/get-user/", status_code=status.HTTP_200_OK)
def get_user(user_id: int, db: Session = Depends(get_db)):

    try:

        print("\nGet user method called...\n")

        user = db.query(User).filter(User.id==user_id).first()

        if not user:
            print(f"User {user_id} is not exist\n")
            raise HTTPException(status_code=404, detail="User not found")
        
        print(f"User {user.name} showed")
        
        return user.id, user.created_at, user.updated_at, user.tasks, user.notes

    except Exception as e:
        print(f"Facing error in getting user, Error: {str(e)}\n")
        raise HTTPException(status_code=404, detail=f"Error: {e}")
    


@app.post("/llm_response/", status_code=status.HTTP_200_OK)
async def llm_response(req: ChatRequest, db: Session = Depends(get_db)):

    try:

        print("\nLLM Response method is callled...\n")

        query = req.query

        user_id = req.user_id

        session_id = req.session_id

        print(f"Query is given,\nQuery: {query}\n")

        print(f"User id: {user_id}\n")

        is_id = db.query(User).filter(User.id==user_id).first()

        if not is_id:
            print(f"User id {user_id} not exists\n")
            raise HTTPException(status_code=404, details=f"User id {user_id} not found")
        
        
        if not session_id:

            new_session = Sessions(user_id=user_id)

            db.add(new_session)
            db.commit()
            db.refresh(new_session)

            session_id = new_session.id

            print(f"New session id: {session_id}\n")

        else:

            session = db.query(Sessions).filter(Sessions.id==session_id).filter(Sessions.user_id==user_id).first()

            if not session:
                print(f"Session {session_id} not exist")

                create_session = Sessions(user_id=user_id)

                db.add(create_session)
                db.commit()
                db.refresh(create_session)

                session_id = create_session.id

                print(f"Created session id: {session_id}\n")
            
        
        history = get_session_history(db, user_id)[-6:]

        save_messages(db, session_id, user_id, "user", query)

        memory = AllocateMemory(id=user_id)

        print("Save messages function called... \nUser query saved in messages table\n")

        response = await chat_agent.run(query, deps=memory, message_history=history)

        print(f"Response: {response}")

        output = response.output

        save_messages(db, session_id, user_id, "assistant", output)

        print("\nSave messages function called... \nResponse saved successfully in messages table\n")

        print("Agent gave response\n")

        result = {
            "User ID": user_id,
            "Session ID": session_id,
            "Response": output
        }

        print(f"Result: {result}\n")

        return result

    except Exception as e:
        
        print(f"Facing error in chat_agent creation or tool calling, Error: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Error: {e}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=True)