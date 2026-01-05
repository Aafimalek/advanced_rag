import os
import json
import uuid
import shutil
import pathlib
import tempfile
import time
import hashlib
import aiofiles
import warnings
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends, Security
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import uvicorn
from starlette.concurrency import run_in_threadpool
import asyncio

# Suppress the specific FutureWarning from unstructured's dependency
warnings.filterwarnings(
    "ignore",
    message="The `max_size` parameter is deprecated and will be removed in v4.26. Please specify in `size['longest_edge'] instead`.",
    category=FutureWarning,
    module="unstructured_inference.models.detectron2"
)

# --- Environment and API Keys ---
# Note: API keys are now provided by users via headers, not environment variables
load_dotenv()  # Keep for any other env vars

# --- LangChain Models ---
from langchain_ollama import OllamaEmbeddings
from langchain_groq import ChatGroq
from langchain_core.documents import Document

from langchain_text_splitters import RecursiveCharacterTextSplitter
# FAISS import removed - using Chroma instead
try:
    from langchain_chroma import Chroma
except ImportError:
    # Fallback to deprecated import
    from langchain_community.vectorstores import Chroma

# Simple MultiVectorRetriever implementation (if import fails)
try:
    from langchain_community.retrievers import MultiVectorRetriever
except (ImportError, AttributeError, ModuleNotFoundError):
    try:
        from langchain.retrievers.multi_vector import MultiVectorRetriever
    except (ImportError, AttributeError, ModuleNotFoundError):
        # Fallback: Simple implementation (not actually used in code, just for compatibility)
        class MultiVectorRetriever:
            """Simple MultiVectorRetriever implementation."""
            def __init__(self, vectorstore, docstore, id_key="doc_id"):
                self.vectorstore = vectorstore
                self.docstore = docstore
                self.id_key = id_key

# Simple file-based storage implementation (replacement for LocalFileStore)
class LocalFileStore:
    """Simple file-based storage that mimics langchain's LocalFileStore interface."""
    def __init__(self, base_path: str):
        self.base_path = pathlib.Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, key: str) -> pathlib.Path:
        """Get file path for a key, using hash to handle special characters."""
        # Use hash to create a safe filename
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        return self.base_path / f"{key_hash}.dat"
    
    def mset(self, key_value_pairs: List[tuple]):
        """Set multiple key-value pairs."""
        # Create a mapping file to store key -> hash mapping
        mapping_file = self.base_path / "_key_mapping.json"
        mapping = {}
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r') as f:
                    mapping = json.load(f)
            except:
                mapping = {}
        
        for key, value in key_value_pairs:
            file_path = self._get_file_path(key)
            mapping[key] = file_path.name
            with open(file_path, 'wb') as f:
                if isinstance(value, bytes):
                    f.write(value)
                else:
                    f.write(str(value).encode('utf-8'))
        
        # Save mapping
        with open(mapping_file, 'w') as f:
            json.dump(mapping, f)
    
    def mget(self, keys: List[str]) -> List[Optional[bytes]]:
        """Get multiple values by keys."""
        results = []
        for key in keys:
            file_path = self._get_file_path(key)
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    results.append(f.read())
            else:
                results.append(None)
        return results
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

# --- Document Processing ---
import pdfplumber
# Unstructured imports for DOCX and DOC support
try:
    from unstructured.partition.docx import partition_docx
    from unstructured.partition.doc import partition_doc
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    print("Warning: unstructured library not available. DOCX and DOC files will not be supported.")

# CSV and Excel support
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas library not available. CSV and Excel files will not be supported.")

# --- Constants ---
DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR = pathlib.Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)
DOCSTORE_DIR = pathlib.Path("docstore")
DOCSTORE_DIR.mkdir(exist_ok=True)
VEC_DIR = "chroma_data"  # Using Chroma for vector storage
COLLECTION_NAME = "documents"  # Chroma collection name
DOCUMENTS_MANIFEST_FILE = "documents.json"
EMBED_MODEL = "nomic-embed-text:latest"
LLM_MODEL = "llama-3.3-70b-versatile"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
CHAT_HISTORY_FILE = pathlib.Path("chat_history.json")
DOCUMENTS_FILE = pathlib.Path("documents.json")
DOCUMENT_CACHE_FILE = pathlib.Path("document_cache.json")  # Cache for document hashes

SYSTEM_PROMPT_TEMPLATE = (
    "You are a helpful and knowledgeable document assistant. Your task is to answer questions based on the context provided below.\n\n"
    "CRITICAL INSTRUCTIONS:\n"
    "1. READ THE ENTIRE CONTEXT CAREFULLY before answering\n"
    "2. Look for relevant information in ALL parts of the context (text and tables)\n"
    "3. If information is present in ANY form (direct statement, table, list, or implied), USE IT\n"
    "4. Synthesize information from multiple sections if needed\n"
    "5. Be thorough - check the entire context before saying information is not available\n\n"
    "FORMATTING RULES FOR CLEAN OUTPUT:\n"
    "1. Write in clear, natural language\n"
    "2. Use simple paragraphs with blank lines between them\n"
    "3. For lists with multiple items, format each on a new line starting with '* '\n"
    "4. When presenting scores or metrics, use format: '* **Score Value** on Dataset' (e.g., '* **28.4 BLEU** on WMT 2014 English-to-German')\n"
    "5. ALWAYS cite sources: add [Page X] after each claim or list item\n"
    "6. Keep paragraphs concise - 2-4 sentences max per paragraph\n"
    "7. Use clear section breaks (blank lines) between different topics\n\n"
    "RESPONSE LENGTH GUIDELINES:\n"
    "- Simple questions (what, who, when) → 2-3 sentences\n"
    "- 'Explain' or 'describe' → One detailed paragraph\n"
    "- 'In detail', 'comprehensive', 'thorough' → Multiple paragraphs with clear structure\n"
    "- List questions → Complete list with '* ' prefix for each item\n\n"
    "ONLY say 'I cannot find this information in the provided context' if you have:\n"
    "- Searched the ENTIRE context thoroughly\n"
    "- Checked all text sections and tables\n"
    "- Confirmed the information is genuinely not present in any form"
)
PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_TEMPLATE),
    ("human", "Query: {query}\n\nContext:\n{context}\n\nAnswer:"),
])

# --- Global Variables (Initialized on startup) ---
embeddings = None
llm = None
text_splitter = None
vectorstore = None
docstore = None
retriever = None


# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    global embeddings, llm, text_splitter, vectorstore, docstore, retriever
    
    print("--- Starting up application... ---")
    
    # Ensure manifest file exists
    if not os.path.exists(DOCUMENTS_MANIFEST_FILE):
        with open(DOCUMENTS_MANIFEST_FILE, "w") as f:
            json.dump([], f)

    # Models will be initialized per-request with user-provided API keys
    # We keep these as None for now
    embeddings = None
    llm = None
    
    # Initialize text splitter
    # Reduced chunk size to avoid embedding context length issues with nomic-embed-text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,  # Reduced to avoid embedding context length errors
        chunk_overlap=400,  # Higher overlap ensures no information is lost at boundaries
        separators=["\n\n", "\n", ". ", "! ", "? ", ", ", " "]
    )
    
    # Initialize Chroma directory at startup
    if not os.path.exists(VEC_DIR):
        os.makedirs(VEC_DIR)
    vectorstore = None
    print("✔ Chroma vector store directory ready.")
        
    # Create chat history file if it doesn't exist
    if not CHAT_HISTORY_FILE.exists():
        with open(CHAT_HISTORY_FILE, 'w') as f:
            json.dump({}, f)
        print(f"✔ Created new chat history file at {CHAT_HISTORY_FILE}")

    docstore = LocalFileStore(str(DOCSTORE_DIR))
    retriever = None  # Will be initialized per-request
    print("✔ Document store initialized.")
    
    yield
    
    # Shutdown logic can be placed here
    print("--- Shutting down application... ---")


# --- FastAPI App ---
app = FastAPI(lifespan=lifespan)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    query: str
    k: int = 20  # Increased to ensure we get enough text chunks along with tables

class NewChatRequest(BaseModel):
    document_id: str

# --- API Key Authentication ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: Optional[str] = Security(api_key_header)):
    """Dependency to get the API key from the header or return None.
    For Groq LLM, we'll use this if provided, otherwise fall back to GROQ_API_KEY from .env.
    For Ollama embeddings, no API key is needed."""
    return api_key

# --- API Key Helper Functions ---
def get_embeddings_model(api_key: str = None):
    """Creates an embeddings model using Ollama (no API key needed for local Ollama)."""
    return OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
    )

def get_llm_model(api_key: str = None):
    """Creates an LLM model using Groq API."""
    # Get Groq API key from environment if not provided
    groq_api_key = api_key or os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is required. Please set it in your .env file or provide it via API key header.")
    
    return ChatGroq(
        model=LLM_MODEL,
        temperature=0.3,
        groq_api_key=groq_api_key,
        max_retries=2,
    )

def get_vectorstore(api_key: str = None):
    """Loads or creates Chroma vectorstore with Ollama embeddings."""
    embeddings_model = get_embeddings_model(api_key)
    
    # Create or load Chroma vectorstore (persists to disk automatically)
    vectorstore = Chroma(
        persist_directory=VEC_DIR,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings_model,
    )
    
    return vectorstore

def get_retriever(api_key: str = None):
    """Creates a retriever with Ollama embeddings."""
    vs = get_vectorstore(api_key)
    return MultiVectorRetriever(
        vectorstore=vs,
        docstore=docstore,
        id_key="doc_id",
    )

# --- Helper Functions for Persistence ---
async def read_json_async(path: pathlib.Path) -> Any:
    async with aiofiles.open(path, 'r') as f:
        return json.loads(await f.read())

async def write_json_async(path: pathlib.Path, data: Any):
    async with aiofiles.open(path, 'w') as f:
        await f.write(json.dumps(data, indent=2))

async def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    docs = await read_json_async(DOCUMENTS_FILE)
    for doc in docs:
        if doc.get("id") == doc_id:
            return doc
    return None

# --- Document Caching Functions ---
def compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of a file for caching/deduplication."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

async def get_cached_document(file_hash: str) -> Optional[Dict[str, Any]]:
    """Check if a document with this hash has already been processed."""
    try:
        cache = await read_json_async(DOCUMENT_CACHE_FILE)
        return cache.get(file_hash)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

async def cache_document(file_hash: str, doc_id: str, filename: str, stats: Dict[str, int]):
    """Store document metadata in cache."""
    try:
        cache = await read_json_async(DOCUMENT_CACHE_FILE)
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}
    
    cache[file_hash] = {
        "doc_id": doc_id,
        "filename": filename,
        "stats": stats,
        "cached_at": datetime.now().isoformat()
    }
    
    await write_json_async(DOCUMENT_CACHE_FILE, cache)

