import os
import re
import json
import requests
import streamlit as st

# --- Define Directories ---
PUML_FOLDER = os.path.join(os.getcwd(), "PUML")
DIAGRAM_FOLDER = os.path.join(os.getcwd(), "DIAGRAMS")

# Ensure Directories Exist
os.makedirs(PUML_FOLDER, exist_ok=True)
os.makedirs(DIAGRAM_FOLDER, exist_ok=True)

# --- Read GPT Output ---
gpt_output_file = "gpt_output.txt"

def extract_plantuml_blocks(file_path):
    # Ensure the output directory exists
    output_dir = "PUML"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    
    # Regex pattern to match PlantUML blocks
    pattern = re.compile(r"@startuml(.*?)@enduml", re.DOTALL)
    
    matches = pattern.findall(content)
    if not matches:
        print("No PlantUML diagrams found.")
        return []
    
    extracted_files = []
    for match in matches:
        # Extract diagram name from the comment
        name_match = re.search(r"'\s*===\s*(.*?)\s*===", match)
        if name_match:
            diagram_name = name_match.group(1).replace(":", " ").strip().replace(" ", "_")  # Normalize filename
            file_name = f"{diagram_name}.puml"
            file_path = os.path.join(output_dir, file_name)
            
            # Save the PlantUML diagram
            with open(file_path, "w", encoding="utf-8") as output_file:
                output_file.write(f"@startuml{match}@enduml")
            extracted_files.append(file_name)
    
    print(f"Extracted {len(extracted_files)} PlantUML diagrams into '{output_dir}' folder.")
    return extracted_files

# --- Extract and Save PUML Files ---
if os.path.exists(gpt_output_file):
    uml_blocks = extract_plantuml_blocks(gpt_output_file)

    # Process each extracted UML diagram
    for file_name in uml_blocks:
        puml_filename = os.path.join(PUML_FOLDER, file_name)
        with open(puml_filename, "r", encoding="utf-8") as puml_file:
            uml_code = puml_file.read()

        print(f"✅ Extracted '{file_name}' and saved to: {puml_filename}")

# --- Convert PUML to PNG Using Kroki ---
KROKI_PLANTUML_URL = "https://kroki.io/plantuml/png"

def get_uml_image(uml_code, file_name):
    """Generate UML image from PUML code."""
    headers = {"Content-Type": "application/json"}
    payload = json.dumps({"diagram_source": uml_code})
    
    response = requests.post(KROKI_PLANTUML_URL, headers=headers, data=payload)
    
    if response.status_code == 200:
        image_filename = os.path.join(DIAGRAM_FOLDER, f"{file_name}.png")
        with open(image_filename, "wb") as file:
            file.write(response.content)
    elif response.status_code == 504:
            st.error("Could not reach Kroki server.")
    else:
        print(f"❌ Error generating UML diagram for {file_name}")

# --- Process PUML Files ---
for puml_file in os.listdir(PUML_FOLDER):
    if puml_file.endswith(".puml"):
        file_name = os.path.splitext(puml_file)[0]
        with open(os.path.join(PUML_FOLDER, puml_file), "r", encoding="utf-8") as file:
            uml_code = file.read()
        get_uml_image(uml_code, file_name)
