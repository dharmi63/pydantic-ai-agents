from db_models import Messages
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

def save_messages(db, session_id, user_id, role, content):

    msg = Messages(session_id=session_id, user_id=user_id, role=role, content=content)

    db.add(msg)
    db.commit()
    db.refresh(msg)

    print(f"session id:{msg.session_id} \nrole: {msg.role} \ncontent: {msg.content}")


def get_session_history(db, user_id):

    print("Get session history function callled...\n")

    msgs = db.query(Messages).filter(Messages.user_id==user_id).order_by(Messages.created_at).all()

    history = []

    for m in msgs:

        if m.role == "user":
            history.append(
                ModelRequest(
                    parts=[UserPromptPart(content=m.content)]
                )
            )

        elif m.role == "assistant":
            history.append(
                ModelResponse(
                    parts=[TextPart(content=m.content)]
                )
            )

    print(f"History: {history}\n")


    return history