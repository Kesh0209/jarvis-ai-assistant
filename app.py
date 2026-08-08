import os
import json
import urllib.request
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from tavily import TavilyClient

st.set_page_config(page_title="J.A.R.V.I.S.", page_icon="🎙️", layout="centered")

# Minimalist Dark UI
st.markdown("""
<style>
    .stApp {
        background-color: #0b0c10;
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .siri-orb {
        width: 80px; height: 80px; border-radius: 50%; margin: 20px auto;
        background: radial-gradient(circle, #64c8ff 0%, #b45aff 50%, #ff3296 100%);
        box-shadow: 0 0 30px rgba(180, 90, 255, 0.6);
        animation: orb-pulse 3s infinite alternate ease-in-out;
    }
    @keyframes orb-pulse {
        0% { transform: scale(0.9); }
        100% { transform: scale(1.1); }
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="siri-orb"></div>', unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center;'>J.A.R.V.I.S.</h2>", unsafe_allow_html=True)

# API Keys
groq_api_key = st.secrets.get("GROQ_API_KEY", "").strip()
tavily_api_key = st.secrets.get("TAVILY_API_KEY", "").strip()

if not groq_api_key:
    st.warning("⚠️ GROQ_API_KEY is missing in Streamlit Secrets.")
    st.stop()

groq_client = Groq(api_key=groq_api_key)

SYSTEM_PROMPT = """
You are J.A.R.V.I.S., a loyal, articulate, intelligent personal assistant inspired by Iron Man.
- Address the user as 'Boss' or 'Sir'.
- Keep answers direct, concise, and conversational.
"""

def perform_search(query):
    if not tavily_api_key:
        return ""
    try:
        tavily = TavilyClient(api_key=tavily_api_key)
        res = tavily.search(query=query, max_results=2)
        results = res.get("results", [])
        if not results: return ""
        return "\n".join([f"- {r['title']}: {r['content']}" for r in results])
    except Exception:
        return ""

if "messages" not in st.session_state:
    st.session_state.messages = []
if "processed_audio_id" not in st.session_state:
    st.session_state.processed_audio_id = None

# Sidebar Control
st.sidebar.title("⚙️ Controls")
voice_enabled = st.sidebar.toggle("🔊 Speak Out Loud", value=True)
if st.sidebar.button("🛑 STOP SPEAKING"):
    components.html("<script>window.speechSynthesis.cancel();</script>", height=0)

# Display Chat Messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_query = None

# Method 1: Microphone Recording
st.write("🎙️ **Tap to Speak:**")
audio_file = st.audio_input("Record Voice", label_visibility="collapsed")

if audio_file:
    audio_id = f"{audio_file.name}_{audio_file.size}"
    if st.session_state.processed_audio_id != audio_id:
        with st.spinner("Processing speech with High-Precision Whisper..."):
            try:
                # Switched to whisper-large-v3 for max precision across accents
                transcription = groq_client.audio.transcriptions.create(
                    file=("speech.wav", audio_file.read()),
                    model="whisper-large-v3",
                    language="en",
                    temperature=0.0,
                    response_format="text",
                )
                if transcription and transcription.strip():
                    user_query = transcription.strip()
                    st.info(f"🗣️ **Heard:** \"{user_query}\"")
                    st.session_state.processed_audio_id = audio_id
            except Exception as e:
                st.error(f"Audio Transcription Error: {str(e)}")

# Method 2: Text Input
text_input = st.chat_input("Type to JARVIS...")
if text_input:
    user_query = text_input

# --- PROCESS QUERY ---
if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})

    search_context = ""
    if any(kw in user_query.lower() for kw in ["news", "latest", "today", "weather", "who is", "what is", "price"]):
        with st.spinner("Fetching live web context..."):
            search_context = perform_search(user_query)

    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in st.session_state.messages[:-1]:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    
    final_prompt = user_query + (f"\n\n[LIVE SEARCH DATA]:\n{search_context}" if search_context else "")
    api_messages.append({"role": "user", "content": final_prompt})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": api_messages,
        "temperature": 0.5,
        "max_tokens": 1024
    }

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            reply = res_data["choices"][0]["message"]["content"]
            st.session_state.messages.append({"role": "assistant", "content": reply})

            # Play Voice response via JS
            if voice_enabled:
                clean_speech = reply.replace('"', '\\"').replace('\n', ' ').replace("'", "\\'")
                js_speech = f"""
                <script>
                    if ('speechSynthesis' in window) {{
                        window.speechSynthesis.cancel();
                        var msg = new SpeechSynthesisUtterance("{clean_speech}");
                        msg.rate = 1.0;
                        window.speechSynthesis.speak(msg);
                    }}
                </script>
                """
                components.html(js_speech, height=0)

    except Exception as e:
        st.error(f"Error processing request: {str(e)}")
