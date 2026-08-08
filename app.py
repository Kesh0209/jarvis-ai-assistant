import json
import urllib.request
import streamlit as st
import streamlit.components.v1 as components
from duckduckgo_search import DDGS

st.set_page_config(page_title="JARVIS AI Assistant", page_icon="🤖", layout="wide")

# Sidebar Configuration
st.sidebar.title("🤖 JARVIS Settings")
voice_enabled = st.sidebar.toggle("🔊 Enable Voice Responses", value=True)
enable_web_search = st.sidebar.toggle("🌐 Live Web Search", value=True)

st.title("🤖 JARVIS AI Assistant")

# Retrieve free API key from Streamlit Cloud Secrets
groq_api_key = st.secrets.get("GROQ_API_KEY", "").strip()

if not groq_api_key:
    st.warning("⚠️ GROQ_API_KEY is missing. Please add it to App Settings -> Secrets.")
    st.stop()

SYSTEM_PROMPT = """
You are JARVIS, an ultra-intelligent, articulate, and loyal AI assistant inspired by Iron Man.
- Address the user respectfully as 'Boss' or 'Sir'.
- Keep responses sharp, helpful, concise, and smart.
- When live web search context is provided, synthesize it accurately to deliver up-to-date answers.
"""

def perform_search(query):
    """Fetches real-time duckduckgo search snippets."""
    try:
        results = DDGS().text(query, max_results=3)
        if not results:
            return ""
        context = "\n[LIVE INTERNET SEARCH RESULTS]:\n"
        for res in results:
            context += f"- Title: {res['title']}\n  Snippet: {res['body']}\n"
        return context
    except Exception:
        return ""

def speak_text(text):
    """Executes browser JavaScript Text-to-Speech synthesis."""
    # Clean text for JavaScript execution
    clean_text = text.replace('"', '\\"').replace('\n', ' ').replace("'", "\\'")
    js_code = f"""
    <script>
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel(); // Stop any active speech
            var msg = new SpeechSynthesisUtterance("{clean_text}");
            msg.rate = 1.0;
            msg.pitch = 0.9; // JARVIS pitch feel
            msg.lang = 'en-US';
            window.speechSynthesis.speak(msg);
        }}
    </script>
    """
    components.html(js_code, height=0)

# Initialize session chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User prompt input
if prompt := st.chat_input("Ask JARVIS anything..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Perform internet search if toggled or needed
    search_context = ""
    if enable_web_search:
        search_keywords = ["news", "latest", "today", "weather", "who is", "what is", "price", "score", "current"]
        if any(kw in prompt.lower() for kw in search_keywords):
            with st.spinner("🔍 JARVIS is searching the web..."):
                search_context = perform_search(prompt)

    # Prepare payload for Groq free cloud API
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in st.session_state.messages[:-1]:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Append user prompt with web context if available
    final_user_content = prompt + (f"\n\n{search_context}" if search_context else "")
    api_messages.append({"role": "user", "content": final_user_content})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": api_messages,
        "temperature": 0.6,
        "max_tokens": 1024
    }

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
                
                # Speak out response if toggled ON
                if voice_enabled:
                    speak_text(reply)

        except urllib.error.HTTPError as e:
            st.error(f"HTTP Error {e.code}: {e.reason}")
        except Exception as e:
            st.error(f"API Error: {str(e)}")
