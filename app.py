import os
import json
import urllib.request
import streamlit as st

st.set_page_config(page_title="JARVIS AI Assistant", page_icon="🤖")
st.title("🤖 JARVIS AI Assistant")

# Retrieve free API key from Streamlit Cloud Secrets
groq_api_key = st.secrets.get("GROQ_API_KEY", "")

if not groq_api_key:
    st.warning("⚠️ GROQ_API_KEY is missing. Please add it to App Settings -> Secrets.")
    st.stop()

SYSTEM_PROMPT = """
You are JARVIS, an intelligent, articulate, and loyal AI assistant inspired by Iron Man.
- Address the user respectfully as 'Boss' or 'Sir'.
- Keep responses sharp, helpful, and concise.
"""

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

    # Prepare payload for Groq free cloud API
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in st.session_state.messages:
        api_messages.append({"role": msg["role"], "content": msg["content"]})

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
            "Authorization": f"Bearer {groq_api_key.strip()}",
            "Content-Type": "application/json"
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
        except Exception as e:
            st.error(f"API Error: {str(e)}")
