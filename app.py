import os
import shutil
import streamlit as st
from PIL import Image
from rag_setup import load_rag_chain

# --- Remove Existing Folders Before Execution (Only when a new scenario is entered) ---
if "scenario_entered" not in st.session_state:
    st.session_state.scenario_entered = False  # Tracks whether the user has submitted a scenario
    if os.path.exists("DIAGRAMS"):
        shutil.rmtree("DIAGRAMS")
    if os.path.exists("PUML"):
        shutil.rmtree("PUML")

# --- Set Up Streamlit Page ---
st.set_page_config(page_title="RAG UML Diagram Generator", layout="wide")

# --- Custom CSS for UI Improvements ---
st.markdown(
    """
    <style>
    /* Widen the centered content block */
    .block-container {
        max-width: 1100px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    /* Make text box wider */
    .stTextArea textarea {
        font-size: 16px !important;
        width: 100% !important;
    }

    /* Keep black border by default */
    textarea, input, button {
        border: 2px solid black !important;
        border-radius: 5px !important;
    }
    
    /* Green glow on focus */
    textarea:focus, input:focus {
        border-color: black !important;
        box-shadow: 0 0 5px green !important;
    }

    /* Reduce button size */
    div.stButton > button, div.stDownloadButton > button {
        font-size: 10px !important;
        padding: 3px 6px !important;
        height: 25px !important;
    }

    /* Display images at a smaller size without affecting downloads */
    .diagram-img {
        max-height: 450px !important;
        width: auto !important;
        display: block;
        margin: auto;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Page Title ---
st.title("RAG-Based UML Diagram Generator")
st.write("Enter a detailed software scenario below. The system will generate UML diagrams using a RAG model.")

# --- Cache the RAG Chain to prevent reloading ---
@st.cache_resource(show_spinner=False)
def get_rag_chain():
    return load_rag_chain()  # Directly load and cache the RAG model

# Load RAG Model with Custom Spinner
with st.spinner("Initializing RAG Model..."):
    if "rag_chain" not in st.session_state:
        st.session_state.rag_chain = get_rag_chain()  # Caching to prevent reloading

rag_chain = st.session_state.rag_chain  # Store in session_state

# --- Large Text Area for Input ---
user_input = st.text_area("Enter your scenario:", height=300, key="user_input", help="Provide a detailed description.")

# --- Processing Message Placeholder ---
processing_placeholder = st.empty()

# --- Process Input ---
if st.button("Generate UML Diagrams"):
    if user_input.strip():
        # Remove old diagrams when a new scenario is entered
        shutil.rmtree("DIAGRAMS", ignore_errors=True)
        shutil.rmtree("PUML", ignore_errors=True)
        os.makedirs("DIAGRAMS", exist_ok=True)
        os.makedirs("PUML", exist_ok=True)

        st.session_state.scenario_entered = True  # Track scenario input

        # Save Input to File
        with open("user_scenario.txt", "w", encoding="utf-8") as file:
            file.write(user_input)

        processing_placeholder.write("⏳ **Processing... This may take a minute.**")

        # Invoke the RAG Model
        try:
            response = rag_chain.invoke(user_input)

            # Save the response to a file
            with open("gpt_output.txt", "w", encoding="utf-8") as output_file:
                output_file.write(response)

            # Generate UML Diagrams
            os.system("python generate_diagrams.py")

            st.success("✅ UML diagrams generated successfully!")
            processing_placeholder.empty()  # Remove processing message
        except Exception as e:
            st.error(f"❌ An error occurred: {e}")
    else:
        st.warning("⚠️ Please enter a scenario before generating diagrams.")

# --- Display Generated Diagrams (Only if a scenario has been entered) ---
if st.session_state.scenario_entered:
    st.subheader("Generated UML Diagrams")

    diagram_folder = "DIAGRAMS"
    puml_folder = "PUML"

    os.makedirs(diagram_folder, exist_ok=True)
    os.makedirs(puml_folder, exist_ok=True)

    diagram_files = sorted([f for f in os.listdir(diagram_folder) if f.endswith(".png")])
    puml_files = {f.replace(".puml", ""): os.path.join(puml_folder, f) for f in os.listdir(puml_folder) if f.endswith(".puml")}

    if diagram_files:
        def format_diagram_name(filename):
            """Convert 'class_diagram.png' to 'Class Diagram'."""
            return filename.replace("_", " ").replace(".png", "").title()

        for diagram in diagram_files:
            diagram_path = os.path.join(diagram_folder, diagram)
            title = format_diagram_name(diagram)
            puml_filename = os.path.splitext(diagram)[0]  # Extract file name without extension
            puml_path = puml_files.get(puml_filename)

            st.markdown(f"<h3 style='font-size:22px;'>{title}</h3>", unsafe_allow_html=True)

            # Display images at smaller size but retain full resolution for downloads
            st.image(diagram_path, use_container_width=False, caption=None, output_format="PNG", clamp=True)


            # Stack Download Buttons (Smaller size)
            with st.container():
                with open(diagram_path, "rb") as file:
                    st.download_button(
                        label="⬇️ Image",
                        data=file,
                        file_name=diagram,
                        mime="image/png",
                        key=f"image_{diagram}"
                    )

                if puml_path:
                    with open(puml_path, "rb") as file:
                        st.download_button(
                            label="⬇️ PlantUML",
                            data=file,
                            file_name=f"{puml_filename}.puml",
                            mime="text/plain",
                            key=f"puml_{puml_filename}"
                        )

    else:
        st.info("Click 'Generate UML Diagrams' to generate UML diagrams.")
