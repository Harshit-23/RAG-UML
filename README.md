# RAG-Based UML Diagram Generator (Streamlit)

This project is a Retrieval-Augmented Generation (RAG) application built with Streamlit. It integrates OpenAI's GPT models (LLM) and ChromaDB (Vector Database) for automated UML diagram generation using a RAG model.

The application supports two branches:
1) `main` Branch: Incorporates Chain of Thought (CoT) reasoning for improved responses.
2) `non-cot` Branch: Does not use Chain of Thought, providing an alternative approach.

Additionally, we have refined the prompts using prompt engineering to enhance response accuracy.

## Steps to run the project

### 1. Create and Activate a Virtual Environment

Using `conda` (or any virtual environment manager of your choice):

```bash
conda create -n myenv python=3.11.2
conda activate myenv
```

### 2. Install the necessary dependencies listed in `requirements.txt`

```bash
pip install -r requirements.txt
```

### 3. Run the Streamlit Application

```bash
streamlit run streamlit_app.py
```
