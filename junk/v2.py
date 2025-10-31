import streamlit as st
import ollama
import base64
from io import BytesIO
import time
import psutil
import pandas as pd

# --- Page Configuration ---
st.set_page_config(
    page_title="🤖 Mints Lab Multimodal Chat",
    page_icon="🖼️",
    layout="wide"
)

# --- CSS for Themes and Styling ---
st.markdown("""
<style>
    .stApp {
        background-color: #1a1a1a;
        color: #e5e7eb;
    }
    .stChatMessage {
        background-color: #2d2d2d;
    }
    .css-1aumxhk {
        color: #e5e7eb;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
    }
    .stTextInput > div > div > input {
        background-color: #4CAF50;
        color: white;
    }
    section[data-testid="stChatInput"] div div input {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    .light-theme {
        background-color: #f0f2f6 !important;
        color: #333 !important;
    }
    .light-chat {
        background-color: #e9ecef !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---

@st.cache_data(ttl=3600)
def get_available_models():
    try:
        models_data = ollama.list().get("models", [])
        return [m.get("model") for m in models_data]
    except Exception as e:
        st.error(f"Error fetching Ollama models: {e}")
        return ["Qwen2.5-coder:7b", "Codellama:7b", "mistral:7b", "phi3:mini", "llava:latest", "moondream:latest", "llama3:latest"]

def image_to_base64(image_file):
    img_bytes = image_file.getvalue()
    return base64.b64encode(img_bytes).decode('utf-8')

def get_resource_usage():
    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent
        }
    except Exception:
        return {"cpu_percent": 0, "memory_percent": 0}

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_model" not in st.session_state:
    st.session_state.selected_model = ""
if "resource_history" not in st.session_state:
    st.session_state.resource_history = []
if "staged_image" not in st.session_state:
    st.session_state.staged_image = None
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

# --- Sidebar ---
with st.sidebar:
    st.title("🌿 Mints Lab Configuration")
    st.markdown("### Designed and deployed by Faiz Ahmad, PhD candidate, UTD")
    
    # 1. Theme Selection with key
    st.session_state.theme = st.selectbox(
        "Theme",
        ["Dark", "Light"],
        index=0 if st.session_state.theme == "Dark" else 1,
        key="theme_selector"
    )
    
    # Apply Light Theme CSS if selected
    if st.session_state.theme == "Light":
        st.markdown("""
        <style>
            .stApp { background-color: #f0f2f6; color: #333; }
            .stChatMessage { background-color: #e9ecef; }
            .css-1aumxhk { color: #333; }
            .stButton > button { background-color: #4CAF50; color: white; }
            .stTextInput > div > div > input { background-color: #4CAF50; color: white; }
            section[data-testid="stChatInput"] div div input { background-color: #4CAF50 !important; color: white !important; }
        </style>
        """, unsafe_allow_html=True)
    
    # Model Selection with key
    available_models = get_available_models()
    if not st.session_state.selected_model and available_models:
        st.session_state.selected_model = available_models[0]

    st.session_state.selected_model = st.selectbox(
        "Select Model",
        available_models,
        index=available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0,
        key="model_selector"
    )
    st.caption(f"Currently using: `{st.session_state.selected_model}`")

    st.markdown("---")

    # 2. Model Parameters
    st.markdown("### 🧠 Model Settings")
    system_prompt = st.text_area(
        "System Prompt",
        "You are a helpful assistant. If you are given an image, describe it in detail.",
        height=100,
        help="Customize the assistant's behavior."
    )
    temperature = st.slider("Temperature (Creativity)", 0.0, 1.5, 0.7, 0.1, help="Controls response creativity.")

    st.markdown("---")

    # 3. Image Upload
    st.markdown("### 🖼️ Image Upload")
    st.session_state.staged_image = st.file_uploader(
        "Upload an image (optional)",
        type=["png", "jpg", "jpeg"],
        help="Drag and drop or browse to upload."
    )
    if st.session_state.staged_image:
        st.image(st.session_state.staged_image, caption="Image ready to send", width=200)

    st.markdown("---")

    # 4. System Insights
    st.markdown("### 📊 System Insights")
    resources = get_resource_usage()
    if resources["cpu_percent"] > 0 or resources["memory_percent"] > 0:
        st.session_state.resource_history.append(resources)
    if len(st.session_state.resource_history) > 10:
        st.session_state.resource_history.pop(0)

    with st.expander("View Resource Chart", expanded=True):
        if st.session_state.resource_history:
            df = pd.DataFrame(st.session_state.resource_history)
            st.bar_chart(df)
        else:
            st.write("No resource data available yet. Interact to see metrics.")

    st.markdown("---")

    # 5. Clear Chat
    if st.button("🧹 Clear Chat History", help="Reset the conversation and resources."):
        st.session_state.messages = []
        st.session_state.staged_image = None
        st.session_state.resource_history = []
        st.rerun()

# --- Main Chat Interface ---
st.title("🌱 Mints Lab Multimodal Chat")
st.caption(f"Powered by {st.session_state.selected_model} | Time: {time.strftime('%I:%M %p CDT, %B %d, %Y')}")

# Display past chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if "image_data" in msg:
            st.image(msg["image_data"], width=300)
        if "response_time" in msg:
            st.caption(f"Model: {msg.get('model', st.session_state.selected_model)}, Time: {msg['response_time']:.2f}s")
        st.markdown(f"<div style='background-color: #4CAF50; padding: 10px; border-radius: 5px; color: white;'>{msg['content']}</div>", unsafe_allow_html=True)

# Handle the user's new prompt
if prompt := st.chat_input("What would you like to ask?"):
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
        st.markdown(f"<div style='background-color: #4CAF50; padding: 10px; border-radius: 5px; color: white;'>{prompt}</div>", unsafe_allow_html=True)

    with st.chat_message("assistant"):
        start_time = time.time()
        try:
            api_messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
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
            
            full_response = ""
            for chunk in stream:
                full_response += chunk['message']['content']
                st.write(chunk['message']['content'], end='')
            st.write("")  # Newline after streaming
            
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
            error_message = f"❌ An error occurred with Ollama: {str(e)}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
        
        st.rerun()
