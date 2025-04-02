import os
import re
import json
import requests
import streamlit as st
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# --- Define Directories ---
PUML_FOLDER = os.path.join(os.getcwd(), "PUML")
DIAGRAM_FOLDER = os.path.join(os.getcwd(), "DIAGRAMS")

# Ensure Directories Exist
os.makedirs(PUML_FOLDER, exist_ok=True)
os.makedirs(DIAGRAM_FOLDER, exist_ok=True)

# --- Read GPT Output ---
gpt_output_file = "gpt_output.txt"

client = openai.OpenAI(api_key=OPENAI_API_KEY)

KROKI_PLANTUML_URL = "https://kroki.io/plantuml/png"

def get_gpt_response(prompt):
    try:
        # Make a request to OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Specify the model to use
            messages=[{"role": "user", "content": prompt}]
        )
        # Extract the assistant's reply
        reply = response.choices[0].message.content
        return reply
    except Exception as e:
        return f"Error: {str(e)}"

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
def regenerate_uml(puml_code, diagram_name):
    prompt = f"""
    The following PlantUML code for the diagram '{diagram_name}' has syntax errors. 
    Please correct it using the correct and latest plantUML syntax for all components used in the code 
    and return only the corrected PlantUML code with no extra comments. Do not change any logic related to the diagram.
    
    {puml_code}
    """
    corrected_code = get_gpt_response(prompt)
    corrected_file = os.path.join("PUML", f"{diagram_name}.puml")
    with open(corrected_file, "w", encoding="utf-8") as file:
        file.write(corrected_code)
    return corrected_file

def get_uml_image(uml_code, file_name):
    headers = {"Content-Type": "application/json"}
    payload = json.dumps({"diagram_source": uml_code})
    
    response = requests.post(KROKI_PLANTUML_URL, headers=headers, data=payload)
    
    if response.status_code == 200:
        with open(os.path.join("DIAGRAMS", f"{file_name}.png"), "wb") as file:
            file.write(response.content)
    else:
        print(f"❌ Error generating {file_name}. Regenerating...")
        new_puml_file = regenerate_uml(uml_code, file_name)
        with open(new_puml_file, "r", encoding="utf-8") as file:
            new_uml_code = file.read()
        return get_uml_image(new_uml_code, file_name)

# def get_uml_image(uml_code, file_name):
#     """Generate UML image from PUML code."""
#     headers = {"Content-Type": "application/json"}
#     payload = json.dumps({"diagram_source": uml_code})
    
#     response = requests.post(KROKI_PLANTUML_URL, headers=headers, data=payload)
    
#     if response.status_code == 200:
#         image_filename = os.path.join(DIAGRAM_FOLDER, f"{file_name}.png")
#         with open(image_filename, "wb") as file:
#             file.write(response.content)
#     elif response.status_code == 504:
#             st.error("Could not reach Kroki server.")
#     else:
#         print(f"❌ Error generating UML diagram for {file_name}")

# --- Process PUML Files ---
for puml_file in os.listdir(PUML_FOLDER):
    if puml_file.endswith(".puml"):
        file_name = os.path.splitext(puml_file)[0]
        with open(os.path.join(PUML_FOLDER, puml_file), "r", encoding="utf-8") as file:
            uml_code = file.read()
        get_uml_image(uml_code, file_name)
