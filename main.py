import streamlit as st
import pandas as pd
import uuid
import requests
import re

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
# url= "https://html5solutions.app.n8n.cloud/webhook-test/7eba5fc5-2a52-4ec2-bc37-54aa358a22a1"
if "history" not in st.session_state:
    st.session_state.history = []

# Set the title of the Streamlit app
st.title("BigQuery ChatBot")

def parse_table_data(text):
    print("Starting parse_table_data with text:", text[:100])  # Print first 100 chars
    # Extract text between code blocks
    code_block_pattern = r"```\n(.*?)\n```"
    code_blocks = re.findall(code_block_pattern, text, re.DOTALL)
    print("Found code blocks:", len(code_blocks))
    
    if not code_blocks:
        print("No code blocks found")
        return None, text
    
    table_data = code_blocks[0].strip()
    pre_text = text.split("```")[0].strip()
    print("Pre-text:", pre_text)
    print("Table data:", table_data[:100])  # Print first 100 chars
    
    # Split into lines and clean
    lines = [line.strip() for line in table_data.split('\n') if line.strip()]
    print("Number of lines:", len(lines))
    
    if len(lines) < 2:
        print("Not enough lines")
        return None, text
    
    # Get headers
    headers = [h.strip() for h in lines[0].split('|')]
    print("Headers:", headers)
    
    # Get data rows
    rows = []
    for line in lines[1:]:
        # Use regex to split by | but preserve empty cells
        cells = re.split(r'\|', line)
        cells = [cell.strip() for cell in cells]
        print("Row cells:", cells)
        if len(cells) == len(headers):
            rows.append(cells)
    
    if not rows:
        print("No valid rows found")
        return None, text
    
    # Create DataFrame
    df = pd.DataFrame(rows, columns=headers)
    print("Created DataFrame with shape:", df.shape)
    return df, pre_text

def send_message():
    try:
        user_input = st.session_state.user_input
        if not user_input or not user_input.strip():
            return

        # Prepare chat history for the API request
        chat_history = []
        for chat in st.session_state.history:
            try:
                chat_history.append({
                    "role": "user",
                    "content": chat["question"]
                })
                if isinstance(chat["answer"], dict) and "text" in chat["answer"]:
                    chat_history.append({
                        "role": "assistant",
                        "content": chat["answer"]["text"]
                    })
                elif isinstance(chat["answer"], str):
                    chat_history.append({
                        "role": "assistant",
                        "content": chat["answer"]
                    })
                elif isinstance(chat["answer"], pd.DataFrame):
                    chat_history.append({
                        "role": "assistant",
                        "content": chat["answer"].to_string()
                    })
            except Exception as e:
                print(f"Error processing chat history: {str(e)}")
                continue

        body = {
            "sessionId": session_id,
            "chatInput": user_input,
            "action": "sendMessage",
            "history": chat_history
        }
        
        try:
            res = requests.post(url, json=body)
            res.raise_for_status()  # Raise an exception for bad status codes
        except requests.exceptions.RequestException as e:
            st.session_state.history.append({
                "question": user_input,
                "answer": f"Error making API request: {str(e)}"
            })
            st.session_state.user_input = ""
            return

        if not res.content:
            st.session_state.history.append({
                "question": user_input,
                "answer": "Empty response from server"
            })
            st.session_state.user_input = ""
            return

        try:
            data = res.json()
        except ValueError as e:
            st.session_state.history.append({
                "question": user_input,
                "answer": f"Error decoding JSON response: {str(e)}"
            })
            st.session_state.user_input = ""
            return

        if not isinstance(data, list) or not data:
            st.session_state.history.append({
                "question": user_input,
                "answer": "Invalid response format: Expected a non-empty list"
            })
            st.session_state.user_input = ""
            return

        response_data = data[0]
        if not isinstance(response_data, dict):
            st.session_state.history.append({
                "question": user_input,
                "answer": "Invalid response format: Expected a dictionary"
            })
            st.session_state.user_input = ""
            return

        if "output" not in response_data:
            st.session_state.history.append({
                "question": user_input,
                "answer": "Invalid response format: Missing 'output' field"
            })
            st.session_state.user_input = ""
            return

        output_text = response_data["output"]
        if not isinstance(output_text, str):
            st.session_state.history.append({
                "question": user_input,
                "answer": "Invalid response format: 'output' should be a string"
            })
            st.session_state.user_input = ""
            return

        # Handle different types of responses
        if "```" not in output_text and not output_text.startswith("Hello!") and "No record found" not in output_text:
            st.session_state.history.append({
                "question": user_input,
                "answer": output_text
            })
        elif "```" in output_text:
            try:
                df, pre_text = parse_table_data(output_text)
                if df is not None:
                    st.session_state.history.append({
                        "question": user_input,
                        "answer": {
                            "text": pre_text,
                            "dataframe": df
                        }
                    })
                else:
                    st.session_state.history.append({
                        "question": user_input,
                        "answer": output_text
                    })
            except Exception as e:
                print(f"Error parsing table: {str(e)}")
                st.session_state.history.append({
                    "question": user_input,
                    "answer": output_text
                })
        else:
            st.session_state.history.append({
                "question": user_input,
                "answer": output_text
            })

    except Exception as e:
        print(f"Unexpected error in send_message: {str(e)}")
        st.session_state.history.append({
            "question": user_input,
            "answer": f"An unexpected error occurred: {str(e)}"
        })
    finally:
        st.session_state.user_input = ""

# Display chat history
st.write("### Chat History")
for chat in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(f"*You:* {chat['question']}")
    with st.chat_message("assistant"):
        if isinstance(chat["answer"], dict) and "text" in chat["answer"] and "dataframe" in chat["answer"]:
            st.markdown(chat["answer"]["text"])
            # Configure the dataframe display
            st.dataframe(
                chat["answer"]["dataframe"],
                use_container_width=True,
                hide_index=True
            )
        elif isinstance(chat["answer"], pd.DataFrame):
            st.dataframe(
                chat["answer"],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.markdown(chat["answer"])

# Sidebar for chat history
st.sidebar.title("Chat History")

# Add clear history button
if st.sidebar.button("Clear History"):
    st.session_state.history = []
    st.rerun()

# Display chat history in sidebar with timestamps
for i, chat in enumerate(st.session_state.history):
    with st.sidebar.expander(f"Chat {i+1}", expanded=False):
        st.markdown(f"**You:** {chat['question']}")
        if isinstance(chat["answer"], dict) and "text" in chat["answer"] and "dataframe" in chat["answer"]:
            st.markdown(chat["answer"]["text"])
            st.dataframe(
                chat["answer"]["dataframe"],
                use_container_width=True,
                hide_index=True
            )
        elif isinstance(chat["answer"], pd.DataFrame):
            st.dataframe(
                chat["answer"],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.markdown(f"**Assistant:** {chat['answer']}")

# User input field
user_input = st.text_input(
    "Type your question here...",
    key="user_input",
    placeholder="Ask me anything...",
    on_change=send_message
)
