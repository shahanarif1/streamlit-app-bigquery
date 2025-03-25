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
    user_input = st.session_state.user_input
    if user_input.strip():
        # Prepare chat history for the API request
        chat_history = []
        for chat in st.session_state.history:
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

        body = {
            "sessionId": session_id,
            "chatInput": user_input,
            "action": "sendMessage",
            "history": chat_history  # Include chat history in the request
        }
        print("Sending request with history:", chat_history)  # Debug print
        res = requests.post(url, json=body)
        print("checking Response data:", res.text)
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
            
            # Check if the response is in the expected format
            if isinstance(res, list) and len(res) > 0:
                data = res

                # Check if the response should not be shown in a table
                if "output" in data[0]:
                    output_text = data[0]["output"]
                    print("Processing output text:", output_text[:100])  # Print first 100 chars
                    
                    # Handle simple chat messages
                    if "```" not in output_text and not output_text.startswith("Hello!") and "No record found" not in output_text:
                        print("Handling as simple message")
                        st.session_state.history.append({
                            "question": user_input,
                            "answer": output_text
                        })
                    # Handle table responses
                    elif "```" in output_text:
                        print("Found code block, attempting to parse table")
                        try:
                            df, pre_text = parse_table_data(output_text)
                            if df is not None:
                                print("Successfully parsed table")
                                st.session_state.history.append({
                                    "question": user_input,
                                    "answer": {
                                        "text": pre_text,
                                        "dataframe": df
                                    }
                                })
                            else:
                                print("Failed to parse table")
                                st.session_state.history.append({
                                    "question": user_input,
                                    "answer": output_text
                                })
                        except Exception as e:
                            print(f"Error parsing table: {str(e)}")  # Debug print
                            st.session_state.history.append({
                                "question": user_input,
                                "answer": output_text
                            })
                    # Handle special messages (Hello, No record found)
                    else:
                        print("Handling as special message")
                        st.session_state.history.append({
                            "question": user_input,
                            "answer": output_text
                        })
                else:
                    print("No output field in response")
                    # Convert the response data into a DataFrame
                    df = pd.DataFrame(data)

                    # Ensure all columns have consistent types
                    for column in df.columns:
                        if df[column].apply(lambda x: isinstance(x, list)).any():
                            df[column] = df[column].apply(lambda x: str(x) if isinstance(x, list) else x)

                    st.session_state.history.append({
                        "question": user_input,
                        "answer": df
                    })
            else:
                print("Unexpected response format")
                # Handle unexpected response format
                st.session_state.history.append({
                    "question": user_input,
                    "answer": f"Unexpected response format: {data}"
                })
        else:
            print("Empty response content")
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
