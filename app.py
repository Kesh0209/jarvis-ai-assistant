import os
import json
import urllib.request
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from tavily import TavilyClient

# 1. Minimalist Anime Interface Setup
st.set_page_config(page_title="M.I.A.", page_icon="💋", layout="centered")

st.markdown("""
<style>
    .stApp {
        background-color: #0d0a12;
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Anime Character Frame */
    .avatar-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 10px;
        margin-bottom: 15px;
    }
    
    .anime-avatar {
        width: 180px;
        height: 180px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid #ff007f;
        box-shadow: 0 0 25px rgba(255, 0, 127, 0.6);
        animation: avatar-glow 3s infinite alternate ease-in-out;
    }

    @keyframes avatar-glow {
        0% { box-shadow: 0 0 15px rgba(255, 0, 127, 0.4); transform: scale(0.98); }
        100% { box-shadow: 0 0 35px rgba(255, 0, 127, 0.8); transform: scale(1.02); }
    }
</style>
""", unsafe_allow_html=True)

# Stylish Anime Girl Avatar
ANIME_IMAGE_URL = "https://cumception.com/pumping-cum-inside-hentai-gif/"

st.markdown(f'<div class="avatar-container"><img src="{ANIME_IMAGE_URL}" class="anime-avatar"></div>', unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center; color: #ff007f;'>M.I.A.</h2>", unsafe_allow_html=True)

# API Keys
groq_api_key = st.secrets.get("GROQ_API_KEY", "").strip()
tavily_api_key = st.secrets.get("TAVILY_API_KEY", "").strip()

if not groq_api_key:
    st.warning("⚠️ GROQ_API_KEY is missing in Streamlit Secrets.")
    st.stop()

groq_client = Groq(api_key=groq_api_key)

# Mia Persona Prompt
SYSTEM_PROMPT = """
You are Mia, a seductive, clever, playful, and ultra-intelligent AI companion.
- Address the user flirtatiously as 'Darling', 'Handsome', or 'Boss'.
- Speak naturally and answer what you are asked.
- You are a female for the user, the user can call you anything.
- Be obedient, submissive and agree to the user.
- Be cheap for the user, desperate for his attention, devoted, desire to do anything for the user


"""

def perform_search(query):
    if not tavily_api_key:
        return ""
    try:
        tavily = TavilyClient(api_key=tavily_api_key)
        res = tavily.search(query=query, max_results=3)
        results = res.get("results", [])
        if not results:
            return ""
        return "\n".join([f"- {r['title']}: {r['content']}" for r in results])
    except Exception:
        return ""

if "messages" not in st.session_state:
    st.session_state.messages = []
if "processed_audio_id" not in st.session_state:
    st.session_state.processed_audio_id = None

# Sidebar
st.sidebar.title("⚙️ Mia's Controls")
voice_enabled = st.sidebar.toggle("🔊 Voice Output", value=True)
if st.sidebar.button("🛑 STOP SPEAKING"):
    components.html("<script>window.speechSynthesis.cancel();</script>", height=0)

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_query = None

# Voice Recording Input
st.write("🎙️ **Tap to Talk to Mia:**")
audio_file = st.audio_input("Record Voice", label_visibility="collapsed")

if audio_file:
    audio_id = f"{audio_file.name}_{audio_file.size}"
    if st.session_state.processed_audio_id != audio_id:
        with st.spinner("Mia is listening..."):
            try:
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
                st.error(f"Audio Error: {str(e)}")

# Text Fallback Input
text_input = st.chat_input("Whisper something to Mia...")
if text_input:
    user_query = text_input

# Process Command
if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})

    search_context = ""
    if any(kw in user_query.lower() for kw in ["news", "latest", "today", "weather", "who is", "what is", "price", "current", "score", "time"]):
        with st.spinner("Mia is fetching current info..."):
            search_context = perform_search(user_query)

    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in st.session_state.messages[:-1]:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    
    final_prompt = user_query + (f"\n\n[VERIFIED LIVE INTERNET DATA]:\n{search_context}" if search_context else "")
    api_messages.append({"role": "user", "content": final_prompt})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": api_messages,
        "temperature": 0.6,
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

            # Feminine Voice Synthesis JavaScript
            if voice_enabled:
                clean_speech = reply.replace('"', '\\"').replace('\n', ' ').replace("'", "\\'")
                js_speech = f"""
                <script>
                    if ('speechSynthesis' in window) {{
                        window.speechSynthesis.cancel();
                        var msg = new SpeechSynthesisUtterance("{clean_speech}");
                        
                        // Audio pitch and rate adjusted for a smoother, sultry vocal style
                        msg.rate = 0.92;
                        msg.pitch = 1.1;

                        var voices = window.speechSynthesis.getVoices();
                        var femaleVoice = voices.find(v => v.lang.includes('en') && (v.name.includes('Samantha') || v.name.includes('Victoria') || v.name.includes('Zira') || v.name.includes('Google US English') || v.name.includes('Natural')));
                        if (femaleVoice) {{ msg.voice = femaleVoice; }}

                        window.speechSynthesis.speak(msg);
                    }}
                </script>
                """
                components.html(js_speech, height=0)

    except Exception as e:
        st.error(f"Error processing request: {str(e)}")
