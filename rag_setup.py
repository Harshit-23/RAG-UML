import os
import fitz  # PyMuPDF
import shutil
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

def format_docs(docs, file_path="retrieved_docs.txt"):
    formatted_text = "\n\n".join(doc.page_content for doc in docs)
    with open(file_path, "w", encoding="utf-8") as f:
        for i, doc in enumerate(docs, 1):
            f.write(f"Document {i}:\n{doc.page_content}\n{'='*50}\n")
    return formatted_text

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text("text") for page in doc)

def load_rag_chain(api_key, model="gpt-4o-mini"):
    if not api_key:
        raise ValueError("API key is required to initialize the RAG model.")

    os.environ["OPENAI_API_KEY"] = api_key

    project_dir = os.getcwd()
    folder_path = os.path.join(project_dir, "dataset")
    os.makedirs(folder_path, exist_ok=True)

    all_texts = [
        extract_text_from_pdf(os.path.join(folder_path, f))
        for f in os.listdir(folder_path)
        if f.endswith(".pdf")
    ]
    document_text = "\n".join(all_texts)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    documents = [Document(page_content=chunk) for chunk in text_splitter.split_text(document_text)]

    # FAISS-based vectorstore using native save/load
    faiss_path = os.path.join(project_dir, "faiss_index")
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)

    if os.path.exists(faiss_path):
        try:
            vectorstore = FAISS.load_local(faiss_path, embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            print(f"⚠️ Failed to load FAISS index, rebuilding. Reason: {e}")
            shutil.rmtree(faiss_path)
            vectorstore = FAISS.from_documents(documents, embedding=embeddings)
            vectorstore.save_local(faiss_path)
    else:
        vectorstore = FAISS.from_documents(documents, embedding=embeddings)
        vectorstore.save_local(faiss_path)

    retriever = vectorstore.as_retriever()

    with open("uml_extraction_prompt.txt", "r", encoding="utf-8") as file:
        first_prompt_template = file.read()
    first_prompt = ChatPromptTemplate.from_template(first_prompt_template)

    with open("uml_generation_prompt.txt", "r", encoding="utf-8") as file:
        second_prompt_template = file.read()
    second_prompt = ChatPromptTemplate.from_template(second_prompt_template)

    llm_1 = ChatOpenAI(model_name=model, temperature=0.001, openai_api_key=api_key)
    llm_2 = ChatOpenAI(model_name=model, temperature=0.001, openai_api_key=api_key)

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

    return first_rag_chain, second_rag_chain
