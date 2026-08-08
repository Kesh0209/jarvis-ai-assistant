import os
import json
import asyncio
import urllib.request
import streamlit as st
import edge_tts
from tavily import TavilyClient

st.set_page_config(page_title="JARVIS AI Assistant", page_icon="🤖", layout="wide")

st.sidebar.title("🤖 JARVIS Settings")
voice_enabled = st.sidebar.toggle("🔊 Enable Voice Responses", value=True)
enable_web_search = st.sidebar.toggle("🌐 Live Web Search", value=True)

# Select a deep, natural British/American neural voice
VOICE_OPTION = st.sidebar.selectbox(
    "Voice Model",
    ["en-GB-RyanNeural", "en-US-ChristopherNeural", "en-GB-ThomasNeural"],
    index=0
)

st.title("🤖 JARVIS AI Assistant")

# Retrieve API Keys
groq_api_key = st.secrets.get("GROQ_API_KEY", "").strip()
tavily_api_key = st.secrets.get("TAVILY_API_KEY", "").strip()

if not groq_api_key:
    st.warning("⚠️ GROQ_API_KEY is missing in Streamlit Secrets.")
    st.stop()

SYSTEM_PROMPT = """
You are JARVIS, an ultra-intelligent, articulate, and loyal AI assistant inspired by Iron Man.
- Address the user respectfully as 'Boss' or 'Sir'.
- Keep responses concise, articulate, and direct.
- STRICT FACTUALITY RULE: When web search context is provided, rely SOLELY on those facts. If the information is not present in the search results, explicitly state that you do not have verified real-time data rather than inventing facts. Do NOT hallucinate news or current events.
"""

# Neural Text-to-Speech Function using Edge-TTS
async def text_to_speech_edge(text, voice):
    # Filter out Markdown formatting so JARVIS doesn't read out symbols like asterisks
    clean_text = text.replace("*", "").replace("#", "").replace("`", "")
    communicate = edge_tts.Communicate(clean_text, voice)
    audio_path = "jarvis_voice.mp3"
    await communicate.save(audio_path)
    return audio_path

def perform_accurate_search(query):
    """Retrieves high-accuracy factual context via Tavily AI Search."""
    if not tavily_api_key:
        return "[SYSTEM NOTE: Tavily API key missing. Cannot perform live search.]"
    try:
        tavily = TavilyClient(api_key=tavily_api_key)
        response = tavily.search(query=query, search_depth="basic", max_results=3)
        results = response.get("results", [])
        
        if not results:
            return "No verified search results found."
            
        context = "\n[VERIFIED LIVE INTERNET SEARCH CONTEXT]:\n"
        for res in results:
            context += f"- Source: {res['title']}\n  Snippet: {res['content']}\n"
        return context
    except Exception as e:
        return f"[Search Error: {str(e)}]"

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Process User Input
if prompt := st.chat_input("Ask JARVIS anything..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Strict intent check for web search
    search_context = ""
    search_keywords = ["news", "latest", "today", "weather", "who is", "what is", "price", "score", "current", "event", "happened"]
    
    if enable_web_search and any(kw in prompt.lower() for kw in search_keywords):
        with st.spinner("🔍 JARVIS is verifying real-time web context..."):
            search_context = perform_accurate_search(prompt)

    # Reconstruct Messages Payload
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in st.session_state.messages[:-1]:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    
    final_user_content = prompt + (f"\n\n{search_context}" if search_context else "")
    api_messages.append({"role": "user", "content": final_user_content})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": api_messages,
        "temperature": 0.2, # Lower temperature reduces hallucinations and enforces strict adherence to context
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

    with st.chat_message("assistant"):
        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                reply = res_data["choices"][0]["message"]["content"]
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                
                # Generate and play realistic neural voice audio
                if voice_enabled:
                    with st.spinner("🎙️ Generating JARVIS voice response..."):
                        audio_file = asyncio.run(text_to_speech_edge(reply, VOICE_OPTION))
                        st.audio(audio_file, format="audio/mp3", autoplay=True)

        except urllib.error.HTTPError as e:
            st.error(f"HTTP Error {e.code}: {e.reason}")
        except Exception as e:
            st.error(f"API Error: {str(e)}")
