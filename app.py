import streamlit as st
import ollama
import base64
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(
    page_title="🤖 Faiz's Ollama Multimodal Chat",
    page_icon="🖼️",
    layout="wide"
)

# --- Helper Functions ---

@st.cache_data(ttl=3600)  # Cache the model list for 1 hour
def get_available_models():
    """Fetches the list of available models from Ollama."""
    try:
        models_data = ollama.list().get("models", [])
        # Your list shows 'llava:v1.6', 'moondream:latest', 'llama3:latest', etc.
        return [m.get("model") for m in models_data]
    except Exception as e:
        st.error(f"Error fetching Ollama models: {e}")
        # Provide a fallback list if Ollama isn't running
        return ["llava:v1.6", "moondream:latest", "llama3:latest"]

def image_to_base64(image_file):
    """Converts an uploaded image file to a base64 string."""
    # Read the file's bytes
    img_bytes = image_file.getvalue()
    # Encode the bytes to base64
    base64_str = base64.b64encode(img_bytes).decode('utf-8')
    return base64_str

# --- Session State Initialization ---
# This is the most important part of a Streamlit app.
# It's where we store variables that persist between user interactions.

if "messages" not in st.session_state:
    # This will store our chat history
    st.session_state.messages = []

if "selected_model" not in st.session_state:
    # This will store the currently selected model
    st.session_state.selected_model = ""

# --- Sidebar ---
# All our controls will go here
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # 1. Model Selection
    available_models = get_available_models()
    
    # Set a default model (try llava first, then moondream, then any)
    if not st.session_state.selected_model and available_models:
        if "llava:v1.6" in available_models:
            st.session_state.selected_model = "llava:v1.6"
        elif "moondream:latest" in available_models:
            st.session_state.selected_model = "moondream:latest"
        else:
            st.session_state.selected_model = available_models[0]

    # Dropdown to select the model
    st.session_state.selected_model = st.selectbox(
        "Select Model",
        available_models,
        index=available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0
    )

    st.markdown("---")

    # 2. Model Parameters
    st.markdown("### 🧠 Model Parameters")
    system_prompt = st.text_area(
        "System Prompt",
        "You are a helpful assistant. If you are given an image, describe it in detail.",
        height=100
    )
    temperature = st.slider("Temperature (Creativity)", 0.0, 1.5, 0.7, 0.1)

    st.markdown("---")

    # 3. Image Upload
    st.markdown("### 🖼️ Image Upload")
    # We use a file uploader that stays in the sidebar.
    # The 'staged_image' will be used when the user sends their *next* prompt.
    st.session_state.staged_image = st.file_uploader(
        "Upload an image (optional)",
        type=["png", "jpg", "jpeg"]
    )

    if st.session_state.staged_image:
        # Show a preview
        st.image(st.session_state.staged_image, caption="Image ready to send", width=200)

    st.markdown("---")

    # 4. Clear Chat
    if st.button("🧹 Clear Chat History"):
        st.session_state.messages = []
        st.session_state.staged_image = None
        st.rerun()  # Rerun the app to clear the chat display

# --- Main Chat Interface ---
st.title("🤖 Ollama Multimodal Chat")
st.caption(f"Currently using: `{st.session_state.selected_model}`")

# Display past chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # Check if the message has image data and display it
        if "image_data" in msg:
            st.image(msg["image_data"], width=300)
        # Display the text content
        st.write(msg["content"])

# Handle the user's new prompt
if prompt := st.chat_input("What would you like to ask?"):
    
    # --- User's Turn ---
    user_msg = {"role": "user", "content": prompt}
    image_to_send_to_ollama = []

    # Check if there is an image staged in the sidebar
    if st.session_state.staged_image:
        # 1. Convert image to base64 for the API
        base64_img = image_to_base64(st.session_state.staged_image)
        image_to_send_to_ollama.append(base64_img)
        
        # 2. Get image bytes for *display* in the chat
        image_bytes_for_display = st.session_state.staged_image.getvalue()
        user_msg["image_data"] = image_bytes_for_display  # For history
        
        # 3. Clear the staged image
        st.session_state.staged_image = None
        
    # Add user's message to chat history
    st.session_state.messages.append(user_msg)

    # Display user's message in the chat
    with st.chat_message("user"):
        if "image_data" in user_msg:
            st.image(user_msg["image_data"], width=300)
        st.write(prompt)

    # --- Assistant's Turn ---
    with st.chat_message("assistant"):
        try:
            # Reformat the entire history for the Ollama API
            # This is how we achieve "memory"
            api_messages = []
            if system_prompt:
                api_messages.append({"role": "system", "content": system_prompt})

            for msg in st.session_state.messages:
                api_msg = {"role": msg["role"], "content": msg["content"]}
                
                # Check if this historical message had an image
                if "image_data" in msg:
                    # Convert the *stored bytes* back to base64 for the API
                    img_file_like = BytesIO(msg["image_data"])
                    api_msg["images"] = [image_to_base64(img_file_like)]
                
                api_messages.append(api_msg)

            # The `st.write_stream` function is magic!
            # It will "type out" the response as it comes in.
            stream = ollama.chat(
                model=st.session_state.selected_model,
                messages=api_messages,
                stream=True,
                options={"temperature": temperature}
            )
            
            # This will collect the full response for saving to history
            full_response = st.write_stream(
                (chunk['message']['content'] for chunk in stream)
            )
            
            # Add the full response to our session state history
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )

        except Exception as e:
            error_message = f"❌ An error occurred with Ollama: {str(e)}"
            st.error(error_message)
            # Add the error to history so the user knows what happened
            st.session_state.messages.append(
                {"role": "assistant", "content": error_message}
            )
        
        # We need to rerun to clear the staged image from the sidebar UI
        # after the response is complete.
        st.rerun()
