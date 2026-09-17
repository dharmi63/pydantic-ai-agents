import streamlit as st
import requests

BASE_URL = "http://localhost:8006"

st.set_page_config(page_title="AI Agent UI", layout="wide")

st.title("🤖 AI Agent Interface")

# Create Tabs
tab1, tab2, tab3 = st.tabs(["Create User", "Get User", "Chat"])

# -------------------------------
# 🟢 TAB 1: CREATE USER
# -------------------------------
with tab1:
    st.header("Create User")

    name = st.text_input("Enter User Name")

    if st.button("Create User"):
        if name:
            try:
                res = requests.post(f"{BASE_URL}/create-user/", params={"name": name})
                if res.status_code == 201:
                    st.success(f"User created: {res.json()}")
                else:
                    st.error(res.json())
            except Exception as e:
                st.error(str(e))
        else:
            st.warning("Enter name first")

# -------------------------------
# 🔵 TAB 2: GET USER
# -------------------------------
with tab2:
    st.header("Get User Details")

    user_id = st.number_input("Enter User ID", min_value=1, step=1)

    if st.button("Get User"):
        try:
            res = requests.get(f"{BASE_URL}/get-user/", params={"user_id": user_id})
            if res.status_code == 200:
                st.success("User Found")
                st.json(res.json())
            else:
                st.error(res.json())
        except Exception as e:
            st.error(str(e))

# -------------------------------
# 🟣 TAB 3: CHAT UI 
# -------------------------------
with tab3:
    st.header("Chat with Agent")

    # Sidebar Inputs
    st.sidebar.header("Session Settings")

    chat_user_id = st.sidebar.number_input("User ID", min_value=1, step=1)
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = ""

    chat_session_id = st.sidebar.text_input(
        "Session ID",
        value=st.session_state.session_id
    )

    
    
    st.markdown("""
<style>

/* Chat input container - improved */
.stChatInput {
    position: fixed;
    bottom: 15px;
    left: 50%;
    transform: translateX(-50%);
    width: 55%;
    max-width: 720px;
    background: #f9f9f9;  
    padding: 8px 12px;
    border-radius: 25px;
    border: 1px solid #cfcfcf;  
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    z-index: 100;
}

/* Input box */
.stChatInput textarea {
    min-height: 36px !important;
    max-height: 90px !important;
    font-size: 14px !important;
    padding: 8px 12px !important;
    border-radius: 18px !important;
    border: none !important;
}

/* Remove extra padding */
.stChatInput > div {
    padding: 0 !important;
}

/* Chat spacing */
.chat-container {
    padding-bottom: 120px;
    max-width: 800px;
    margin: auto;
}

</style>
""", unsafe_allow_html=True)
    

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Chat container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    st.markdown('</div>', unsafe_allow_html=True)

    # 🔥 Sticky input
    prompt = st.chat_input("Type your message...")

    if prompt:
        # ✅ Show user message immediately
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 🔥 Display instantly (before API call)
        with st.chat_message("user"):
            st.markdown(prompt)

        payload = {
            "user_id": chat_user_id,
            "query": prompt,
            "session_id": int(chat_session_id) if chat_session_id else None
        }

        try:
            with st.spinner("Thinking..."):
                res = requests.post(f"{BASE_URL}/llm_response/", json=payload)

            if res.status_code == 200:
                data = res.json()
                response_text = data.get("Response", "")

                # Add assistant message
                st.session_state.messages.append(
                    {"role": "assistant", "content": response_text}
                )

                st.session_state.session_id = str(data.get("Session ID"))
                st.sidebar.success(f"Session ID: {st.session_state.session_id}")

                st.rerun()

            else:
                st.error(res.json())

        except Exception as e:
            st.error(str(e))