import streamlit as st
from streamlit import session_state as ss
from streamlit_pdf_viewer import pdf_viewer
import os
import base64
import replicate
import fitz  # PyMuPDF
import pyperclip
from pathlib import Path
from streamlit_javascript import st_javascript
from shapely.geometry import Polygon
from pathlib import Path
from shapely.ops import cascaded_union


st.set_page_config(layout="wide")

def print_hightlight_text(page, rect):
    """Return text containted in the given rectangular highlighted area.

    Args:
        page (fitz.page): the associated page.
        rect (fitz.Rect): rectangular highlighted area.
    """
    words = page.getText("words")  # list of words on page
    words.sort(key=lambda w: (w[3], w[0]))  # ascending y, then x
    mywords = [w for w in words if fitz.Rect(w[:4]).intersects(rect)]
    group = groupby(mywords, key=lambda w: w[3])
    for y1, gwords in group:
        print(" ".join(w[4] for w in gwords))


class Annotator():
  def __init__(self, doc: Path, page: int):
    self.doc = fitz.open(doc)
    self.PAGE = self.doc[page - 1]
    self.padding = 2
  
  def splitContent(self, content: str):
    self.content = content.split(" ")
    self.getTextRects()
  
  def drawShape(self, color: tuple):
    shape = self.PAGE.new_shape()
    shape.drawPolyline(self.points)
    shape.finish(color=(0, 0, 0), fill=color, stroke_opacity=0.15, fill_opacity=0.15)
    shape.commit()
    self.doc.save(Path("[Annotated].pdf"), garbage=1, deflate=True, clean=True)

  def getTextRects(self):
    rects = [self.PAGE.search_for(i) for i in self.content] # This should produce a list of fitz.Rect
    if rects:
        rects = [self.padRect(r) for r in rects] # add padding
    polygons = [self.rectToPolygon for r in rects] # translate fitz.Rects to shape.Polygon
    rectsMerged = cascaded_union(polygons) # merge all polygons
    self.points = list(rectsMerged.exterior.coords)
  
  def padRect(self, rect: fitz.Rect):
    return rect + (-self.padding * 2, -self.padding, self.padding * 2, self.padding)
   
  def rectToPolygon(self, rect: fitz.Rect):
    upperLeft = (rect[0], rect[1])
    upperRight = (rect[2], rect[1])
    lowerRight = (rect[2], rect[3])
    lowerLeft = (rect[0], rect[3])
    return Polygon([upperLeft, upperRight, lowerRight, lowerLeft])
  


# Declare variable.
if 'pdf_ref' not in ss:
    ss.pdf_ref = None

with st.sidebar:
#     st.title('🦙💬 Llama 2 Chatbot')
#     # if 'REPLICATE_API_TOKEN' in st.secrets:
#     #     st.success('API key already provided!', icon='✅')
#     #     replicate_api = st.secrets['REPLICATE_API_TOKEN']
#     # else:
    replicate_api = st.text_input('Enter Replicate API token:', type='password')
    text_lookup = st.text_input("Look for", max_chars=50)
    if not (replicate_api.startswith('r8_') and len(replicate_api)==40):
        st.warning('Please enter your credentials!', icon='⚠️')
    else:
        st.success('Proceed to entering your prompt message!', icon='👉')
    os.environ['REPLICATE_API_TOKEN'] = replicate_api
    llm = 'a16z-infra/llama7b-v2-chat:4f0a4744c7295c024a1de15e1a63c880d3da035fa1f49bfd344fe076074c8eea'
    temperature = st.sidebar.slider('temperature', min_value=0.01, max_value=5.0, value=0.1, step=0.01)
    top_p = st.sidebar.slider('top_p', min_value=0.01, max_value=1.0, value=0.9, step=0.01)
    max_length = st.sidebar.slider('max_length', min_value=32, max_value=128, value=120, step=8)



cols = st.columns(spec=[2,1],gap='small')


with cols[0]:
    # Access the uploaded ref via a key.
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    if uploaded_file is not None:
        # Save the uploaded PDF to a temporary location
        with open("temp.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Open the PDF file
        pdf_document = fitz.open("temp.pdf")
        num_pages = pdf_document.page_count
        st.write(f"The PDF file has {num_pages} pages.")
        # Select a page number
        page_number = st.number_input("Select page number", 1, num_pages, 1)
        # Display the selected page
        page = pdf_document.load_page(page_number - 1)
        selected_page_pdf = fitz.open()  # Create a new PDF document
        selected_page_pdf.insert_pdf(pdf_document, from_page=page_number-1, to_page=page_number-1)
        # Save the selected page to a temporary file
        selected_page_path = f"temp_page_{page_number}.pdf"
        #annot = selected_page_pdf[0].first_annot
        #st.write(print_hightlight_text(selected_page_pdf[0],annot.rect))
        selected_page_pdf.save(selected_page_path)
        selected_page_pdf.close()
        # annotator = Annotator(Path(selected_page_path), page = 1)
        # annotator.splitContent(str(pyperclip.paste()))
        # annotator.drawShape()
        # Display the selected page using an iframe
        with open(selected_page_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="90%" height="800" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
        

        # Clean up temporary file
        if os.path.exists(selected_page_path):
            os.remove(selected_page_path)
        #binary_data = page.tobytes()
        #pdf_viewer(input=binary_data, width=700)
        # pix = page.get_pixmap()
        # img_path = f"page_{page_number}.png"
        # pix.save(img_path)
        # st.image(img_path)
        # if text_lookup:
        #     areas = page.search_for(text_lookup)
        #     for area in areas:
        #         page.add_rect_annot(area)
        #     st.image(pix.tobytes(), use_column_width=True)


        # # Clean up temporary images
        # for i in range(1, num_pages + 1):
        #     img_path = f"page_{i}.png"
        #     if os.path.exists(img_path):
        #         os.remove(img_path)

    # st.file_uploader("Upload PDF file", type=('pdf'), key='pdf')

    # if ss.pdf:
    #     ss.pdf_ref = ss.pdf  # backup

    # # Now you can access "pdf_ref" anywhere in your app.
    # if ss.pdf_ref:
    #     #binary_data = ss.pdf_ref.getvalue()
    #     #pdf_viewer(input=binary_data, width=500)
    #     ui_width = st_javascript("window.innerWidth")
    #     displayPDF(ss.pdf_ref, ui_width -10)

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
