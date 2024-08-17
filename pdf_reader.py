import streamlit as st
from streamlit import session_state as ss
from streamlit_javascript import st_javascript
from streamlit_pdf_viewer import pdf_viewer
import os
import streamlit.components.v1 as components,html
import base64
import replicate
from config import REPLICATE_API_TOKEN
import fitz  # PyMuPDF
import pyperclip
from pathlib import Path
from streamlit_javascript import st_javascript
from pathlib import Path


st.set_page_config(layout="wide")
  


# Declare variable.
if 'pdf_ref' not in ss:
    ss.pdf_ref = None

with st.sidebar:
    st.title('🦙💬 Llama 2 Chatbot')
    if REPLICATE_API_TOKEN:
        st.success('API key already provided!', icon='✅')
        replicate_api = REPLICATE_API_TOKEN
    else:
        replicate_api = st.text_input('Enter Replicate API token:', type='password')
        if not (replicate_api.startswith('r8_') and len(replicate_api)==40):
            st.warning('Please enter your credentials!', icon='⚠️')
        else:
            st.success('Proceed to entering your prompt message!', icon='👉')
    text_lookup = st.text_input("Look for", max_chars=50,value="")
    #page_number = st.number_input("Page number", min_value=1, value=1, step=1)
    os.environ['REPLICATE_API_TOKEN'] = replicate_api
    llm = 'a16z-infra/llama7b-v2-chat:4f0a4744c7295c024a1de15e1a63c880d3da035fa1f49bfd344fe076074c8eea'


## fitz get coordinates of selected text on a page

cols = st.columns(spec=[2,1],gap='small')


with cols[0]:
    # Access the uploaded ref via a key.
    original_doc = st.file_uploader("Choose a PDF file", type=("pdf"),key="pdf")
    if original_doc:
        with open("temp.pdf", "wb") as f:
            f.write(original_doc.getbuffer())
        with fitz.open('temp.pdf') as doc:
            #stream=original_doc.getvalue()
            page_number = st.sidebar.number_input(
                "Page number", min_value=1, max_value=doc.page_count, value=1, step=1
            )
            page = doc.load_page(page_number - 1)
            if text_lookup:
                areas = page.search_for(text_lookup)
                for area in areas:
                    page.add_highlight_annot(area)
                # save the updated page to the original document
                doc.save(doc.name,incremental=True,encryption=0)
            selected_page_pdf = fitz.open()  # Create a new PDF document
            selected_page_pdf.insert_pdf(doc, from_page=page_number-1, to_page=page_number-1)
            # Display the selected page using an iframe
            # Save the selected page to a temporary file
            selected_page_path = f"temp_page_{page_number}.pdf"
            selected_page_pdf.save(selected_page_path)
            selected_page_pdf.close()
            with open(selected_page_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                pdf_display = f'<iframe id="myIframe" src="data:application/pdf;base64,{base64_pdf}" width="90%" height="800" type="application/pdf">'
                st.markdown(pdf_display,unsafe_allow_html=True)
            # Scroll to and highlight text
            html_c = st_javascript('''<script>
                    function showAlert(event) {
                        alert('You clicked at coordinates (' + event.clientX + ', ' + event.clientY + ')');
                    }
                    // Add event listener to the document
                    document.addEventListener('click', showAlert);
                    ''')
            components.html(html_c)
            #st.markdown({html_c})
            mjs = '''
            <script>
                // Function to handle clicks inside the iframe
                function handleIframeClick(event) {
                    // Send coordinates back to the parent
                    alert("Hello")
                    const iframe = document.getElementById('myIframe');
                    const rect = iframe.getBoundingClientRect();
                    const x = event.clientX - rect.left;
                    const y = event.clientY - rect.top;
                    window.parent.postMessage({x: x, y: y}, '*');
                }
                // Add an event listener to the iframe
                window.addEventListener('message', function(event) {
                    if (event.data.type === 'click') {
                        handleIframeClick(event);
                    }
                });
                // Setup message listener for receiving click coordinates
                window.addEventListener('message', function(event) {
                    if (event.data.type === 'click') {
                        console.log(`Clicked at (${event.data.x}, ${event.data.y}) in the iframe`);
                        window.parent.postMessage({type: 'click', x: event.data.x, y: event.data.y}, '*');
                    }
                });
            </script>
            '''
            #Clean up temporary file
            if os.path.exists(selected_page_path):
                os.remove(selected_page_path)
            #             function getMousePosition(iframe, event) {
            #     let rect = iframe.getBoundingClientRect();
            #     let x = event.clientX - rect.left;
            #     let y = event.clientY - rect.top;
            #     return x;
            # }
            # let canvasElem = document.querySelector("iframe");
            # canvasElem.addEventListener("mousedown", function (e) {
            #     getMousePosition(canvasElem, e);
            # }); 
    temperature = st.sidebar.slider('temperature', min_value=0.01, max_value=5.0, value=0.1, step=0.01)
    top_p = st.sidebar.slider('top_p', min_value=0.01, max_value=1.0, value=0.9, step=0.01)
    max_length = st.sidebar.slider('max_length', min_value=32, max_value=128, value=120, step=8)

with cols[1]:
    st.subheader('Chat Window')
    if "messages" not in st.session_state.keys():
        st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]

    # Display or clear chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    def clear_chat_history():
        st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]
    st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

    # Function for generating LLaMA2 response. Refactored from https://github.com/a16z-infra/llama2-chatbot
    def generate_llama2_response(prompt_input):
        string_dialogue = "You are a helpful assistant. You do not respond as 'User' or pretend to be 'User'. You only respond once as 'Assistant'. Keep your answer as short as possible."
        for dict_message in st.session_state.messages:
            if dict_message["role"] == "user":
                string_dialogue += "User: " + dict_message["content"] + "\n\n"
            else:
                string_dialogue += "Assistant: " + dict_message["content"] + "\n\n"
        output = replicate.run(llm, 
                               input={"prompt": f"{string_dialogue} {prompt_input} Assistant: ",
                                      "temperature":temperature, "top_p":top_p, "max_length":max_length, "repetition_penalty":1})
        return output

    # User-provided prompt
    if prompt := st.chat_input(disabled=not replicate_api):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)



    # Generate a new response if last message is not from assistant
    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = generate_llama2_response(prompt)
                placeholder = st.empty()
                full_response = ''
                for item in response:
                    full_response += item
                    placeholder.markdown(full_response)
                placeholder.markdown(full_response)
        message = {"role": "assistant", "content": full_response}
        st.session_state.messages.append(message)
