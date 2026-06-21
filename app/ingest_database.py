from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from uuid import uuid4
import os

# import the .env file
from dotenv import load_dotenv
load_dotenv()
DATA_PATH = os.getenv("DATA_PATH")
if not DATA_PATH:
    raise ValueError("Missing path! Please set DATA_PATH in .env.")
CHROMA_PATH = os.getenv("CHROMA_PATH")
if not CHROMA_PATH:
    raise ValueError("Missing path! Please set CHROMA_PATH in .env.")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    encode_kwargs={"normalize_embeddings": True},
)
# initiate the vector store
vector_store = Chroma(
    collection_name="parking_spaces",
    embedding_function=embeddings,
    persist_directory=CHROMA_PATH,
)

# loading the PDF document
loader = PyPDFDirectoryLoader(DATA_PATH)
raw_documents = loader.load()

# splitting the document
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=100,
    length_function=len,
    is_separator_regex=False,
)

# creating the chunks
chunks = text_splitter.split_documents(raw_documents)

# creating unique ID's
uuids = [str(uuid4()) for _ in range(len(chunks))]

# adding chunks to vector store
vector_store.add_documents(documents=chunks, ids=uuids)