# --- Document Processing and Chunking Logic (from notebook, with improvements) ---
def load_file(path: str) -> List[Dict[str, Any]]:
    """Loads a document (PDF, DOCX, DOC, CSV, or Excel) and extracts text and tables."""
    path = str(path)
    suffix = pathlib.Path(path).suffix.lower()
    elements = []
    
    if suffix == ".pdf":
        # Use pdfplumber for PDF files
        with pdfplumber.open(path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract text
                text = page.extract_text()
                if text and text.strip():
                    elements.append({
                        'type': 'text',
                        'text': text,
                        'page': page_num,
                        'category': 'Text'
                    })
                
                # Extract tables
                tables = page.extract_tables()
                for table_idx, table in enumerate(tables):
                    if table:
                        # Convert table to HTML format
                        table_html = "<table>"
                        for row in table:
                            table_html += "<tr>"
                            for cell in row:
                                cell_text = str(cell) if cell else ""
                                table_html += f"<td>{cell_text}</td>"
                            table_html += "</tr>"
                        table_html += "</table>"
                        
                        # Convert table to text format
                        table_text = "\n".join(["\t".join([str(cell) if cell else "" for cell in row]) for row in table])
                        
                        elements.append({
                            'type': 'table',
                            'text': table_text,
                            'html': table_html,
                            'page': page_num,
                            'category': 'Table',
                            'table_index': table_idx
                        })
        return elements
    
    elif suffix == ".docx":
        # Use unstructured for DOCX files
        if not UNSTRUCTURED_AVAILABLE:
            raise ValueError("DOCX support requires the 'unstructured' library. Please install it: pip install unstructured[docx]")
        
        docx_elements = partition_docx(filename=path)
        page_num = 1  # DOCX doesn't have pages, but we'll use 1 for consistency
        
        for idx, elem in enumerate(docx_elements):
            # Get element type and text
            elem_type = getattr(elem, 'category', 'NarrativeText')
            elem_text = getattr(elem, 'text', str(elem))
            
            # Check if it's a table (by category or metadata)
            is_table = (elem_type == 'Table' or 
                       (hasattr(elem, 'metadata') and elem.metadata and 
                        getattr(elem.metadata, 'text_as_html', None)))
            
            if is_table:
                # Extract table HTML if available
                table_html = ''
                if hasattr(elem, 'metadata') and elem.metadata:
                    table_html = getattr(elem.metadata, 'text_as_html', '')
                
                table_text = elem_text
                
                if not table_html and table_text:
                    # Create a simple HTML table from text
                    table_html = f"<table><tr><td>{table_text}</td></tr></table>"
                
                elements.append({
                    'type': 'table',
                    'text': table_text,
                    'html': table_html,
                    'page': page_num,
                    'category': 'Table',
                    'table_index': idx
                })
            else:
                # Regular text element
                if elem_text and elem_text.strip():
                    elements.append({
                        'type': 'text',
                        'text': elem_text,
                        'page': page_num,
                        'category': 'Text'
                    })
        return elements
    
    elif suffix == ".doc":
        # Use unstructured for older DOC files
        if not UNSTRUCTURED_AVAILABLE:
            raise ValueError("DOC support requires the 'unstructured' library. Please install it: pip install unstructured[doc]")
        
        doc_elements = partition_doc(filename=path)
        page_num = 1  # DOC doesn't have pages, but we'll use 1 for consistency
        
        for idx, elem in enumerate(doc_elements):
            # Get element type and text
            elem_type = getattr(elem, 'category', 'NarrativeText')
            elem_text = getattr(elem, 'text', str(elem))
            
            # Check if it's a table (by category or metadata)
            is_table = (elem_type == 'Table' or 
                       (hasattr(elem, 'metadata') and elem.metadata and 
                        getattr(elem.metadata, 'text_as_html', None)))
            
            if is_table:
                # Extract table HTML if available
                table_html = ''
                if hasattr(elem, 'metadata') and elem.metadata:
                    table_html = getattr(elem.metadata, 'text_as_html', '')
                
                table_text = elem_text
                
                if not table_html and table_text:
                    # Create a simple HTML table from text
                    table_html = f"<table><tr><td>{table_text}</td></tr></table>"
                
                elements.append({
                    'type': 'table',
                    'text': table_text,
                    'html': table_html,
                    'page': page_num,
                    'category': 'Table',
                    'table_index': idx
                })
            else:
                # Regular text element
                if elem_text and elem_text.strip():
                    elements.append({
                        'type': 'text',
                        'text': elem_text,
                        'page': page_num,
                        'category': 'Text'
                    })
        return elements
    
    elif suffix == ".csv":
        # Use pandas for CSV files
        if not PANDAS_AVAILABLE:
            raise ValueError("CSV support requires the 'pandas' library. Please install it: pip install pandas")
        
        df = pd.read_csv(path)
        
        # Convert entire CSV to a table
        table_html = "<table>"
        # Add header row
        table_html += "<tr>"
        for col in df.columns:
            table_html += f"<th>{col}</th>"
        table_html += "</tr>"
        
        # Add data rows
        for _, row in df.iterrows():
            table_html += "<tr>"
            for val in row:
                table_html += f"<td>{val}</td>"
            table_html += "</tr>"
        table_html += "</table>"
        
        # Convert to text format
        table_text = df.to_string(index=False)
        
        elements.append({
            'type': 'table',
            'text': table_text,
            'html': table_html,
            'page': 1,
            'category': 'Table',
            'table_index': 0
        })
        return elements
    
    elif suffix in [".xlsx", ".xls"]:
        # Use pandas for Excel files
        if not PANDAS_AVAILABLE:
            raise ValueError("Excel support requires the 'pandas' library. Please install it: pip install pandas openpyxl")
        
        # Read all sheets from Excel file
        excel_file = pd.ExcelFile(path)
        table_idx = 0
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet_name)
            
            # Convert sheet to a table
            table_html = f"<table><caption>Sheet: {sheet_name}</caption>"
            # Add header row
            table_html += "<tr>"
            for col in df.columns:
                table_html += f"<th>{col}</th>"
            table_html += "</tr>"
            
            # Add data rows
            for _, row in df.iterrows():
                table_html += "<tr>"
                for val in row:
                    table_html += f"<td>{val}</td>"
                table_html += "</tr>"
            table_html += "</table>"
            
            # Convert to text format
            table_text = f"Sheet: {sheet_name}\n" + df.to_string(index=False)
            
            elements.append({
                'type': 'table',
                'text': table_text,
                'html': table_html,
                'page': 1,  # Excel sheets don't have pages, use 1
                'category': 'Table',
                'table_index': table_idx
            })
            table_idx += 1
        
        return elements
    
    else:
        supported_formats = [".pdf"]
        if UNSTRUCTURED_AVAILABLE:
            supported_formats.extend([".docx", ".doc"])
        if PANDAS_AVAILABLE:
            supported_formats.extend([".csv", ".xlsx", ".xls"])
        raise ValueError(f"Unsupported file type: {suffix}. Supported formats: {', '.join(supported_formats)}")


async def summarize_table_async(table_html: str, api_key: str, table_text: str = "") -> str:
    """Summarizes table content from HTML representation with retry logic for rate limits."""
    max_retries = 3
    retry_delay = 2  # Start with 2 seconds
    
    for attempt in range(max_retries):
        try:
            llm_text = get_llm_model(api_key) # Initialize model with API key
            prompt = f"""Summarize the key information in this table concisely. Focus on main data points, trends, and relationships.

Table HTML:
{table_html[:2000]}

Table Text:
{table_text[:1000]}

Provide a clear, structured summary."""
            message = HumanMessage(content=prompt)
            response = await llm_text.ainvoke([message])
            return response.content
        except Exception as e:
            error_msg = str(e)
            # Check if it's a rate limit error
            if "429" in error_msg or "rate limit" in error_msg.lower() or "rate_limit" in error_msg.lower():
                if attempt < max_retries - 1:
                    # Extract wait time from error if available, otherwise use exponential backoff
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                    print(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"Error summarizing table after {max_retries} retries: {e}")
                    return f"Table content: {table_text[:500]}"
            else:
                # For non-rate-limit errors, return immediately
                print(f"Error summarizing table: {e}")
                return f"Table content: {table_text[:500]}"
    
    # Fallback if all retries failed
    return f"Table content: {table_text[:500]}"

async def summarize_text_async(text_chunk: str, page_num: int = None, chunk_idx: int = 0) -> str:
    """Returns text chunk as-is for better keyword matching in vector search.
    Adds context prefix for first chunks to help with broad queries."""
    
    # For the very first chunk, add document context to help with broad queries
    if page_num == 1 and chunk_idx == 0:
        # Add a brief contextual prefix to help match queries like "what is this paper about"
        prefix = "This document/research paper discusses: "
        return prefix + text_chunk
    
    # For all other chunks, return as-is for exact keyword matching
    return text_chunk

