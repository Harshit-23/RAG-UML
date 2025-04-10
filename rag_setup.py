import os
import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
# from dotenv import load_dotenv

# Load environment variables from .env file
# load_dotenv()

# Now you can access them safely
# LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2")
# LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT")
# LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set them as environment variables
# os.environ["LANGCHAIN_TRACING_V2"] = LANGCHAIN_TRACING_V2
# os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
# os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
# os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

def format_docs(docs, file_path="retrieved_docs.txt"):
    """Format retrieved documents and save them to a file for debugging."""
    formatted_text = "\n\n".join(doc.page_content for doc in docs)

    # Save retrieved documents to a file
    with open(file_path, "w", encoding="utf-8") as f:
        for i, doc in enumerate(docs, 1):
            f.write(f"Document {i}:\n{doc.page_content}\n{'='*50}\n")

    return formatted_text  # Ensure the pipeline still works

def extract_text_from_pdf(pdf_path):
    """Extract text from a given PDF file."""
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text("text") for page in doc)

def load_rag_chain(api_key, model="gpt-4o-mini"):
    """Loads and initializes the RAG pipeline using the provided API key and model."""
    if not api_key:
        raise ValueError("API key is required to initialize the RAG model.")
    
    os.environ["OPENAI_API_KEY"] = api_key  # Set API key globally for OpenAI

    print("🔄 Initializing RAG Model...")

    # Define dataset folder
    project_dir = os.getcwd()
    folder_path = os.path.join(project_dir, "dataset")
    os.makedirs(folder_path, exist_ok=True)

    # Extract text from PDFs
    all_texts = [extract_text_from_pdf(os.path.join(folder_path, f)) for f in os.listdir(folder_path) if f.endswith(".pdf")]
    document_text = "\n".join(all_texts)

    # Chunking for retrieval
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    chunks = text_splitter.split_text(document_text)
    documents = [Document(page_content=chunk) for chunk in chunks]

    # Define a persistent storage path for ChromaDB
    chroma_db_path = os.path.join(os.getcwd(), "chroma_db")
    os.makedirs(chroma_db_path, exist_ok=True)

    # Load or Create Persistent ChromaDB
    vectorstore = Chroma(
        persist_directory=chroma_db_path,  # ✅ Chroma auto-saves
        embedding_function=OpenAIEmbeddings(openai_api_key=api_key)
    )

    # If Chroma is empty, populate it
    if vectorstore._collection.count() == 0:
        print("🔄 Populating ChromaDB with new documents...")
        vectorstore.add_documents(documents)

    retriever = vectorstore.as_retriever()

    # Read the template from file
    with open("prompt_template.txt", "r", encoding="utf-8") as file:
        template = file.read()
    
    # Define Prompt
    prompt = ChatPromptTemplate.from_template(template)

    # Load LLM Model
    # llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    llm = ChatOpenAI(model_name=model, temperature=0.001, openai_api_key=api_key)

    # Define RAG Chain
    rag_chain = (
        {"context": retriever | format_docs, "user_contexts": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    print("✅ RAG Model Initialized Successfully!")
    return rag_chain
