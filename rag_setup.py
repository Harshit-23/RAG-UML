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
    
    # template = """
    # Role Definition:
    # You are an expert software engineer and UML designer with deep knowledge of software architecture, object-oriented design, and system modelling. Your task is to generate precise, syntactically correct, and logically complete PlantUML diagrams based on a given software scenario.

    # User-Provided Scenario:
    # {query}

    # Instructions:
    # 1.	Analyse the input scenario:
    # a)	Identify key entities, actors, use cases, classes, objects, states, and interactions.
    # b)	Extract relationships between these components, including inheritance, composition, association, dependencies.
    # c)	Recognize system behaviour over time to ensure proper structuring of sequence and state diagrams.

    # 2.	Generate UML Diagrams in the correct PlantUML syntax. Provide correct and complete PlantUML code for the following UML diagrams:
    # a)	Use Case Diagram (System Actors & Use Cases):
    # 	Actors must be enclosed in "actor" elements and connected to use cases with -- or -->.
    # 	All system functionalities must be enclosed inside a "rectangle" representing the system boundary.
    # 	Use include and extends relationships where applicable for modular representation.
    # 	Ensure all actors have valid use case interactions (Avoid isolated actors).

    # b)	Class Diagram (System Structure & Relationships):
    # 	Use correct UML relationships:
    # Inheritance / Generalization (--|>)
    # Composition (*--)
    # Aggregation (o--)
    # Association (--)
    # 	Use correct cardinalities to specify relationships:
    # 1.	One-to-One (`User "1" -- "1" Order`)
    # 2.	One-to-Many (`User "1" -- "*" Order`)
    # 3.	Many-to-One (`Order "*" -- "1" Payment`)
    # 4.	Many-to-Many (`Student "*" -- "*" Course`)
    # 	Ensure every class has proper attributes and methods.
    # 	Avoid floating classes (every class must be linked to at least one other entity).

    # c)	Activity Diagram (Process Flow & Workflow Representation):
    # 	Use activity nodes with syntax `:Activity Name;`.
    # 	Start the process using `start` or `[*] --> FirstActivity;`.
    # 	End the process using `stop`, `end`, or `LastActivity --> [*];`.
    # 	Use decision nodes with `if (Condition?) then (Yes)` and `else (No)` followed by `endif`.
    # 	Represent parallel activities using `fork`, `fork again`, and `end fork`.
    # 	Include loops with `repeat`, `repeat while (Condition?)`, or `while (Condition?)` followed by `endwhile`.
    # 	Ensure all activities are logically connected to represent a complete workflow.

    # d)	Sequence Diagram (Object Interaction Over Time)
    # 	Follow correct lifeline notation (Use participant for entities).
    # 	Use arrows (-> or -->) for interactions.
    # 	Ensure messages are clearly defined, showing method calls, returns, and interactions.
    # 	Every participant must have meaningful interactions.

    # e)	Collaboration Diagram (Object Flow Representation)
    # 	Use directed associations (->) to represent interactions between objects.
    # 	Ensure the diagram follows a flowchart-like structure rather than a timeline-based approach.
    # 	Correctly represent interactions among multiple entities.
    # 	Number the functions/interactions between various objects/entities sequentially to maintain clarity and order.

    # f)	State Diagram (Object Lifecycle & Transitions)
    # 	Use transitions (-->) to show state progression.
    # 	Use `state "xyz" as XYZ` syntax while defining a state.
    # 	Ensure complex objects have multiple possible states.
    # 	Do not isolate states (every state must have an entry and exit point).

    # 3.	Ensure Consistency and Accuracy:
    # a)	Follow UML best practices to avoid redundancy and maintain clarity.
    # b)	Ensure all diagram elements align with the described software scenario.
    # c)	Use meaningful and concise naming conventions.

    # 4.	Output Format (Follow strictly):
    # a)	Each diagram should be enclosed in triple backticks (` ``` `) with "plantuml" specified for markdown compatibility.
    # b)	Clearly label each diagram with a heading/comment (Each diagram’s code should be labelled like this: ' === Class Diagram === in the plantUML code right after ‘@startuml’)
    # c)	The output must contain only the PlantUML code (with all codes as a single snippet), with no additional text.


    # Sample Context (DO NOT use the formatting of the context below in your response. Use formatting mentioned above in the instructions):
    # {context}

    # """

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
