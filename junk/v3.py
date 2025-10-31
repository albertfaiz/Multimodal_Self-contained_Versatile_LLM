import streamlit as st
import ollama
import base64
from io import BytesIO
import time
import psutil
import json
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="🤖 Mints Lab Multimodal Chat",
    page_icon="🖼️",
    layout="wide"
)

# --- Helper Functions ---

@st.cache_data(ttl=3600)
def get_available_models():
    try:
        models_data = ollama.list().get("models", [])
        return [m.get("model") for m in models_data]
    except Exception:
        return ["Qwen2.5-coder:7b", "Codellama:7b", "mistral:7b", "phi3:mini", "llava:latest", "moondream:latest", "llama3:latest"]

def image_to_base64(image_file):
    try:
        img_bytes = image_file.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception:
        return None

def get_resource_usage():
    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "memory_percent": psutil.virtual_memory().percent
        }
    except Exception:
        return {"cpu_percent": 0, "memory_percent": 0}

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_model" not in st.session_state:
    st.session_state.selected_model = get_available_models()[0] if get_available_models() else "llama3:latest"
if "staged_image" not in st.session_state:
    st.session_state.staged_image = None
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

# --- Simple CSS for Themes ---
st.markdown("""
<style>
    .stApp [data-testid="stAppViewContainer"] { background-color: #000; color: #fff; }
    .stApp [data-testid="stSidebar"] { background-color: #111; }
    .stApp [data-testid="stDecoration"] { background-color: #111; }
    .st-emotion-cache-1aumxhk { color: inherit; }
    .stButton > button { background-color: #10B981; color: white; border-radius: 0.5rem; }
    .stTextInput > div > div > input { background-color: #333; color: #fff; }
</style>
""", unsafe_allow_html=True)

if st.session_state.theme == "Light":
    st.markdown("""
    <style>
        .stApp [data-testid="stAppViewContainer"] { background-color: #f0f2f6; color: #333; }
        .stApp [data-testid="stSidebar"] { background-color: #f8f9fa; }
        .stApp [data-testid="stDecoration"] { background-color: #f8f9fa; }
        .st-emotion-cache-1aumxhk { color: #333; }
        .stTextInput > div > div > input { background-color: #fff; color: #333; border: 1px solid #ccc; }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.title("🌿 Mints Lab Configuration")
    st.markdown("### Designed and deployed by Faiz Ahmad, PhD candidate, UTD")
    
    # Theme Selection
    st.session_state.theme = st.selectbox(
        "Theme",
        ["Dark", "Light"],
        index=0 if st.session_state.theme == "Dark" else 1
    )
    
    # Model Selection
    available_models = get_available_models()
    st.session_state.selected_model = st.selectbox(
        "Select Model",
        available_models,
        index=available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0
    )
    st.caption(f"Currently using: `{st.session_state.selected_model}`")

    st.markdown("---")

    # Model Parameters
    st.markdown("### 🧠 Model Settings")
    system_prompt = st.text_area(
        "System Prompt",
        "You are a helpful assistant. If you are given an image, describe it in detail.",
        height=100
    )
    temperature = st.slider("Temperature (Creativity)", 0.0, 1.5, 0.7, 0.1)

    st.markdown("---")

    # Image Upload
    st.markdown("### 🖼️ Image Upload")
    st.session_state.staged_image = st.file_uploader(
        "Upload an image (optional)",
        type=["png", "jpg", "jpeg"],
        help="Drag and drop or browse to upload."
    )
    if st.session_state.staged_image:
        st.image(st.session_state.staged_image, caption="Image ready to send", width=200)

    st.markdown("---")

    # System Metrics
    st.markdown("### 📊 System Metrics")
    resources = get_resource_usage()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("CPU Usage", f"{resources['cpu_percent']:.1f}%")
    with col2:
        st.metric("Memory Usage", f"{resources['memory_percent']:.1f}%")

    st.markdown("---")

    # Utilities
    st.markdown("### 🔧 Utilities")
    if st.button("📤 Export Chat"):
        try:
            chat_export = [{"role": msg["role"], "content": msg["content"]} for msg in st.session_state.messages]
            st.download_button(
                label="Download Chat History",
                data=json.dumps(chat_export, indent=2),
                file_name=f"mintslab_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        except Exception as e:
            st.error(f"Export failed: {str(e)}")

    if st.button("🧹 Clear Chat History"):
        st.session_state.messages = []
        st.session_state.staged_image = None
        st.rerun()

# --- Main Chat Interface ---
st.title("🌱 Mints Lab Multimodal Chat")
st.caption(f"Powered by {st.session_state.selected_model} | Time: {time.strftime('%I:%M %p CDT, %B %d, %Y')}")

# Display past chat messages
for msg in st.session_state.messages:
    try:
        with st.chat_message(msg["role"]):
            if "image_data" in msg:
                st.image(msg["image_data"], width=300)
            if "response_time" in msg:
                st.caption(f"Model: {msg.get('model', st.session_state.selected_model)}, Time: {msg['response_time']:.2f}s")
            st.write(msg["content"])
    except Exception:
        st.write(f"Error displaying message: {msg['content'][:50]}...")

# Handle the user's new prompt
if prompt := st.chat_input("What would you like to ask?"):
    try:
        user_msg = {"role": "user", "content": prompt}

        if st.session_state.staged_image:
            base64_img = image_to_base64(st.session_state.staged_image)
            image_bytes_for_display = st.session_state.staged_image.getvalue()
            user_msg["image_data"] = image_bytes_for_display
            st.session_state.staged_image = None

        st.session_state.messages.append(user_msg)

        with st.chat_message("user"):
            if "image_data" in user_msg:
                st.image(user_msg["image_data"], width=300)
            st.write(prompt)

        with st.chat_message("assistant"):
            start_time = time.time()
            api_messages = []
            if system_prompt:
                api_messages.append({"role": "system", "content": system_prompt})
            for msg in st.session_state.messages:
                api_msg = {"role": msg["role"], "content": msg["content"]}
                if "image_data" in msg:
                    img_file_like = BytesIO(msg["image_data"])
                    api_msg["images"] = [image_to_base64(img_file_like)]
                api_messages.append(api_msg)

            stream = ollama.chat(
                model=st.session_state.selected_model,
                messages=api_messages,
                stream=True,
                options={"temperature": temperature}
            )
            
            full_response = st.write_stream(chunk['message']['content'] for chunk in stream)
            response_time = time.time() - start_time

            assistant_msg = {
                "role": "assistant",
                "content": full_response,
                "model": st.session_state.selected_model,
                "response_time": response_time
            }
            st.session_state.messages.append(assistant_msg)
            st.caption(f"Model: {st.session_state.selected_model}, Time: {response_time:.2f}s")

    except Exception as e:
        error_message = f"❌ An error occurred: {str(e)}"
        st.error(error_message)
        st.session_state.messages.append({"role": "assistant", "content": error_message})
    
    st.rerun()
