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

def format_docs(docs, file_path="retrieved_docs.txt"):
    """Format retrieved documents and save them to a file for debugging."""
    formatted_text = "\n\n".join(doc.page_content for doc in docs)

    # Save retrieved documents to a file
    with open(file_path, "w", encoding="utf-8") as f:
        for i, doc in enumerate(docs, 1):
            f.write(f"Document {i}:\n{doc.page_content}\n{'='*50}\n")

    return formatted_text  # Ensure the pipeline still works

def load_rag_chain():
    """Loads and initializes the RAG pipeline using two LLMs."""
    print("🔄 Initializing Two-Stage RAG Model...")

    # Load dataset and extract text from PDFs
    project_dir = os.getcwd()
    folder_path = os.path.join(project_dir, "dataset")
    os.makedirs(folder_path, exist_ok=True)

    def extract_text_from_pdf(pdf_path):
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        return text

    all_texts = [extract_text_from_pdf(os.path.join(folder_path, f)) for f in os.listdir(folder_path) if f.endswith(".pdf")]
    document_text = "\n".join(all_texts)

    # Chunking for retrieval
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    documents = [Document(page_content=chunk) for chunk in text_splitter.split_text(document_text)]

    # Persistent ChromaDB storage
    chroma_db_path = os.path.join(os.getcwd(), "chroma_db")
    os.makedirs(chroma_db_path, exist_ok=True)
    vectorstore = Chroma(persist_directory=chroma_db_path, embedding_function=OpenAIEmbeddings())

    # Populate ChromaDB if empty
    if vectorstore._collection.count() == 0:
        print("🔄 Populating ChromaDB...")
        vectorstore.add_documents(documents)

    retriever = vectorstore.as_retriever()

    # Load first LLM prompt template (UML Extraction)
    with open("uml_extraction_prompt.txt", "r", encoding="utf-8") as file:
        first_prompt_template = file.read()
    
    first_prompt = ChatPromptTemplate.from_template(first_prompt_template)
    
    # Load second LLM prompt template (PlantUML Generation)
    with open("uml_generation_prompt.txt", "r", encoding="utf-8") as file:
        second_prompt_template = file.read()
    
    second_prompt = ChatPromptTemplate.from_template(second_prompt_template)

    # Load expertise information from `expertise_info.txt`
    expertise_info_path = os.path.join(os.getcwd(), "expertise_info.txt")
    if os.path.exists(expertise_info_path):
        with open(expertise_info_path, "r", encoding="utf-8") as file:
            expertise_info = file.read()
    else:
        expertise_info = "No additional expertise information provided."

    # Load LLM Models
    llm_1 = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.001)
    llm_2 = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.001)

    # Define Two-Step RAG Chain
    first_rag_chain = (
        {"context": retriever | format_docs, "query": RunnablePassthrough()}
        | first_prompt
        | llm_1
        | StrOutputParser()
    )

    second_rag_chain = (
        {"all_contexts": RunnablePassthrough()}
        | second_prompt
        | llm_2
        | StrOutputParser()
    )

    print("Chain of Thoguht RAG Model Initialized Successfully!")
    return first_rag_chain, second_rag_chain
