import streamlit as st
import json
import os
import sys
print(sys.path)
sys.path.append('../')
from Inferencing.search import run_search
st.set_page_config(page_title="Simple Chatbot")

st.title("🤖 Simple Chatbot")

# Initialize the chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
user_input = st.chat_input("Say something...")

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    os.chdir('../Inferencing')
    response = json.loads(run_search(json.dumps({ 
            "data": ['Machine not working']
        })))["fdk_response"]
    os.chdir('../Frontend')
    # # Generate a simple response (replace with your own logic or model)
    # response = f"You said: {user_input}"

    # Add assistant response
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.json(response)

    # Feedback option
    feedback = st.radio("Was this response helpful?", ("Yes", "No"), key=f"feedback_{len(st.session_state.messages)}")

    if feedback:
        def send_feedback(feedback_value, additional_feedback=None):
            print(f"Feedback received: {feedback_value}")
            if additional_feedback:
                print(f"Additional feedback: {additional_feedback}")

        if feedback == "No":
            additional_feedback = st.text_area("Please describe the problem:")
            if additional_feedback:
                send_feedback(feedback, additional_feedback)
        else:
            send_feedback(feedback)
