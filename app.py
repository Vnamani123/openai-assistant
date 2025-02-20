import streamlit as st
import time
from openai import OpenAI
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from PyPDF2 import PdfReader

# === Clear chat history on every refresh ===
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# === Instruction Box ===
st.markdown("""
📝 **How to Use the StudentSim - A simulated student at office hours to practice and humanize TA responses.**

- Engage in conversation with the student, assuming your role as the TA for the given scenario.
- Begin with a friendly greeting, like "Hello."
- When you feel ready, type and submit “I am Done” or “I’m Done” to receive your evaluation.
- Ready for another scenario, message "Another Scenario". 
- Expect a detailed evaluation, including feedback on tone, rating, and suggestions for improving social cues.
- If you want to add an image or text file, feel free to upload it for analysis.
""", unsafe_allow_html=True)

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
    # Check for any active run in the thread
    active_run = client.beta.threads.runs.list(thread_id=assistant_thread.id)
    
    if active_run.data:
        latest_run = active_run.data[0]
        if latest_run.status in ["queued", "in_progress"]:
            # Wait for the previous run to complete before proceeding
            wait_on_run(latest_run, assistant_thread)  # Call wait_on_run to ensure the run is completed

    # Create a new message after the previous run is complete
    client.beta.threads.messages.create(thread_id=assistant_thread.id, role="user", content=user_input)

    # Trigger assistant run
    run = client.beta.threads.runs.create(thread_id=assistant_thread.id, assistant_id=assistant_id)
    run = wait_on_run(run, assistant_thread)  # Wait for the new run to finish

    # Retrieve messages after the new run has completed
    messages = client.beta.threads.messages.list(thread_id=assistant_thread.id, order="asc")
    return messages.data[-1].content[0].text.value

    # Create a new message in the thread after the previous run is complete
    client.beta.threads.messages.create(thread_id=assistant_thread.id, role="user", content=user_input)

    # Trigger assistant run
    run = client.beta.threads.runs.create(thread_id=assistant_thread.id, assistant_id=assistant_id)
    run = wait_on_run(run, assistant_thread)  # Wait for the new run to complete

    # Retrieve messages
    messages = client.beta.threads.messages.list(thread_id=assistant_thread.id, order="asc")
    return messages.data[-1].content[0].text.value

    # Create a new message in the thread
    client.beta.threads.messages.create(thread_id=assistant_thread.id, role="user", content=user_input)

    # Trigger assistant run
    run = client.beta.threads.runs.create(thread_id=assistant_thread.id, assistant_id=assistant_id)
    run = wait_on_run(run, assistant_thread)

    # Retrieve messages
    messages = client.beta.threads.messages.list(thread_id=assistant_thread.id, order="asc")
    return messages.data[-1].content[0].text.value

# Initialize session state variables for chat
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# === Handle file upload and trigger AI processing ===
file_text = None
uploaded_file = st.file_uploader("Upload an image or text file:", type=["txt", "pdf", "png", "jpg", "jpeg"], key="file_uploader", label_visibility="collapsed")

# Flag to check if the image has been processed
if 'image_processed' not in st.session_state:
    st.session_state.image_processed = False

if uploaded_file is not None and not st.session_state.image_processed:
    if uploaded_file.type.startswith("image/"):
        # Process image using OCR (Preprocessing added)
        image = Image.open(uploaded_file)
        
        # Preprocessing the image for better OCR accuracy
        image = image.convert("L")  # Convert to grayscale
        image = image.filter(ImageFilter.MedianFilter())  # Apply a median filter
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2)  # Increase contrast
        
        # Display image
        image_placeholder = st.empty()  # Placeholder to remove the image later
        image_placeholder.image(image, caption="Uploaded Image", use_container_width=True)

        # Extract text using pytesseract
        file_text = pytesseract.image_to_string(image)

        # Debug the OCR output
        if file_text.strip():
            st.write(f"Extracted Text from Image: {file_text}")  # Debugging step
            st.session_state.user_input = file_text  # Store text from image in session state to process it
            # Clear the image
            image_placeholder.empty()

            # Set the flag to indicate that the image has been processed
            st.session_state.image_processed = True

            # Clear the uploaded file from the uploader (prevents re-uploading)
            uploaded_file = None
    else:
        # Process text or PDF file
        if uploaded_file.type == "text/plain":
            file_text = uploaded_file.read().decode("utf-8")
        elif uploaded_file.type == "application/pdf":
            try:
                pdf_reader = PdfReader(uploaded_file)
                file_text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
                # Debugging step for PDF text extraction
                if file_text.strip():
                    st.write(f"Extracted Text from PDF: {file_text}")
            except Exception as e:
                st.warning(f"Error reading PDF: {e}")

# --- Process Chat Message ---
user_input = st.session_state.user_input
if user_input:
    result = get_assistant_response(user_input)

    # Store messages in session state for displaying
    st.session_state.chat_history.append({"role": "User", "content": user_input})
    st.session_state.chat_history.append({"role": "Assistant", "content": result})

# Create a container for chat messages
chat_container = st.container()

# Display chat messages dynamically
with chat_container:
    for chat in st.session_state.chat_history:
        if chat["role"] == "User":
            st.markdown(f"**🎓 TA:** {chat['content']}")
        else:
            st.markdown(f"**💻 CS Student:** {chat['content']}")

# Add an empty space for scrolling
scroll_placeholder = st.empty()

# === User Input at the Bottom ===
user_message = st.chat_input("Message to the Student:")

if user_message:
    # Append user message
    st.session_state.chat_history.append({"role": "User", "content": user_message})

    # Get AI response
    result = get_assistant_response(user_message)

    # Append AI response
    st.session_state.chat_history.append({"role": "Assistant", "content": result})

    # Force UI update to move chat down
    scroll_placeholder.empty()

    # Rerun app to display latest messages
    st.rerun()
