import os
import json
import urllib.request
import streamlit as st
import streamlit.components.v1 as components
from tavily import TavilyClient

# 1. Page Config (Clean Minimalist Siri Style)
st.set_page_config(page_title="JARVIS Personal Voice Assistant", page_icon="🎙️", layout="centered")

# Custom Apple/Siri Style Styling
st.markdown("""
<style>
    /* Dark Minimalist Background */
    .stApp {
        background-color: #0d0e12;
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
    }
    
    .assistant-header {
        text-align: center;
        margin-top: 20px;
        margin-bottom: 10px;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    
    /* Glowing Siri Sphere Container */
    .siri-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 30px 0;
    }
    
    .siri-orb {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(100,200,255,0.9) 0%, rgba(180,90,255,0.8) 50%, rgba(255,50,150,0.6) 100%);
        box-shadow: 0 0 30px rgba(140, 100, 255, 0.6), inset 0 0 15px rgba(255, 255, 255, 0.8);
        animation: orb-pulse 3s infinite alternate ease-in-out;
    }

    @keyframes orb-pulse {
        0% { transform: scale(0.92); box-shadow: 0 0 20px rgba(100, 200, 255, 0.5); }
        100% { transform: scale(1.08); box-shadow: 0 0 45px rgba(255, 50, 150, 0.8); }
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="assistant-header">J.A.R.V.I.S.</h1>', unsafe_allow_html=True)
st.markdown('<div class="siri-container"><div class="siri-orb"></div></div>', unsafe_allow_html=True)

# API Keys
groq_api_key = st.secrets.get("GROQ_API_KEY", "").strip()
tavily_api_key = st.secrets.get("TAVILY_API_KEY", "").strip()

if not groq_api_key:
    st.warning("⚠️ GROQ_API_KEY is missing in Streamlit Secrets.")
    st.stop()

SYSTEM_PROMPT = """
You are J.A.R.V.I.S., a loyal, highly intelligent, articulate, and natural personal assistant inspired by Iron Man.
- Address the user as 'Boss' or 'Sir'.
- Speak naturally, directly, and concisely (as if speaking in a real conversation).
- Balance factual accuracy with your intelligent reasoning. When given live web context, use it naturally without denying previous valid facts.
"""

def perform_search(query):
    if not tavily_api_key:
        return ""
    try:
        tavily = TavilyClient(api_key=tavily_api_key)
        response = tavily.search(query=query, search_depth="basic", max_results=3)
        results = response.get("results", [])
        if not results:
            return ""
        context = "\n[LIVE VERIFIED WEB DATA]:\n"
        for res in results:
            context += f"- {res['title']}: {res['content']}\n"
        return context
    except Exception:
        return ""

# Session Chat State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "latest_reply" not in st.session_state:
    st.session_state.latest_reply = ""

# Sidebar Options
st.sidebar.title("⚙️ Voice Settings")
voice_enabled = st.sidebar.toggle("🔊 Speak Response Aloud", value=True)
enable_web_search = st.sidebar.toggle("🌐 Automatic Web Search", value=True)

if st.sidebar.button("🛑 STOP SPEAKING (Shut Up)"):
    components.html("<script>window.speechSynthesis.cancel();</script>", height=0)

# Display Chat Messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# JavaScript Web Speech Synthesis Trigger
if voice_enabled and st.session_state.latest_reply:
    clean_speech = st.session_state.latest_reply.replace('"', '\\"').replace('\n', ' ').replace("'", "\\'")
    js_speech = f"""
    <script>
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel(); // Stop any existing audio
            var msg = new SpeechSynthesisUtterance("{clean_speech}");
            msg.rate = 1.0;
            msg.pitch = 1.0;
            
            // Try selecting a natural sounding English voice
            var voices = window.speechSynthesis.getVoices();
            var naturalVoice = voices.find(v => v.lang.includes('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Daniel')));
            if (naturalVoice) {{ msg.voice = naturalVoice; }}
            
            window.speechSynthesis.speak(msg);
        }}
    </script>
    """
    components.html(js_speech, height=0)
    st.session_state.latest_reply = "" # Reset after triggering

# Input Box
if prompt := st.chat_input("Talk or type to JARVIS..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Intelligent Search Trigger
    search_context = ""
    search_keywords = ["news", "latest", "today", "weather", "who is", "what is", "price", "score", "current", "search"]
    if enable_web_search and any(kw in prompt.lower() for kw in search_keywords):
        with st.spinner("Checking live information..."):
            search_context = perform_search(prompt)

    # API Request
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in st.session_state.messages[:-1]:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    
    final_content = prompt + (f"\n\n{search_context}" if search_context else "")
    api_messages.append({"role": "user", "content": final_content})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": api_messages,
        "temperature": 0.5, # Smooth balance between facts and creativity
        "max_tokens": 1024
    }

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            reply = res_data["choices"][0]["message"]["content"]
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.session_state.latest_reply = reply
            st.rerun()

    except Exception as e:
        st.error(f"Error: {str(e)}")