async def build_multimodal_elements_streaming(file_path: str, api_key: str):
    """Async generator to extract and process elements using pdfplumber, yielding status updates."""
    
    file_suffix = pathlib.Path(file_path).suffix.lower()
    if file_suffix == ".pdf":
        yield {"step": "extracting", "message": "Extracting text and tables from PDF with pdfplumber..."}
    elif file_suffix == ".docx":
        yield {"step": "extracting", "message": "Extracting text and tables from DOCX with unstructured..."}
    elif file_suffix == ".doc":
        yield {"step": "extracting", "message": "Extracting text and tables from DOC with unstructured..."}
    elif file_suffix == ".csv":
        yield {"step": "extracting", "message": "Extracting data from CSV file..."}
    elif file_suffix in [".xlsx", ".xls"]:
        yield {"step": "extracting", "message": "Extracting data from Excel file..."}
    else:
        yield {"step": "extracting", "message": f"Extracting content from {file_suffix} file..."}
    elements = await run_in_threadpool(load_file, file_path)

    # Separate elements by type (from pdfplumber output)
    table_elements = [e for e in elements if e.get('type') == 'table']
    text_elements = [e for e in elements if e.get('type') == 'text']

    yield {"step": "extracting", "message": f"Found {len(text_elements)} text blocks and {len(table_elements)} tables."}

    # --- Table Processing ---
    table_elements_to_process = []
    for elem in table_elements:
        table_text = elem.get('text', '')
        table_html = elem.get('html', '')
        if not table_html and table_text:
            table_html = f"<table><tr><td>{table_text}</td></tr></table>"
        table_elements_to_process.append({
            "doc_id": str(uuid.uuid4()), 
            "type": "table", 
            "original": table_html or table_text,
            "source": str(file_path), 
            "text_content": table_text, 
            "html_content": table_html,
            "page": elem.get('page')
        })

    # --- Text Processing with Page Numbers ---
    # Group text elements by page to preserve page information
    text_by_page = {}
    for e in text_elements:
        text_content = e.get('text', '')
        if text_content:
            page_num = e.get('page')
            if page_num not in text_by_page:
                text_by_page[page_num] = []
            text_by_page[page_num].append(text_content)
    
    text_elements_to_process = []
    if text_by_page:
        yield {"step": "chunking", "message": "Splitting text into chunks with page tracking..."}
        
        # Process each page's text separately to maintain page numbers
        for page_num, texts in text_by_page.items():
            page_text = "\n".join(texts)
            chunks = await run_in_threadpool(text_splitter.split_text, page_text)
            
            for i, chunk in enumerate(chunks):
                text_elements_to_process.append({
                    "doc_id": str(uuid.uuid4()), 
                    "type": "text", 
                    "original": chunk,
                    "source": str(file_path), 
                    "page": page_num,
                    "chunk_index": i
                })
        
        yield {"step": "chunking", "message": f"Created {len(text_elements_to_process)} text chunks across {len(text_by_page)} pages."}

    # --- Concurrent Summarization with Rate Limiting ---
    yield {"step": "summarizing", "message": "Starting concurrent summarization of tables..."}
    
    # Create a semaphore to limit concurrent API calls (avoid rate limits)
    # Reduced to 3 to avoid Groq rate limits (12000 TPM limit)
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
    
    async def rate_limited_task(task_coro):
        """Wrapper to rate-limit task execution with delay between requests"""
        async with semaphore:
            # Add small delay between requests to avoid rate limits
            await asyncio.sleep(0.5)  # 500ms delay between requests
            return await task_coro
    
    # Only summarize tables with LLM
    # Text chunks are used as-is for better keyword matching (much faster!)
    table_tasks = [rate_limited_task(summarize_table_async(e["html_content"], api_key, e["text_content"])) for e in table_elements_to_process]
    
    # For text, only summarize the first chunk for document context
    # All other text chunks use raw text (no LLM call needed - massive speedup!)
    text_summaries = []
    for e in text_elements_to_process:
        if e.get("page") == 1 and e.get("chunk_index") == 0:
            # First chunk gets a contextual prefix
            text_summaries.append(rate_limited_task(summarize_text_async(e["original"], e.get("page"), e.get("chunk_index", 0))))
        else:
            # All other chunks: just use the raw text (no API call!)
            text_summaries.append(asyncio.create_task(asyncio.sleep(0, result=e["original"])))
    
    all_tasks = table_tasks + text_summaries
    total_tasks = len(table_tasks) + sum(1 for e in text_elements_to_process if e.get("page") == 1 and e.get("chunk_index") == 0)
    skipped_text = len(text_elements_to_process) - sum(1 for e in text_elements_to_process if e.get("page") == 1 and e.get("chunk_index") == 0)
    
    if skipped_text > 0:
        yield {"step": "summarizing", "message": f"Skipping LLM for {skipped_text} text chunks (using raw text for better keyword matching)..."}
    
    # Use asyncio.gather for better parallelism
    completed_count = 0
    summaries = []
    
    # Process in smaller batches to avoid rate limits
    batch_size = 3  # Reduced batch size to avoid rate limits
    for i in range(0, len(all_tasks), batch_size):
        batch = all_tasks[i:i + batch_size]
        batch_results = await asyncio.gather(*batch, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                print(f"Warning: Summarization failed: {result}")
                summaries.append("Content could not be summarized.")
            else:
                summaries.append(result)
        
        completed_count += len(batch)
        yield {"step": "summarizing", "message": f"Summarized {completed_count}/{total_tasks} elements..."}
        
        # Add delay between batches to avoid rate limits
        if i + batch_size < len(all_tasks):
            await asyncio.sleep(1)  # 1 second delay between batches

    # Assign summaries back to elements in order
    all_processed_elements = []
    summary_idx = 0
        
    for elem in table_elements_to_process:
        elem["summary"] = summaries[summary_idx]
        all_processed_elements.append(elem)
        summary_idx += 1
        
    for elem in text_elements_to_process:
        elem["summary"] = summaries[summary_idx]
        all_processed_elements.append(elem)
        summary_idx += 1
    
    # Yield final elements
    for elem in all_processed_elements:
        yield {"type": "element", "element": elem}

async def index_file_streaming(fp: str, doc_id: str, original_filename: str, api_key: str):
    """Async generator to index a file and yield status updates."""
    # Check cache first to avoid reprocessing duplicates
    yield {"step": "checking", "message": "Checking if document has been processed before..."}
    
    file_hash = await run_in_threadpool(compute_file_hash, fp)
    cached_doc = await get_cached_document(file_hash)
    
    if cached_doc:
        yield {"step": "cache_hit", "message": f"Document already processed! Using cached version (saved ~{cached_doc['stats'].get('texts', 0) + cached_doc['stats'].get('tables', 0)} API calls)..."}
        
        # Return cached document info instead of reprocessing
        # Still create a new chat for this "upload"
        try:
            documents = await read_json_async(DOCUMENTS_FILE)
        except (FileNotFoundError, json.JSONDecodeError):
            documents = []
        
        # Find the original document
        original_doc = next((d for d in documents if d.get("id") == cached_doc["doc_id"]), None)
        if original_doc:
            # Create new chat for cached document
            chat_history = await read_json_async(CHAT_HISTORY_FILE)
            chat_id = str(uuid.uuid4())
            new_chat = {
                "id": chat_id,
                "document_id": cached_doc["doc_id"],
                "created_at": datetime.now().isoformat(),
                "title": original_filename,
                "messages": []
            }
            chat_history[chat_id] = new_chat
            await write_json_async(CHAT_HISTORY_FILE, chat_history)
            
            chat_with_document = {**new_chat, "document": original_doc}
            yield {"step": "complete", "message": "Using cached document!", "document": original_doc, "chat": chat_with_document}
            return
    
    # Get vectorstore for this request with user's API key
    vectorstore_user = get_vectorstore(api_key)
    
    yield {"step": "extraction", "message": f"Processing file: {original_filename}"}
    
    elements_generator = build_multimodal_elements_streaming(fp, api_key)
    all_elements = {"tables": [], "texts": []}

    async for status in elements_generator:
        if status.get("type") == "element":
            elem = status["element"]
            all_elements[f"{elem['type']}s"].append(elem)
        else:
            yield status

    yield {"step": "indexing", "message": "Storing summaries and original documents..."}
    
    total_elements = sum(len(v) for v in all_elements.values())
    
    # Batch collect all docstore entries and summary documents
    docstore_entries = []
    all_summary_docs = []
    
    # Maximum text length for embeddings (nomic-embed-text has ~8192 token limit, ~32000 chars)
    MAX_EMBEDDING_LENGTH = 30000  # Safe limit for embeddings
    
    for elem_type, elems in all_elements.items():
        for elem in elems:
            # Prepare docstore entry
            docstore_entries.append((elem["doc_id"], json.dumps(elem).encode("utf-8")))
            
            # Prepare summary document for vectorstore
            # Truncate summary if too long to avoid embedding context length errors
            summary_text = elem["summary"]
            if len(summary_text) > MAX_EMBEDDING_LENGTH:
                summary_text = summary_text[:MAX_EMBEDDING_LENGTH] + "... [truncated]"
                print(f"Warning: Truncated summary for {elem['doc_id']} (was {len(elem['summary'])} chars)")
            
            metadata = {"doc_id": elem["doc_id"], "type": elem["type"], "source": elem["source"]}
            if 'page' in elem: metadata['page'] = elem['page']
            if 'chunk_index' in elem: metadata['chunk'] = elem['chunk_index']
            
            summary_doc = Document(page_content=summary_text, metadata=metadata)
            all_summary_docs.append(summary_doc)
    
    # Batch operations for significant speedup
    yield {"step": "indexing", "message": f"Storing {total_elements} elements in docstore (batch)..."}
    await run_in_threadpool(docstore.mset, docstore_entries)
    
    yield {"step": "indexing", "message": f"Adding {total_elements} documents to vector index (batch)..."}
    try:
        # Add documents in smaller batches to avoid embedding context length errors
        batch_size = 50  # Process embeddings in smaller batches
        for i in range(0, len(all_summary_docs), batch_size):
            batch = all_summary_docs[i:i + batch_size]
            await run_in_threadpool(vectorstore_user.add_documents, batch)
            if i + batch_size < len(all_summary_docs):
                await asyncio.sleep(0.1)  # Small delay between batches
    except Exception as e:
        error_msg = str(e)
        if "context length" in error_msg.lower() or "exceeds" in error_msg.lower():
            yield {"step": "error", "message": f"Some text chunks are too long for embedding. Please try with a document that has shorter text sections."}
            raise
        else:
            raise

    # Chroma auto-persists, no explicit save needed
    yield {"step": "saving", "message": "Vector index persisted automatically (Chroma)..."}
    
    # Update manifest
    yield {"step": "manifest", "message": "Updating document manifest..."}
    new_document_record = None
    try:
        documents = await read_json_async(DOCUMENTS_FILE)
    except (FileNotFoundError, json.JSONDecodeError):
        documents = []
        
    existing_doc_index = next((i for i, doc in enumerate(documents) if doc["name"] == original_filename), -1)
        
    stats = { "tables": len(all_elements["tables"]), "texts": len(all_elements["texts"]) }
        
    if existing_doc_index != -1:
        documents[existing_doc_index]["uploadedAt"] = datetime.now().isoformat()
        documents[existing_doc_index]["stats"] = stats
        documents[existing_doc_index]["preview"] = f"Re-indexed with {stats['texts']} texts, {stats['tables']} tables."
        new_document_record = documents[existing_doc_index]
    else:
        new_document_record = {
            "id": doc_id,
            "name": original_filename,
            "path": fp,
            "uploadedAt": datetime.now().isoformat(),
            "preview": f"Indexed with {stats['texts']} texts, {stats['tables']} tables.",
            "stats": stats
        }
        documents.append(new_document_record)
        
    await write_json_async(DOCUMENTS_FILE, documents)
    
    # Cache the document hash to avoid reprocessing duplicates
    yield {"step": "caching", "message": "Caching document fingerprint..."}
    await cache_document(file_hash, doc_id, original_filename, stats)

    # After indexing, create a new chat for this document
    chat_history = await read_json_async(CHAT_HISTORY_FILE)
    chat_id = str(uuid.uuid4())
    new_chat = {
        "id": chat_id,
        "document_id": doc_id,
        "created_at": datetime.now().isoformat(),
        "title": original_filename, # Title of chat is the filename
        "messages": []
    }
    chat_history[chat_id] = new_chat
    await write_json_async(CHAT_HISTORY_FILE, chat_history)
    
    # Send the complete message with both document and chat (include document in response only)
    chat_with_document = {**new_chat, "document": new_document_record}
    yield {"step": "complete", "message": "Processing complete!", "document": new_document_record, "chat": chat_with_document}


async def query_rag(query: str, k: int = 6):
    """Queries the RAG pipeline using multi-vector retrieval."""
    print(f"\n🔍 Query: {query}")
    
    # 1. Retrieve summaries from vectorstore
    summary_docs = await run_in_threadpool(vectorstore.similarity_search, query, k=k)
    
    if not summary_docs:
        print("  ⚠️  No relevant documents found.")
        return {"answer": "No relevant documents found for your query.", "chunks": [], "element_types": {}}
    
    print(f"  📋 Retrieved {len(summary_docs)} relevant summaries")
    
    # 2. Extract doc_ids from retrieved summaries
    doc_ids = [doc.metadata.get("doc_id") for doc in summary_docs if "doc_id" in doc.metadata]
    
    if not doc_ids:
        print("  ⚠️  No doc_ids found in retrieved summaries.")
        return {"answer": "No relevant documents found for your query.", "chunks": summary_docs, "element_types": {}}
    
    # 3. Fetch original elements from docstore
    originals_raw = await run_in_threadpool(docstore.mget, doc_ids)
    originals = [json.loads(o.decode("utf-8")) for o in originals_raw if o is not None]
    
    print(f"  📦 Fetched {len(originals)} original elements from docstore")
    
    # 4. Separate by type
    tables = []
    texts = []
    
    for elem in originals:
        if isinstance(elem, dict):
            elem_type = elem.get("type", "")
            if elem_type == "table":
                tables.append(elem["original"])
            elif elem_type == "text":
                texts.append(elem["original"])
    
    element_counts = {
        "tables": len(tables),
        "texts": len(texts)
    }
    
    print(f"  📊 Element breakdown: {element_counts['tables']} tables, {element_counts['texts']} text chunks")
    
    # 5. Build context from texts and tables
    context_parts = []
    if texts:
        context_parts.append("=== TEXT CONTEXT ===\n" + "\n\n".join(texts))
    if tables:
        context_parts.append("=== TABLE CONTEXT ===\n" + "\n\n".join(tables))
    
    context = "\n\n".join(context_parts)
    
    # 6. Invoke LLM with text context
    messages = [SystemMessage(content=SYSTEM_PROMPT_TEMPLATE)]
    human_text = f"Query: {query}\n\nContext:\n{context}\n\nAnswer:"
    messages.append(HumanMessage(content=human_text))
    
    print(f"  🤖 Generating answer with LLM...")
    response = await llm.ainvoke(messages)
    
    print(f"  ✅ Answer generated successfully\n")
    
    return {
        "answer": response.content,
        "chunks": summary_docs,
        "element_types": element_counts
    }

async def answer_generator(chat_id: str, query: str, k: int, api_key: str):
    """Generator that finds context, streams the LLM response, and saves history."""
    
    # Get models for this request with user's API key
    vectorstore_user = get_vectorstore(api_key)
    llm_user = get_llm_model(api_key)
    
    # 1. Retrieve context (non-streaming part, adapted from query_rag)
    print(f"\n🔍 Query for streaming: {query}")
    # Limit k to avoid retrieving too many chunks (max 10 to prevent token limit overflow)
    # With TPM limit of 12k tokens, we need to be conservative
    k = min(k, 10)
    summary_docs = await run_in_threadpool(vectorstore_user.similarity_search, query, k=k)
    print(f"  📦 Retrieved {len(summary_docs)} document chunks from vector store")
    chunks_for_json = [{"page_content": doc.page_content, "metadata": doc.metadata} for doc in summary_docs]
    
    # First, yield the context so the frontend can show sources immediately.
    yield f"data: {json.dumps({'type': 'context', 'chunks': chunks_for_json})}\n\n"
    
    # Fetch original elements and build multimodal context
    doc_ids = [doc.metadata.get("doc_id") for doc in summary_docs if "doc_id" in doc.metadata]
    originals_raw = await run_in_threadpool(docstore.mget, doc_ids)
    originals = [json.loads(o.decode("utf-8")) for o in originals_raw if o is not None]
    
    tables, texts = [], []
    for elem in originals:
        if isinstance(elem, dict):
            elem_type = elem.get("type")
            page_num = elem.get("page", "Unknown")
            
            if elem_type == "table":
                table_content = f"[From Page {page_num}]\n{elem['original']}"
                tables.append(table_content)
            elif elem_type == "text":
                text_content = f"[From Page {page_num}]\n{elem['original']}"
                texts.append(text_content)
    
    # Build structured context with clear sections
    context_parts = []
    
    # Limit individual chunk sizes to prevent huge tables from breaking context
    # Reduced to stay within token limits (TPM: 12k tokens ≈ 48k chars total)
    MAX_CHUNK_LENGTH = 20000  # Max 20k chars per chunk (~5k tokens)
    
    if texts:
        truncated_texts = []
        for text in texts:
            if len(text) > MAX_CHUNK_LENGTH:
                truncated_texts.append(text[:MAX_CHUNK_LENGTH] + "\n[Text truncated due to length]")
            else:
                truncated_texts.append(text)
        context_parts.append("=== DOCUMENT TEXT ===")
        context_parts.append("\n\n".join(truncated_texts))
    
    if tables:
        truncated_tables = []
        for table in tables:
            if len(table) > MAX_CHUNK_LENGTH:
                truncated_tables.append(table[:MAX_CHUNK_LENGTH] + "\n[Table truncated due to length]")
            else:
                truncated_tables.append(table)
        context_parts.append("\n\n=== TABLES AND STRUCTURED DATA ===")
        context_parts.append("\n\n".join(truncated_tables))
    
    context = "\n\n".join(context_parts) if context_parts else "No context available."
    
    # Log context statistics
    print(f"  📊 Context built: {len(texts)} text chunks, {len(tables)} tables")
    print(f"  📏 Total context length: {len(context)} characters")
    
    # Limit context length to avoid exceeding LLM context window
    # Groq models have TPM (tokens per minute) limits: 12,000 tokens
    # Rough estimate: 1 token ≈ 4 characters, so 12k tokens ≈ 48k characters
    # But we need to account for system prompt (~500 tokens) and query (~100 tokens)
    # So safe limit is ~11k tokens ≈ 44k characters
    # Using 40k characters as a conservative limit to stay well under TPM limits
    MAX_CONTEXT_LENGTH = 40000  # characters (~10k tokens, leaving room for prompt and query)
    
    if len(context) > MAX_CONTEXT_LENGTH:
        print(f"  ⚠️  Context too long ({len(context)} chars), truncating to {MAX_CONTEXT_LENGTH} chars...")
        # Truncate intelligently - try to keep complete chunks
        truncated_context = context[:MAX_CONTEXT_LENGTH]
        # Try to cut at a reasonable boundary (newline or paragraph break)
        last_newline = truncated_context.rfind('\n\n')
        if last_newline > MAX_CONTEXT_LENGTH * 0.9:  # If we can find a break point near the limit
            truncated_context = truncated_context[:last_newline]
        truncated_context += f"\n\n[Context truncated - showing first {MAX_CONTEXT_LENGTH} characters of {len(context)} total]"
        context = truncated_context
        print(f"  📏 Truncated context length: {len(context)} characters")
    
    # Build messages for the LLM
    messages = [SystemMessage(content=SYSTEM_PROMPT_TEMPLATE)]
    human_text = f"Query: {query}\n\nContext:\n{context}\n\nAnswer:"
    
    # Check total message length (system prompt + human message)
    # Total should not exceed ~45k chars to stay within 12k token TPM limit
    MAX_TOTAL_LENGTH = 45000  # characters (~11k tokens, leaving room for system prompt)
    total_length = len(SYSTEM_PROMPT_TEMPLATE) + len(human_text)
    if total_length > MAX_TOTAL_LENGTH:
        print(f"  ⚠️  Total message length ({total_length} chars) exceeds safe limit ({MAX_TOTAL_LENGTH} chars), further truncating...")
        # Further truncate the context
        available_space = MAX_TOTAL_LENGTH - len(SYSTEM_PROMPT_TEMPLATE) - len(query) - 200  # Reserve space for query and formatting
        if len(context) > available_space:
            context = context[:available_space] + "\n\n[Context further truncated due to token limits]"
            human_text = f"Query: {query}\n\nContext:\n{context}\n\nAnswer:"
            print(f"  📏 Final context length after truncation: {len(context)} characters")
    
    messages.append(HumanMessage(content=human_text))

    # 2. Stream the LLM response
    full_answer = ""
    print(f"  🤖 Streaming answer with multimodal LLM...")
    try:
        async for chunk in llm_user.astream(messages):
            content = chunk.content
            if content:
                full_answer += content
                yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"
    except Exception as e:
        error_msg = str(e)
        print(f"  ❌ Error during streaming: {error_msg}")
        
        # Handle specific API errors
        if "rate limit" in error_msg.lower() or "429" in error_msg or "413" in error_msg:
            if "tokens per day" in error_msg.lower() or "TPD" in error_msg:
                error_response = "I apologize, but the daily API rate limit has been reached. Please try again tomorrow or upgrade your API plan."
            elif "request too large" in error_msg.lower() or "TPM" in error_msg or "tokens per minute" in error_msg.lower():
                error_response = "I apologize, but the document context is too large for the API rate limit. The document contains too much data. Please try asking a more specific question that targets a smaller portion of the document, or try again in a moment when the rate limit resets."
            else:
                error_response = "I apologize, but the API rate limit was exceeded. Please try again in a moment."
        elif "context length" in error_msg.lower() or "context_length_exceeded" in error_msg.lower() or "reduce the length" in error_msg.lower():
            error_response = "I apologize, but the document context is too large to process. Please try asking a more specific question or upload a smaller document."
        elif "API key" in error_msg.lower() or "authentication" in error_msg.lower():
            error_response = "I apologize, but there was an authentication error. Please check your API key."
        else:
            error_response = f"I encountered an error while processing your request. Please try again or rephrase your question."
        
        full_answer = error_response
        yield f"data: {json.dumps({'type': 'chunk', 'content': error_response})}\n\n"
            
    print(f"  ✅ Stream finished.")
    
    # Fallback if no answer was generated
    if not full_answer or full_answer.strip() == "":
        full_answer = "I apologize, but I couldn't generate a response. Please try rephrasing your question or provide more context."
        yield f"data: {json.dumps({'type': 'chunk', 'content': full_answer})}\n\n"

    # 3. After streaming, save the full conversation history.
    bot_message = {
        "sender": "bot",
        "text": full_answer,
        "chunks": chunks_for_json,
    }
    
    chat_history = await read_json_async(CHAT_HISTORY_FILE)
    # Correctly append the message to the specific chat's message list
    if chat_id in chat_history and 'messages' in chat_history[chat_id]:
        chat_history[chat_id]['messages'].append(bot_message)
    await write_json_async(CHAT_HISTORY_FILE, chat_history)
    print(f"  💾 Saved full response to chat {chat_id}")

    # 4. Yield a final message to signal the end
    yield f"data: {json.dumps({'type': 'end'})}\n\n"


# --- FastAPI Lifecycle Events ---


# --- API Endpoints ---
async def upload_generator(tmp_path: str, doc_id: str, filename: str, api_key: str):
    """Generator that processes the file and yields status updates."""
    try:
        yield f"data: {json.dumps({'step': 'setup', 'message': f'Starting processing for {filename}'})}\n\n"

        # The index_file_streaming function already handles the rest, including the final 'saving' step with all data
        async for status in index_file_streaming(tmp_path, doc_id, filename, api_key):
            yield f"data: {json.dumps(status)}\n\n"

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Error during streaming upload: {error_details}")
        yield f"data: {json.dumps({'step': 'error', 'message': str(e)})}\n\n"
    # The temp file is now a permanent file, so we don't remove it
    # finally:
    #     await run_in_threadpool(os.remove, tmp_path)

# This endpoint does not need API key validation as it's a simple health check / info endpoint
@app.get("/")
def read_root():
    return {"status": "DocChat AI is running"}


# --- API Key Validation Endpoint ---
@app.post("/validate-api-key")
async def validate_api_key_endpoint(api_key: Optional[str] = Depends(get_api_key)):
    """Validates the provided API key by attempting to create a simple LLM model and test Ollama connection."""
    try:
        # Test Ollama connection
        test_embeddings = get_embeddings_model(api_key)
        await run_in_threadpool(test_embeddings.embed_query, "test")
        
        # Test Groq API key (will use .env if api_key is None)
        test_llm = get_llm_model(api_key)
        # Simple test - just verify the model can be created
        # We don't need to actually invoke it for validation
        
        return {"valid": True, "message": "API key is valid and Ollama connection is working"}
    except Exception as e:
        error_msg = str(e)
        if "GROQ_API_KEY" in error_msg or "API key" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid API key. Please check your Groq API key in .env file or provide it via X-API-Key header.")
        if "connection" in error_msg.lower() or "refused" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Ollama service is not available. Please ensure Ollama is running at 127.0.0.1:11434")
        raise HTTPException(status_code=500, detail=f"Failed to validate: {error_msg}")

@app.post("/upload")
async def upload_file_endpoint(file: UploadFile = File(...), api_key: Optional[str] = Depends(get_api_key)):
    """Uploads a file, saves it permanently, then streams the indexing process."""
    try:
        file_suffix = pathlib.Path(file.filename).suffix
        doc_id = str(uuid.uuid4())
        permanent_path = UPLOADS_DIR / f"{doc_id}{file_suffix}"
        
        # Save the file asynchronously
        async with aiofiles.open(permanent_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    return StreamingResponse(upload_generator(str(permanent_path), doc_id, file.filename, api_key), media_type="text/event-stream")

@app.get("/documents")
async def get_documents_endpoint(api_key: Optional[str] = Depends(get_api_key)):
    """Returns the list of all indexed documents from the manifest."""
    try:
        return await read_json_async(DOCUMENTS_FILE)
    except FileNotFoundError:
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read documents list: {e}")

@app.get("/documents/{doc_id}/file")
async def get_document_file_endpoint(doc_id: str, api_key: Optional[str] = Depends(get_api_key)):
    """Serves the original document file."""
    doc = await get_document_by_id(doc_id)
    if not doc or not doc.get("path") or not os.path.exists(doc["path"]):
        raise HTTPException(status_code=404, detail="Document file not found.")
    # Determine media type based on file extension
    doc_path = doc["path"]
    suffix = pathlib.Path(doc_path).suffix.lower()
    media_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.csv': 'text/csv',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel'
    }
    media_type = media_types.get(suffix, 'application/octet-stream')
    return FileResponse(doc_path, media_type=media_type)

# --- Chat History Endpoints ---

@app.post("/chats")
async def create_chat_endpoint(request: NewChatRequest, api_key: Optional[str] = Depends(get_api_key)):
    """(DEPRECATED) Creating a chat is now handled by the /upload endpoint."""
    raise HTTPException(
        status_code=410, 
        detail="This endpoint is deprecated. Upload a document to create a new chat."
    )

@app.get("/documents/{doc_id}/chats")
async def get_document_chats_endpoint(doc_id: str, api_key: Optional[str] = Depends(get_api_key)):
    """(DEPRECATED) Use GET /chats instead."""
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Please use GET /chats to list all conversations."
    )

