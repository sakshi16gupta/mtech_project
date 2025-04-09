import streamlit as st
import json
import os
import sys
print(sys.path)
sys.path.append(os.path.abspath(os.curdir)+"/")
from Inferencing.search import run_search
from Inferencing.feedback import run_feedback

st.set_page_config(page_title="Chatbot with Feedback")

st.title("🤖 Chatbot with Feedback")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = {}

# Chat input
user_input = st.chat_input("Say something...")

# Handle user input
if user_input:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    os.chdir('./Inferencing')
    response = json.loads(run_search(json.dumps({ 
            "data": [user_input]
        })))["fdk_response"]
    os.chdir('./Frontend')
    st.session_state.messages.append({"role": "assistant", "content": response})

# Display chat and feedback
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

    # Show feedback for assistant messages
    if message["role"] == "assistant" and idx not in st.session_state.feedback_given:
        feedback_col1, feedback_col2 = st.columns(2)
        with feedback_col1:
            if st.button("👍 Yes, helpful", key=f"yes_{idx}"):
                st.session_state.feedback_given[idx] = "yes"
                st.success("Thanks for your feedback!")
        with feedback_col2:
            if st.button("👎 No, not helpful", key=f"no_{idx}"):
                st.session_state.feedback_given[idx] = "no"

    # If user clicked "No", show text area for detailed feedback
    if (
        message["role"] == "assistant"
        and st.session_state.feedback_given.get(idx) == "no"
    ):
        feedback_text = st.text_area("What went wrong?", key=f"feedback_text_{idx}")
        if feedback_text:
            st.success("Thanks for your feedback!")
            # Optionally save feedback here
            print("#"*50)
            print(os.curdir)
            os.chdir('./Inferencing')
            run_feedback(json.dumps({
                    "fdk_request": {
                        "query_id": "8357dff9-1ab1-458b-bc30-bd193ae820d6-20250409",
                        "query": [
                            "machine not working"
                        ],
                        "feedback": {
                            "description": "feedback",
                            "rating": 5
                        }
                    }
                }) )
            os.chdir('./Frontend')
            st.session_state.feedback_given[idx] = "submitted"
