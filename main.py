import streamlit as st
import pandas as pd
import uuid
import requests

# Set the page config to change the tab title and add a favicon
st.set_page_config(
    page_title="BigQuery Chatbot",
    page_icon=":robot_face:",  # You can replace this with a URL to a favicon image
    layout="centered",
    initial_sidebar_state="auto"
)

# Generate a unique session ID
session_id = str(uuid.uuid4())

url = "https://html5solutions.app.n8n.cloud/webhook/7eba5fc5-2a52-4ec2-bc37-54aa358a22a1"

if "history" not in st.session_state:
    st.session_state.history = []

# Set the title of the Streamlit app
st.title("BigQuery ChatBot")

def send_message():
    user_input = st.session_state.user_input
    if user_input.strip():
        body = {
            "sessionId": session_id,
            "chatInput": user_input,
            "action": "sendMessage"
        }
        res = requests.post(url, json=body)
        # print("checking Response data:", res.text)
        # Check if the response content is not empty
        if res.content:
            try:
                res = res.json()
            except ValueError:
                # Handle JSON decode error
                st.session_state.history.append({
                    "question": user_input,
                    "answer": f"Error decoding JSON response: {res.text}"
                })
                st.session_state.user_input = ""
                return
            
            # Debug print to verify response data
            # print("Response data:", res)

            # Check if the response is in the expected format
            if isinstance(res, list) and len(res) > 0 and "output" in res[0]:
                data = res[0]["output"]

                # Parse the response data into a list of dictionaries
                rows = [row for row in data.split('\n') if row.strip()]
                columns = rows[0].split(' | ')
                records = [dict(zip(columns, row.split(' | '))) for row in rows[1:] if row]

                # Debug print to verify parsed records
                # print("Parsed records:", records)

                # Convert the list of dictionaries into a DataFrame
                df = pd.DataFrame(records)

                st.session_state.history.append({
                    "question": user_input,
                    "answer": df if len(columns) > 1 else data
                })
            else:
                # Handle unexpected response format
                st.session_state.history.append({
                    "question": user_input,
                    "answer": f"Unexpected response format: {res}"
                })
        else:
            # Handle empty response content
            st.session_state.history.append({
                "question": user_input,
                "answer": "Empty response from server"
            })

        st.session_state.user_input = ""

# Display chat history
st.write("### Chat History")
for chat in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(f"*You:* {chat['question']}")
    with st.chat_message("assistant"):
        if isinstance(chat["answer"], pd.DataFrame):
            st.dataframe(chat["answer"])  # Displays the response as a table
        else:
            st.markdown(chat["answer"])  # Displays the response as text

# Sidebar for chat history
st.sidebar.title("Chat History")
for i, chat in enumerate(st.session_state.history):
    with st.sidebar.expander(f"Chat {i+1}"):
        st.markdown(f"**You:** {chat['question']}")
        if isinstance(chat["answer"], pd.DataFrame):
            st.dataframe(chat["answer"])  # Displays the response as a table
        else:
            st.markdown(f"**Assistant:** {chat['answer']}")

# User input field
user_input = st.text_input(
    "Type your question here...",
    key="user_input",
    placeholder="Ask me anything...",
    on_change=send_message
)
