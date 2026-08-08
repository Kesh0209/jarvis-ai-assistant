import os
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq

st.set_page_config(page_title="J.A.R.V.I.S.", page_icon="🎙️", layout="centered")

# Siri UI Styling
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

# API Key Validation
groq_api_key = st.secrets.get("GROQ_API_KEY", "").strip()

if not groq_api_key:
    st.warning("⚠️ GROQ_API_KEY is missing in Streamlit Secrets.")
    st.stop()

groq_client = Groq(api_key=groq_api_key)

SYSTEM_PROMPT = """
You are J.A.R.V.I.S., a loyal, highly intelligent, articulate personal assistant inspired by Iron Man.
- Address the user as 'Boss' or 'Sir'.
- Speak naturally, directly, and concisely.
- Utilize your live web connectivity to provide real-time facts, current time, news, and weather.
"""

if "messages" not in st.session_state:
    st.session_state.messages = []
if "processed_audio_id" not in st.session_state:
    st.session_state.processed_audio_id = None

# Sidebar Controls
st.sidebar.title("⚙️ Controls")
voice_enabled = st.sidebar.toggle("🔊 Speak Out Loud", value=True)
if st.sidebar.button("🛑 STOP SPEAKING"):
    components.html("<script>window.speechSynthesis.cancel();</script>", height=0)

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_query = None

# Microphone Input
st.write("🎙️ **Tap to Speak:**")
audio_file = st.audio_input("Record Voice", label_visibility="collapsed")

if audio_file:
    audio_id = f"{audio_file.name}_{audio_file.size}"
    if st.session_state.processed_audio_id != audio_id:
        with st.spinner("Processing speech..."):
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

# Text Input Fallback
text_input = st.chat_input("Type to JARVIS...")
if text_input:
    user_query = text_input

# Execute Query with Auto Web Search
if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})

    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in st.session_state.messages[:-1]:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    api_messages.append({"role": "user", "content": user_query})

    with st.spinner("JARVIS is connecting to live web streams..."):
        try:
            # groq/compound natively runs real-time web searches server-side
            response = groq_client.chat.completions.create(
                model="groq/compound",
                messages=api_messages,
                temperature=0.3
            )
            
            reply = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": reply})

            # Speak Response
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
            st.error(f"Error: {str(e)}")
