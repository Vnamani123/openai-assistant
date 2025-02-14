# Importing required packages
import streamlit as st
import time
from openai import OpenAI

st.write("OpenAI module is successfully imported!")

# Set your OpenAI API key and assistant ID here
api_key = st.secrets["openai_apikey"]
assistant_id = st.secrets["assistant_id"]

# Set OpenAI client, assistant, and assistant thread
@st.cache_resource
def load_openai_client_and_assistant():
    client = OpenAI(api_key=api_key)
    my_assistant = client.beta.assistants.retrieve(assistant_id)
    thread = client.beta.threads.create()
    return client, my_assistant, thread

client, my_assistant, assistant_thread = load_openai_client_and_assistant()

# Function to wait for assistant response
def wait_on_run(run, thread):
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        time.sleep(0.5)
    return run

# Get response from assistant and store it in session state
def get_assistant_response(user_input=""):
    message = client.beta.threads.messages.create(
        thread_id=assistant_thread.id,
        role="user",
        content=user_input,
    )

    run = client.beta.threads.runs.create(
        thread_id=assistant_thread.id,
        assistant_id=assistant_id,
    )

    run = wait_on_run(run, assistant_thread)

    # Retrieve all messages
    messages = client.beta.threads.messages.list(thread_id=assistant_thread.id, order="asc")
    
    # Store messages in session state for chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Append new messages
    for msg in messages.data:
        role = "User" if msg.role == "user" else "Assistant"
        content = msg.content[0].text.value
        if {"role": role, "content": content} not in st.session_state.chat_history:
            st.session_state.chat_history.append({"role": role, "content": content})

    return messages.data[-1].content[0].text.value

# Initialize session state variables
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

def submit():
    st.session_state.user_input = st.session_state.query
    st.session_state.query = ""

# Streamlit UI
st.title("🍕 Papa Johns Pizza Assistant 🍕")

st.text_input("Play with me:", key="query", on_change=submit)

user_input = st.session_state.user_input

# Display chat history
for chat in st.session_state.chat_history:
    if chat["role"] == "User":
        st.markdown(f"**🧑 User:** {chat['content']}")
    else:
        st.markdown(f"**🤖 Assistant:** {chat['content']}")

# Process new input
if user_input:
    result = get_assistant_response(user_input)
    st.header("Assistant :blue[cool] :pizza:", divider="rainbow")
    st.text(result)


