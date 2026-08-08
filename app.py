import os
import json
import asyncio
import urllib.request
import streamlit as st
import streamlit.components.v1 as components
import edge_tts
from tavily import TavilyClient

# 1. Page Config & Futuristic Dark UI Layout
st.set_page_config(page_title="J.A.R.V.I.S. HUD", page_icon="🌐", layout="wide")

# Custom Stark HUD CSS Styling
st.markdown("""
<style>
    /* Dark Sci-Fi Background & Custom Glows */
    .stApp {
        background-color: #030812;
        color: #00f0ff;
        font-family: 'Orbitron', 'Segoe UI', sans-serif;
    }
    
    /* Glowing Title Panel */
    .hud-title {
        text-align: center;
        color: #00f0ff;
        text-shadow: 0 0 10px #00f0ff, 0 0 20px #00f0ff;
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: 3px;
        margin-bottom: 20px;
    }

    /* 3D Holographic Visualizer Ring (CSS Animation) */
    .holo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 20px 0;
    }
    .holo-ring {
        width: 140px;
        height: 140px;
        border-radius: 50%;
        border: 2px dashed #00f0ff;
        box-shadow: 0 0 15px #00f0ff, inset 0 0 15px #00f0ff;
        animation: spin 8s linear infinite;
        position: relative;
    }
    .holo-core {
        width: 90px;
        height: 90px;
        background: radial-gradient(circle, rgba(0,240,255,0.4) 0%, rgba(3,8,18,0.8) 70%);
        border-radius: 50%;
        position: absolute;
        top: 23px;
        left: 23px;
        box-shadow: 0 0 20px #00f0ff;
        animation: pulse 2s ease-in-out infinite alternate;
    }

    @keyframes spin { 100% { transform: rotate(360deg); } }
    @keyframes pulse { 0% { transform: scale(0.9); opacity: 0.7; } 100% { transform: scale(1.1); opacity: 1; } }

    /* Futuristic HUD Data Cards */
    .hud-card {
        background: rgba(4, 20, 36, 0.7);
        border: 1px solid #00f0ff;
        box-shadow: 0 0 15px rgba(0, 240, 255, 0.3);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        backdrop-filter: blur(5px);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .hud-card:hover {
        transform: translateY(-3px) scale(1.01);
        box-shadow: 0 0 25px rgba(0, 240, 255, 0.6);
    }
    
    .hud-header {
        color: #ffb700;
        font-size: 0.85rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 8px;
        border-bottom: 1px solid rgba(255, 183, 0, 0.3);
        padding-bottom: 4px;
    }

    /* Customize Streamlit Input Elements */
    div[data-baseweb="input"] {
        background-color: rgba(4, 20, 36, 0.8) !important;
        border: 1px solid #00f0ff !important;
        color: #00f0ff !important;
        box-shadow: 0 0 10px rgba(0, 240, 255, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# 2. Sidebar Configuration
st.sidebar.title("⚡ STARK SYSTEMS HUD")
voice_enabled = st.sidebar.toggle("🔊 Audio Output", value=True)
enable_web_search = st.sidebar.toggle("🌐 Live Data Ingestion", value=True)

VOICE_OPTION = st.sidebar.selectbox(
    "Synthesizer Engine",
    ["en-GB-RyanNeural", "en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    index=0
)

# 3. Header & Hologram Visualizer
st.markdown('<div class="hud-title">J.A.R.V.I.S. SYSTEM INTERFACE</div>', unsafe_allow_html=True)

# Render Animated 3D Arc Reactor / Hologram Ring
st.markdown("""
<div class="holo-container">
    <div class="holo-ring">
        <div class="holo-core"></div>
    </div>
</div>
""", unsafe_allow_html=True)

# API Keys
groq_api_key = st.secrets.get("GROQ_API_KEY", "").strip()
tavily_api_key = st.secrets.get("TAVILY_API_KEY", "").strip()

if not groq_api_key:
    st.warning("⚠️ GROQ_API_KEY is missing in Streamlit Secrets.")
    st.stop()

SYSTEM_PROMPT = """
You are J.A.R.V.I.S., an ultra-intelligent, articulate, and loyal AI assistant inspired by Iron Man.
- Address the user respectfully as 'Boss' or 'Sir'.
- Structure your response using clear HUD-style sections or bullet points where necessary.
- STRICT FACTUALITY RULE: When web search context is provided, rely SOLELY on those facts. If information is missing, explicitly state it rather than inventing details.
"""

async def text_to_speech_edge(text, voice):
    clean_text = text.replace("*", "").replace("#", "").replace("`", "")
    communicate = edge_tts.Communicate(clean_text, voice)
    audio_path = "jarvis_voice.mp3"
    await communicate.save(audio_path)
    return audio_path

def perform_accurate_search(query):
    if not tavily_api_key:
        return None, "[SYSTEM NOTE: Tavily API key missing.]"
    try:
        tavily = TavilyClient(api_key=tavily_api_key)
        response = tavily.search(query=query, search_depth="basic", max_results=3)
        results = response.get("results", [])
        
        if not results:
            return None, "No verified search data retrieved."
            
        context = ""
        structured_cards = []
        for res in results:
            context += f"- Source: {res['title']}\n  Snippet: {res['content']}\n"
            structured_cards.append({
                "title": res['title'],
                "url": res['url'],
                "snippet": res['content']
            })
        return structured_cards, context
    except Exception as e:
        return None, f"[Search Error: {str(e)}]"

# Session States
if "messages" not in st.session_state:
    st.session_state.messages = []
if "hud_data" not in st.session_state:
    st.session_state.hud_data = []

# Layout Split: Main Chat Console + Holographic Data Overlay Panel
chat_col, hud_col = st.columns([2, 1])

with chat_col:
    st.subheader("🖥️ Main Console")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

with hud_col:
    st.subheader("📡 Live HUD Data Telemetry")
    if st.session_state.hud_data:
        for item in st.session_state.hud_data:
            st.markdown(f"""
            <div class="hud-card">
                <div class="hud-header">LIVE DATA STREAM</div>
                <strong style="color: #00f0ff;">{item['title']}</strong><br>
                <small style="color: #a0e0ff;">{item['snippet'][:150]}...</small><br>
                <a href="{item['url']}" target="_blank" style="color: #ffb700; font-size: 0.8rem;">[Open Telemetry Link]</a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="hud-card">
            <div class="hud-header">SYSTEM STATUS</div>
            <span style="color: #00f0ff;">All sensors nominal. Waiting for query input...</span>
        </div>
        """, unsafe_allow_html=True)

# User Query Handler
if prompt := st.chat_input("Initiate command or request..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    search_context = ""
    hud_cards = None
    search_keywords = ["news", "latest", "today", "weather", "who is", "what is", "price", "score", "current", "event", "happened"]
    
    if enable_web_search and any(kw in prompt.lower() for kw in search_keywords):
        with st.spinner("⚡ Extracting live web stream..."):
            hud_cards, search_context = perform_accurate_search(prompt)
            if hud_cards:
                st.session_state.hud_data = hud_cards

    # Build API payload
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in st.session_state.messages[:-1]:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    
    final_user_content = prompt + (f"\n\n[VERIFIED DATA STREAM]:\n{search_context}" if search_context else "")
    api_messages.append({"role": "user", "content": final_user_content})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": api_messages,
        "temperature": 0.2,
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
            
            # Generate Audio
            if voice_enabled:
                audio_file = asyncio.run(text_to_speech_edge(reply, VOICE_OPTION))
                st.audio(audio_file, format="audio/mp3", autoplay=True)

            st.rerun()

    except urllib.error.HTTPError as e:
        st.error(f"HTTP Error {e.code}: {e.reason}")
    except Exception as e:
        st.error(f"API Error: {str(e)}")
