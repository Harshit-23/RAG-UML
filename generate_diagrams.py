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
    with open(file_path, "r", encoding="utf-8") as file:
        response_text = file.read()

    # Updated regex to properly capture the diagram title and UML code
    pattern = r"@startuml\s*\n?' === (.*?) ===\s*\n([\s\S]*?)@enduml"

    matches = re.findall(pattern, response_text, re.DOTALL)

    # Return list of tuples (diagram_type, UML_code)
    return [(m[0].strip().replace(" ", "_").lower(), f"@startuml\n' === {m[0]} ===\n{m[1]}\n@enduml") for m in matches]

# --- Extract and Save PUML Files ---
if os.path.exists(gpt_output_file):
    uml_blocks = extract_plantuml_blocks(gpt_output_file)

    for diagram_type, uml_code in uml_blocks:
        puml_filename = os.path.join(PUML_FOLDER, f"{diagram_type}.puml")
        with open(puml_filename, "w", encoding="utf-8", newline="\n") as puml_file:
            puml_file.write(uml_code.strip() + "\n")
        
        print(f"✅ Extracted '{diagram_type}' and saved to: {puml_filename}")

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
