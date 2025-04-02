import os
import shutil
import streamlit as st
from PIL import Image
from rag_setup import load_rag_chain
import zipfile
from io import BytesIO

# --- Remove Existing Folders Before Execution (Only when a new scenario is entered) ---
if "scenario_entered" not in st.session_state:
    st.session_state.scenario_entered = False  # Tracks whether the user has submitted a scenario
    if os.path.exists("DIAGRAMS"):
        shutil.rmtree("DIAGRAMS")
    if os.path.exists("PUML"):
        shutil.rmtree("PUML")

# --- Set Up Streamlit Page ---
st.set_page_config(page_title="RAG UML Diagram Generator", layout="wide")

# Read custom CSS from file
css_file = "custom_styles.css"
if os.path.exists(css_file):
    with open(css_file, "r", encoding="utf-8") as file:
        custom_css = file.read()
else:
    custom_css = ""  # Fallback if file is missing

# Apply the CSS
st.markdown(f"<style>{custom_css}</style>", unsafe_allow_html=True)

# --- Page Title ---
st.title("RAG-Based UML Diagram Generator")
st.write("Enter a detailed software scenario below. The system will generate UML diagrams using a RAG model.")

# --- Cache the RAG Chains to prevent reloading ---
@st.cache_resource(show_spinner=False)
def get_rag_chains():
    return load_rag_chain()

# Load RAG Model with Custom Spinner
with st.spinner("Initializing RAG Model..."):
    if "first_rag_chain" not in st.session_state or "second_rag_chain" not in st.session_state:
        st.session_state.first_rag_chain, st.session_state.second_rag_chain = get_rag_chains()

# --- Load RAG Chains ---
first_rag_chain, second_rag_chain = get_rag_chains()
st.session_state.first_rag_chain = first_rag_chain
st.session_state.second_rag_chain = second_rag_chain

# --- Large Text Area for Input ---
user_input = st.text_area("Enter your scenario:", height=300, key="user_input", help="Provide a detailed description.")

# --- Extra Instructions (Optional) ---
expertise_input = st.text_area("Provide additional expertise information (optional):", 
                               height=150, key="expertise_input",
                               help="This is optional. If provided, it will be used to refine the UML generation process.")

# --- Processing Message Placeholder ---
processing_placeholder = st.empty()

# --- Folders Setup ---
diagram_folder = "DIAGRAMS"
puml_folder = "PUML"

# List of files to delete
files_to_delete = ["retrieved_docs.txt", "expertise_info.txt", "gpt_output.txt", "user_scenario.txt"]

# List of folders to delete
folders_to_delete = ["DIAGRAMS", "PUML"]

# --- Process Input ---
if st.button("Generate UML Diagrams"):
    print("Button Clicked!")
    if user_input.strip():
        # Remove old folders
        for folder in folders_to_delete:
            shutil.rmtree(folder, ignore_errors=True)
            os.makedirs(folder, exist_ok=True)

        # Remove old files
        for file in files_to_delete:
            if os.path.exists(file):
                os.remove(file)

        st.session_state.scenario_entered = True  # Track scenario input

        # Save User Scenario
        with open("user_scenario.txt", "w", encoding="utf-8") as file:
            file.write(user_input)

        # Save Expertise Information
        with open("expertise_info.txt", "w", encoding="utf-8") as file:
            file.write(expertise_input.strip() if expertise_input.strip() else "No additional expertise information provided.")

        processing_placeholder.write("⏳ **Processing... This may take a few minutes.**")

         # Step 1: Invoke the first RAG chain
        try:
            uml_output = first_rag_chain.invoke(user_input)

            # Save UML output to a file
            with open("uml_output.txt", "w", encoding="utf-8") as file:
                file.write(uml_output)

            # Step 2: Read all required files and create a single prompt context
            def read_file(file_path, default_text="No information provided."):
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as file:
                        return file.read().strip()
                return default_text

            user_input_content = read_file("user_scenario.txt")
            uml_output_content = uml_output
            expertise_info_content = read_file("expertise_info.txt")

            all_contexts = f"""
            User-provided Scenario:
            {user_input_content}

            UML information:
            {uml_output_content}

            Expertise information:
            {expertise_info_content}
            """

            # Step 3: Pass the formatted string to the second RAG chain
            final_response = second_rag_chain.invoke(all_contexts)

            # Save the final response to a file
            with open("gpt_output.txt", "w", encoding="utf-8") as output_file:
                output_file.write(final_response)

            # Generate UML Diagrams
            os.system("python generate_diagrams.py")

            st.success("✅ UML diagrams generated successfully!")
            processing_placeholder.empty()

        except Exception as e:
            st.error(f"❌ An error occurred: {e}")
    else:
        st.warning("⚠️ Please enter a scenario before generating diagrams.")

# --- Display Generated Diagrams (Only if a scenario has been entered) ---
if st.session_state.scenario_entered:
    st.subheader("Generated UML Diagrams")

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
        # --- Create ZIP File Helper ---
        def create_zip(folder_path, zip_filename):
            """Compress all files in a folder into a ZIP file."""
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, arcname=file)  # Keep relative paths inside ZIP
            zip_buffer.seek(0)  # Reset pointer to start
            return zip_buffer

        # --- Layout for Two Side-by-Side Wide Buttons ---
        col1, col2 = st.columns(2)

        # --- Download All Images as ZIP ---
        with col1:
            if os.listdir(diagram_folder):  # Ensure images exist
                image_zip = create_zip(diagram_folder, "uml_diagrams.zip")
                st.download_button(
                    label="📂 Download All Images",
                    data=image_zip,
                    file_name="UML_Diagrams.zip",
                    mime="application/zip",
                    use_container_width=True  # Make the button wide
                )

        # --- Download All PlantUML Files as ZIP ---
        with col2:
            if os.listdir(puml_folder):  # Ensure PlantUML files exist
                puml_zip = create_zip(puml_folder, "plantuml_codes.zip")
                st.download_button(
                    label="📂 Download All PlantUML Codes",
                    data=puml_zip,
                    file_name="PlantUML_Codes.zip",
                    mime="application/zip",
                    use_container_width=True  # Make the button wide
                )

    else:
        st.info("Click 'Generate UML Diagrams' to generate UML diagrams.")
