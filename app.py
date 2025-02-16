import streamlit as st
import time
from openai import OpenAI
from PIL import Image
import pytesseract

# === Instruction Box ===
st.markdown(
    """
    📝 **How to Use the StudentSim -  A simulated student at office hours to practice and humanize TA responses.**
    - Start with a Hello.
    - When you are feel ready, type and submit "I am Done" or "I'm Done" for your evaluation.
    - Recieve a detailed evaluation of tone, rating, and social cues improvements.
    - Upload an image or text file if you want it analyzed.
    - Practice speaking to your student with just faster responses. 
    """,
    unsafe_allow_html=True,
)

st.title("💬 StudentSIM: Humanizing TAs 💬")


# === Chat Setup with OpenAI ===
api_key = st.secrets["openai_apikey"]
assistant_id = st.secrets["assistant_id"]

client = OpenAI(api_key=api_key)

@st.cache_resource
def load_openai_client_and_assistant():
    client = OpenAI(api_key=api_key)
    my_assistant = client.beta.assistants.retrieve(assistant_id)
    thread = client.beta.threads.create()
    return client, my_assistant, thread

client, my_assistant, assistant_thread = load_openai_client_and_assistant()

def wait_on_run(run, thread):
    while run.status in ["queued", "in_progress"]:
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    if run.status != "completed":
        st.error(f"Run failed with status: {run.status}")
    return run

def get_assistant_response(user_input=""):
    # Check for active runs and wait if needed
    active_run = client.beta.threads.runs.list(thread_id=assistant_thread.id)
    if active_run.data:
        latest_run = active_run.data[0]
        if latest_run.status in ["queued", "in_progress"]:
            wait_on_run(latest_run, assistant_thread)
    
    # Create a new message in the thread
    client.beta.threads.messages.create(
        thread_id=assistant_thread.id,
        role="user",
        content=user_input,
    )
    
    # Trigger assistant run
    run = client.beta.threads.runs.create(
        thread_id=assistant_thread.id,
        assistant_id=assistant_id,
    )
    run = wait_on_run(run, assistant_thread)
    
    # Retrieve messages and update chat history
    messages = client.beta.threads.messages.list(thread_id=assistant_thread.id, order="asc")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    for msg in messages.data:
        role = "User" if msg.role == "user" else "Assistant"
        content = msg.content[0].text.value
        if {"role": role, "content": content} not in st.session_state.chat_history:
            st.session_state.chat_history.append({"role": role, "content": content})
    
    return messages.data[-1].content[0].text.value

# Initialize session state variables for chat
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

def submit():
    st.session_state.user_input = st.session_state.query
    st.session_state.query = ""

# --- Chat Input Section ---
st.text_input("Type your message:", key="query", on_change=submit)

# --- File Upload Section (placed below chat input) ---
uploaded_file = st.file_uploader("Upload an image or text file:", type=["txt", "pdf", "png", "jpg", "jpeg"], key="file_uploader")

# Initialize extracted text variable
file_text = None

if uploaded_file is not None:
    if uploaded_file.type.startswith("image/"):
        # Process image using OCR (no enhancement)
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        file_text = pytesseract.image_to_string(image)
        st.subheader("Extracted Text from Image:")
        st.text(file_text)
    else:
        # Process text or PDF file
        if uploaded_file.type == "text/plain":
            file_text = uploaded_file.read().decode("utf-8")
        elif uploaded_file.type == "application/pdf":
            try:
                from PyPDF2 import PdfReader
                pdf_reader = PdfReader(uploaded_file)
                file_text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
            except ImportError:
                st.warning("Install PyPDF2: pip install PyPDF2")
        if file_text:
            st.subheader("Extracted Text from File:")
            st.text(file_text)

# --- Process Chat Message ---
user_input = st.session_state.user_input

# Process new input if provided
if user_input:
    result = get_assistant_response(user_input)
    st.header("CS Student", divider="rainbow")
    st.text(result)
    
# Append extracted file text to the chat input if available
if file_text:
    user_input = f"{user_input}\n\n[Extracted File Content]: {file_text}"

# Display chat history with new messages at the top
for chat in reversed(st.session_state.chat_history):
    if chat["role"] == "User":
        st.markdown(f"**🎓 TA:** {chat['content']}")
    else:
        st.markdown(f"**💻 CS Student :** {chat['content']}")

# === Small Credits at Bottom ===
st.markdown("\n---\n💖 *Made in colloboration with CETL and College of Computing* ")
