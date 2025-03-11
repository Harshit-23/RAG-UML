import os
import streamlit as st
from PIL import Image
from rag_setup import load_rag_chain

# --- Set Up Streamlit Page ---
st.set_page_config(page_title="RAG UML Diagram Generator", layout="wide")

# --- Custom CSS for Styling ---
st.markdown(
    """
    <style>
    .big-textarea textarea {
        font-size: 16px !important;
        height: 300px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Page Title ---
st.title("RAG-Based UML Diagram Generator")
st.write("Enter a detailed software scenario below. The system will generate UML diagrams using a RAG model.")

# --- Cache the RAG Chain to Load Once ---
@st.cache_resource
def get_rag_chain():
    return load_rag_chain()

# Load RAG Model (Runs Once)
rag_chain = get_rag_chain()

# --- Large Text Area for Input ---
user_input = st.text_area("Enter your scenario:", height=300, key="user_input", help="Provide a detailed description.")

# --- Process Input ---
if st.button("Generate UML Diagrams"):
    if user_input.strip():
        # Save Input to File
        with open("user_scenario.txt", "w", encoding="utf-8") as file:
            file.write(user_input)

        st.write("⏳ **Processing... This may take a minute.**")

        # Invoke the RAG Model
        try:
            response = rag_chain.invoke(user_input)

            # Save the response to a file
            with open("gpt_output.txt", "w", encoding="utf-8") as output_file:
                output_file.write(response)

            # Generate UML Diagrams
            os.system("python generate_diagrams.py")

            st.success("✅ UML diagrams generated successfully!")
        except Exception as e:
            st.error(f"❌ An error occurred: {e}")

    else:
        st.warning("⚠️ Please enter a scenario before generating diagrams.")

# --- Display Generated Diagrams ---
st.subheader("Generated UML Diagrams")
diagram_folder = os.path.join(os.getcwd(), "DIAGRAMS")

if os.path.exists(diagram_folder):
    diagram_files = [f for f in os.listdir(diagram_folder) if f.endswith(".png")]

    if diagram_files:
        num_columns = 3  # Number of columns for displaying images
        cols = st.columns(num_columns)

        for idx, diagram in enumerate(sorted(diagram_files)):
            with cols[idx % num_columns]:  # Distribute images in columns
                st.image(Image.open(os.path.join(diagram_folder, diagram)), caption=diagram, use_container_width=True)
    else:
        st.info("Click 'Generate UML Diagrams' to generate UML diagrams.")
else:
    os.makedirs(diagram_folder, exist_ok=True)
    st.info("Click 'Generate UML Diagrams' to generate UML diagrams.")