@app.post("/chats/{chat_id}/query")
async def query_chat_endpoint(chat_id: str, request: QueryRequest, api_key: Optional[str] = Depends(get_api_key)):
    """Receives a query, saves the user message, and returns a streaming RAG response."""
    chat_history = await read_json_async(CHAT_HISTORY_FILE)
    
    if chat_id not in chat_history:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    # Save user message before starting the stream
    user_message = {"sender": "user", "text": request.query}
    chat_history[chat_id]["messages"].append(user_message)
    await write_json_async(CHAT_HISTORY_FILE, chat_history)
    
    return StreamingResponse(answer_generator(chat_id, request.query, request.k, api_key), media_type="text/event-stream")


@app.get("/chats/{chat_id}")
async def get_chat_history_endpoint(chat_id: str, api_key: Optional[str] = Depends(get_api_key)):
    """Gets the full message history and associated document for a specific chat."""
    chat_history = await read_json_async(CHAT_HISTORY_FILE)
    if chat_id not in chat_history:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    chat_session = chat_history[chat_id]
    
    # Also fetch the associated document details
    if 'document_id' in chat_session:
        doc = await get_document_by_id(chat_session['document_id'])
        if doc:
            chat_session['document'] = doc
        else:
            print(f"⚠️  Warning: Document {chat_session['document_id']} not found for chat {chat_id}")
            chat_session['document'] = None
    else:
        chat_session['document'] = None
        
    return chat_session

