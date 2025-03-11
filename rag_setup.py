import os
import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Now you can access them safely
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set them as environment variables
os.environ["LANGCHAIN_TRACING_V2"] = LANGCHAIN_TRACING_V2
os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

def load_rag_chain():
    """Loads and initializes the RAG pipeline."""
    print("🔄 Initializing RAG Model...")

    # Define dataset folder
    project_dir = os.getcwd()
    folder_path = os.path.join(project_dir, "dataset")
    os.makedirs(folder_path, exist_ok=True)

    # Function to extract text from PDFs
    def extract_text_from_pdf(pdf_path):
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        return text

    # Extract text from all PDFs in 'dataset' folder
    all_texts = []
    for file in os.listdir(folder_path):
        if file.endswith(".pdf"):
            pdf_path = os.path.join(folder_path, file)
            text = extract_text_from_pdf(pdf_path)
            all_texts.append(text)

    # Combine extracted text
    document_text = "\n".join(all_texts)

    # Chunking for retrieval
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(document_text)
    documents = [Document(page_content=chunk) for chunk in chunks]

    # Define a persistent storage path for ChromaDB
    chroma_db_path = os.path.join(os.getcwd(), "chroma_db")
    os.makedirs(chroma_db_path, exist_ok=True)

    # Load or Create Persistent ChromaDB
    vectorstore = Chroma(
        persist_directory=chroma_db_path,  # ✅ Chroma auto-saves
        embedding_function=OpenAIEmbeddings()
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
    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

    # Define RAG Chain
    rag_chain = (
        {"context": retriever | (lambda docs: "\n\n".join(doc.page_content for doc in docs)), "query": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    print("✅ RAG Model Initialized Successfully!")
    return rag_chain
