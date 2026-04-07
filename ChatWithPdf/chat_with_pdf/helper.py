import os
from decouple import config
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA

# ================= CONFIGURATION =================
PINECONE_API_KEY = config('PINECONE_API_KEY')
INDEX_NAME = config('PINECONE_INDEX_NAME', default='chat-with-pdf')
OPENROUTER_API_KEY = config('OPENROUTER_API_KEY')
OPENROUTER_BASE_URL = config('OPENROUTER_BASE_URL', default='https://openrouter.ai/api/v1')

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

# ================= INITIALIZATION =================
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base=OPENROUTER_BASE_URL
)

def get_pinecone_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    if INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(
            name=INDEX_NAME,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    return INDEX_NAME

# ================= CORE FUNCTIONS =================

def ingest_pdf_to_pinecone(file_path):
    try:
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        chunks = text_splitter.split_documents(documents)

        index_name = get_pinecone_index()

        PineconeVectorStore.from_documents(
            chunks,
            embeddings,
            index_name=index_name
        )
        return "Success"
    except Exception as e:
        print(f"Error in Ingestion: {str(e)}")
        raise e

def get_answer_from_pdf(question):
    try:
        vectorstore = PineconeVectorStore.from_existing_index(
            index_name=INDEX_NAME,
            embedding=embeddings
        )

        llm = ChatOpenAI(
            model="google/gemini-2.0-flash-001",
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3})
        )

        response = qa_chain.invoke({"query": question})
        return response.get("result", "Sorry, I could not find an answer.")

    except Exception as e:
        print(f"Error in Retrieval: {str(e)}")
        return f"Technical Error: {str(e)}"