@app.delete("/chats/{chat_id}")
async def delete_chat_endpoint(chat_id: str, api_key: Optional[str] = Depends(get_api_key)):
    """Deletes a chat session and optionally its associated document if no other chats reference it."""
    try:
        # Load chat history
        chat_history = await read_json_async(CHAT_HISTORY_FILE)
        
        if chat_id not in chat_history:
            raise HTTPException(status_code=404, detail="Chat session not found.")
        
        chat = chat_history[chat_id]
        document_id = chat.get('document_id')
        
        # Remove the chat from history
        del chat_history[chat_id]
        await write_json_async(CHAT_HISTORY_FILE, chat_history)
        
        document_was_deleted = False
        
        # Check if any other chats reference this document
        if document_id:
            other_chats_with_doc = any(
                c.get('document_id') == document_id 
                for c in chat_history.values()
            )
            
            # If no other chats reference this document, delete it
            if not other_chats_with_doc:
                documents = await read_json_async(DOCUMENTS_FILE)
                doc_to_delete = None
                doc_index = -1
                
                for i, doc in enumerate(documents):
                    if doc.get('id') == document_id:
                        doc_to_delete = doc
                        doc_index = i
                        break
                
                if doc_to_delete:
                    # 1. Delete the physical file
                    file_path = doc_to_delete.get('path')
                    if file_path and os.path.exists(file_path):
                        await run_in_threadpool(os.remove, file_path)
                        print(f"🗑️  Deleted file: {file_path}")

                    # 2. Delete from vector store
                    try:
                        vectorstore = get_vectorstore(api_key)
                        # Chroma supports deletion by metadata filter
                        # Note: This requires implementing metadata-based deletion in Chroma
                        print(f"⚠️  Vector deletion for document {document_id} is not fully implemented for Chroma.")
                    except Exception as e:
                        print(f"Error during vector deletion: {e}")

                    # 3. Update documents.json
                    documents.pop(doc_index)
                    await write_json_async(DOCUMENTS_FILE, documents)
                    print(f"🗑️  Deleted document manifest for: {document_id}")
                    document_was_deleted = True
        
        return {
            "message": "Chat and associated document deleted successfully" if document_was_deleted else "Chat deleted successfully",
            "chat_id": chat_id,
            "document_deleted": document_was_deleted
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat history not found.")
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to delete chat: {str(e)}")

@app.get("/chats")
async def get_all_chats_endpoint(api_key: Optional[str] = Depends(get_api_key)):
    """Gets all chat sessions, without messages, sorted by date."""
    try:
        chat_history = await read_json_async(CHAT_HISTORY_FILE)
        
        # Return chats without the full message history for performance
        chat_list = [
            {k: v for k, v in chat.items() if k != 'messages'}
            for chat in chat_history.values()
        ]
        
        return sorted(chat_list, key=lambda x: x['created_at'], reverse=True)
    except FileNotFoundError:
        return []

@app.post("/query")
async def query_endpoint(request: QueryRequest, api_key: Optional[str] = Depends(get_api_key)):
    """(DEPRECATED) Use POST /chats/{chat_id}/query instead."""
    raise HTTPException(
        status_code=410, 
        detail="This endpoint is deprecated. Please use POST /chats/{chat_id}/query instead."
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
