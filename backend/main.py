import os
import io
import base64
import json
import uuid
import shutil
import pathlib
import tempfile
import time
import aiofiles
import warnings
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
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

# --- LangChain and Gemini Models ---
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.storage import LocalFileStore
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

# --- Document Processing ---
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.pptx import partition_pptx
import fitz  # PyMuPDF
from PIL import Image

# --- Constants ---
DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR = pathlib.Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)
DOCSTORE_DIR = pathlib.Path("docstore")
DOCSTORE_DIR.mkdir(exist_ok=True)
VEC_DIR = "faiss_index"  # Switched to FAISS
DOCUMENTS_MANIFEST_FILE = "documents.json"
EMBED_MODEL = "models/gemini-embedding-001" 
LLM_MODEL = "gemini-2.5-flash"
CHAT_HISTORY_FILE = pathlib.Path("chat_history.json")
DOCUMENTS_FILE = pathlib.Path("documents.json")

SYSTEM_PROMPT_TEMPLATE = (
    "You are a helpful and knowledgeable document assistant. Your task is to answer questions based on the context provided below.\n\n"
    "CRITICAL INSTRUCTIONS:\n"
    "1. READ THE ENTIRE CONTEXT CAREFULLY before answering\n"
    "2. Look for relevant information in ALL parts of the context (text, tables, and images)\n"
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
    "- Checked all text sections, tables, and image descriptions\n"
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
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2500,  # Larger chunks for comprehensive context
        chunk_overlap=500,  # Higher overlap ensures no information is lost at boundaries
        separators=["\n\n", "\n", ". ", "! ", "? ", ", ", " "]
    )
    
    # Vectorstore will be loaded per-request with user API keys
    # We'll check if the index exists and create directory structure
    if not os.path.exists(VEC_DIR):
        os.makedirs(VEC_DIR)
    vectorstore = None
    print("✔ Vector store directory initialized.")
        
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
    k: int = 20  # Increased to ensure we get enough text chunks along with tables/images

class NewChatRequest(BaseModel):
    document_id: str

# --- API Key Helper Functions ---
def get_api_key_from_request(request: Request) -> str:
    """Extracts API key from request headers."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key is required. Please provide X-API-Key header.")
    return api_key

def get_embeddings_model(api_key: str):
    """Creates an embeddings model with the provided API key."""
    return GoogleGenerativeAIEmbeddings(model=EMBED_MODEL, google_api_key=api_key)

def get_llm_model(api_key: str):
    """Creates an LLM model with the provided API key."""
    return ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        temperature=0.3,
        google_api_key=api_key,
        max_retries=2,
    )

def get_vectorstore(api_key: str):
    """Loads or creates vectorstore with the provided API key."""
    embeddings_model = get_embeddings_model(api_key)
    
    if os.path.exists(VEC_DIR) and os.path.exists(os.path.join(VEC_DIR, "index.faiss")):
        return FAISS.load_local(VEC_DIR, embeddings_model, allow_dangerous_deserialization=True)
    else:
        # Create a new index
        dummy_doc = Document(page_content="initial empty doc")
        vs = FAISS.from_documents([dummy_doc], embeddings_model)
        vs.save_local(VEC_DIR)
        return vs

def get_retriever(api_key: str):
    """Creates a retriever with the provided API key."""
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

# --- Document Processing and Chunking Logic (from notebook, with improvements) ---
def load_file(path: str) -> List[Any]:
    """Loads a document and partitions it into elements."""
    path = str(path)
    suffix = pathlib.Path(path).suffix.lower()
    if suffix == ".pdf":
        return partition_pdf(
            filename=path,
            extract_images_in_pdf=False,  # We'll handle images separately
            infer_table_structure=True,
            strategy="hi_res",
            languages=['en']  # Explicitly set language
        )
    if suffix == ".docx":
        return partition_docx(filename=path, include_page_breaks=True, infer_table_structure=True, extract_images_in_docx=True)
    if suffix == ".pptx":
        return partition_pptx(filename=path, include_page_breaks=True, infer_table_structure=True, extract_images_in_pptx=True)
    raise ValueError(f"Unsupported file type: {suffix}")

def pil_to_data_uri(img: Image.Image) -> str:
    """Converts a PIL Image to a data URI."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def pdf_page_images(path: str) -> Dict[int, List[str]]:
    """Extracts all meaningful raster images and vector graphics from each page of a PDF."""
    doc = fitz.open(path)
    out = {}
    
    for pno in range(len(doc)):
        page = doc[pno]
        images = []
        
        # 1. Extract raster images (like photos, screenshots)
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                # Skip small or non-RGB images
                if pix.n < 4 and (pix.width < 100 or pix.height < 100):
                    pix = None
                    continue
                if pix.n >= 4:  # RGBA -> RGB for consistency
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                
                img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(pil_to_data_uri(img_pil))
                pix = None # free memory
            except Exception as e:
                print(f"Warning: Could not process raster image on page {pno+1}: {e}")

        # 2. Extract and render vector graphics (like charts, diagrams)
        for drawing in page.get_drawings():
            rect = drawing['rect']
            if rect.width < 100 or rect.height < 100:
                continue
            try:
                pix = page.get_pixmap(clip=rect, dpi=150)
                img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(pil_to_data_uri(img_pil))
                pix = None # free memory
            except Exception as e:
                print(f"Warning: Could not render drawing on page {pno+1}: {e}")

        if images:
            out[pno + 1] = images
            
    doc.close()
    return out
        
def element_to_text(e) -> str:
    """Converts an unstructured element to a text string."""
    txt = getattr(e, 'text', '') or ''
    cat = getattr(e, 'category', '') or ''
    return f"[{cat}] {txt}".strip()

async def summarize_image_async(image_b64: str) -> str:
    """Uses Gemini vision model to describe image content."""
    try:
        prompt = "Describe this image in detail. Focus on key visual elements, text, diagrams, charts, and any important information shown."
        message = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": image_b64}
        ])
        response = await llm.ainvoke([message])
        return response.content
    except Exception as e:
        print(f"Error summarizing image: {e}")
        return "Image content could not be analyzed."

async def summarize_table_async(table_html: str, table_text: str = "") -> str:
    """Summarizes table content from HTML representation."""
    try:
        prompt = f"""Summarize the key information in this table concisely. Focus on main data points, trends, and relationships.

Table HTML:
{table_html[:2000]}

Table Text:
{table_text[:1000]}

Provide a clear, structured summary."""
        message = HumanMessage(content=prompt)
        response = await llm.ainvoke([message])
        return response.content
    except Exception as e:
        print(f"Error summarizing table: {e}")
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

async def build_multimodal_elements_streaming(file_path: str):
    """Async generator to extract and process elements, yielding status updates."""
    
    yield {"step": "extracting", "message": "Partitioning document with Unstructured..."}
    elements = await run_in_threadpool(load_file, file_path)

    # Separate elements by type
    image_elements_raw = [e for e in elements if e.category == "Image"]
    table_elements_raw = [e for e in elements if e.category == "Table"]
    text_elements_raw = [e for e in elements if e.category not in ["Image", "Table"]]

    # --- Image Processing ---
    yield {"step": "extracting", "message": f"Found {len(image_elements_raw)} images."}
    image_elements_to_process = []
    
    # Handle images extracted by PyMuPDF for PDFs
    if str(file_path).lower().endswith(".pdf"):
        pdf_images = await run_in_threadpool(pdf_page_images, file_path)
        for page_no, image_uris in pdf_images.items():
            for idx, img_b64 in enumerate(image_uris):
                image_elements_to_process.append({
                    "doc_id": str(uuid.uuid4()), "type": "image", "original": img_b64,
                    "source": str(file_path), "page": page_no, "image_index": idx
                })
    # Handle images extracted by Unstructured for DOCX/PPTX
    else:
        for elem in image_elements_raw:
            img = Image.open(io.BytesIO(elem.metadata.image_bytes))
            img_b64 = pil_to_data_uri(img)
            image_elements_to_process.append({
                "doc_id": str(uuid.uuid4()), "type": "image", "original": img_b64,
                "source": str(file_path), "page": elem.metadata.page_number
            })

    # --- Table Processing ---
    yield {"step": "extracting", "message": f"Found {len(table_elements_raw)} tables."}
    
    table_elements_to_process = []
    for elem in table_elements_raw:
        table_text = getattr(elem, 'text', '')
        table_html = getattr(elem.metadata, 'text_as_html', '') if hasattr(elem, 'metadata') else ''
        if not table_html and table_text:
            table_html = f"<table><tr><td>{table_text}</td></tr></table>"
        table_elements_to_process.append({
            "doc_id": str(uuid.uuid4()), "type": "table", "original": table_html or table_text,
            "source": str(file_path), "text_content": table_text, "html_content": table_html
        })

    # --- Text Processing with Page Numbers ---
    # Group text elements by page to preserve page information
    text_by_page = {}
    for e in text_elements_raw:
        if e.text:
            page_num = getattr(e.metadata, 'page_number', None) if hasattr(e, 'metadata') else None
            if page_num not in text_by_page:
                text_by_page[page_num] = []
            text_by_page[page_num].append(e.text)
    
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
                    "page": page_num,  # Add page number
                    "chunk_index": i
                })
        
        yield {"step": "chunking", "message": f"Created {len(text_elements_to_process)} text chunks across {len(text_by_page)} pages."}

    # --- Concurrent Summarization ---
    yield {"step": "summarizing", "message": "Starting concurrent summarization of all elements..."}
    
    image_tasks = [summarize_image_async(e["original"]) for e in image_elements_to_process]
    table_tasks = [summarize_table_async(e["html_content"], e["text_content"]) for e in table_elements_to_process]
    text_tasks = [summarize_text_async(e["original"], e.get("page"), e.get("chunk_index", 0)) for e in text_elements_to_process]

    all_tasks = image_tasks + table_tasks + text_tasks
    total_tasks = len(all_tasks)
    
    summaries = []
    # Using a semaphore to limit concurrency if needed in future, but for now just gather
    for i, coro in enumerate(asyncio.as_completed(all_tasks)):
        summary = await coro
        summaries.append(summary)
        yield {"step": "summarizing", "message": f"Summarized element {i+1}/{total_tasks}..."}

    # Assign summaries back to elements
    all_processed_elements = []
    summary_idx = 0
    
    for elem in image_elements_to_process:
        elem["summary"] = summaries[summary_idx]
        all_processed_elements.append(elem)
        summary_idx += 1
        
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
    # Get vectorstore for this request with user's API key
    vectorstore_user = get_vectorstore(api_key)
    
    yield {"step": "extraction", "message": f"Processing file: {original_filename}"}
    
    elements_generator = build_multimodal_elements_streaming(fp)
    all_elements = {"images": [], "tables": [], "texts": []}

    async for status in elements_generator:
        if status.get("type") == "element":
            elem = status["element"]
            all_elements[f"{elem['type']}s"].append(elem)
        else:
            yield status

    yield {"step": "indexing", "message": "Storing summaries and original documents..."}
    
    total_indexed = 0
    total_elements = sum(len(v) for v in all_elements.values())

    for elem_type, elems in all_elements.items():
        for elem in elems:
            total_indexed += 1
            yield {"step": "indexing", "message": f"Indexing {elem['type']} element {total_indexed}/{total_elements}..."}
            
            await run_in_threadpool(docstore.mset, [(elem["doc_id"], json.dumps(elem).encode("utf-8"))])

            metadata = {"doc_id": elem["doc_id"], "type": elem["type"], "source": elem["source"]}
            if 'page' in elem: metadata['page'] = elem['page']
            if 'chunk_index' in elem: metadata['chunk'] = elem['chunk_index']

            summary_doc = Document(page_content=elem["summary"], metadata=metadata)
            await run_in_threadpool(vectorstore_user.add_documents, [summary_doc])

    yield {"step": "saving", "message": "Saving vector index to disk..."}
    await run_in_threadpool(vectorstore_user.save_local, VEC_DIR)
    
    # Update manifest
    yield {"step": "manifest", "message": "Updating document manifest..."}
    new_document_record = None
    try:
        documents = await read_json_async(DOCUMENTS_FILE)
    except (FileNotFoundError, json.JSONDecodeError):
        documents = []
        
    existing_doc_index = next((i for i, doc in enumerate(documents) if doc["name"] == original_filename), -1)
        
    stats = { "images": len(all_elements["images"]), "tables": len(all_elements["tables"]), "texts": len(all_elements["texts"]) }
        
    if existing_doc_index != -1:
        documents[existing_doc_index]["uploadedAt"] = datetime.now().isoformat()
        documents[existing_doc_index]["stats"] = stats
        documents[existing_doc_index]["preview"] = f"Re-indexed with {stats['texts']} texts, {stats['images']} images, {stats['tables']} tables."
        new_document_record = documents[existing_doc_index]
    else:
        new_document_record = {
            "id": doc_id,
            "name": original_filename,
            "path": fp,
            "uploadedAt": datetime.now().isoformat(),
            "preview": f"Indexed with {stats['texts']} texts, {stats['images']} images, {stats['tables']} tables.",
            "stats": stats
        }
        documents.append(new_document_record)
        
    await write_json_async(DOCUMENTS_FILE, documents)

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
    images = []
    tables = []
    texts = []
    
    for elem in originals:
        if isinstance(elem, dict):
            elem_type = elem.get("type", "")
            if elem_type == "image":
                images.append(elem["original"])
            elif elem_type == "table":
                tables.append(elem["original"])
            elif elem_type == "text":
                texts.append(elem["original"])
    
    element_counts = {
        "images": len(images),
        "tables": len(tables),
        "texts": len(texts)
    }
    
    print(f"  📊 Element breakdown: {element_counts['images']} images, {element_counts['tables']} tables, {element_counts['texts']} text chunks")
    
    # 5. Build context from texts and tables
    context_parts = []
    if texts:
        context_parts.append("=== TEXT CONTEXT ===\n" + "\n\n".join(texts))
    if tables:
        context_parts.append("=== TABLE CONTEXT ===\n" + "\n\n".join(tables))
    
    context = "\n\n".join(context_parts)
    
    # 6. Invoke multimodal LLM with text and images
    messages = [SystemMessage(content=SYSTEM_PROMPT_TEMPLATE)]
    
    human_text = f"Query: {query}\n\nContext:\n{context}\n\nAnswer:"
    
    if images:
        print(f"  🖼️  Including {len(images)} images in context")
        human_parts = [{"type": "text", "text": human_text}]
        for img in images[:4]:  # Limit to 4 images to avoid token limits
            human_parts.append({"type": "image_url", "image_url": img})
        messages.append(HumanMessage(content=human_parts))
    else:
        messages.append(HumanMessage(content=human_text))
    
    print(f"  🤖 Generating answer with multimodal LLM...")
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
    summary_docs = await run_in_threadpool(vectorstore_user.similarity_search, query, k=k)
    print(f"  📦 Retrieved {len(summary_docs)} document chunks from vector store")
    chunks_for_json = [{"page_content": doc.page_content, "metadata": doc.metadata} for doc in summary_docs]
    
    # First, yield the context so the frontend can show sources immediately.
    yield f"data: {json.dumps({'type': 'context', 'chunks': chunks_for_json})}\n\n"
    
    # Fetch original elements and build multimodal context
    doc_ids = [doc.metadata.get("doc_id") for doc in summary_docs if "doc_id" in doc.metadata]
    originals_raw = await run_in_threadpool(docstore.mget, doc_ids)
    originals = [json.loads(o.decode("utf-8")) for o in originals_raw if o is not None]
    
    images, tables, texts = [], [], []
    for elem in originals:
        if isinstance(elem, dict):
            elem_type = elem.get("type")
            page_num = elem.get("page", "Unknown")
            
            if elem_type == "image":
                images.append(elem["original"])
            elif elem_type == "table":
                table_content = f"[From Page {page_num}]\n{elem['original']}"
                tables.append(table_content)
            elif elem_type == "text":
                text_content = f"[From Page {page_num}]\n{elem['original']}"
                texts.append(text_content)
    
    # Build structured context with clear sections
    context_parts = []
    
    if texts:
        context_parts.append("=== DOCUMENT TEXT ===")
        context_parts.append("\n\n".join(texts))
    
    if tables:
        context_parts.append("\n\n=== TABLES AND STRUCTURED DATA ===")
        context_parts.append("\n\n".join(tables))
    
    context = "\n\n".join(context_parts) if context_parts else "No context available."
    
    # Log context statistics
    print(f"  📊 Context built: {len(texts)} text chunks, {len(tables)} tables, {len(images)} images")
    print(f"  📏 Total context length: {len(context)} characters")
    
    # Build messages for the LLM
    messages = [SystemMessage(content=SYSTEM_PROMPT_TEMPLATE)]
    human_text = f"Query: {query}\n\nContext:\n{context}\n\nAnswer:"
    if images:
        human_parts = [{"type": "text", "text": human_text}]
        for img in images[:4]: human_parts.append({"type": "image_url", "image_url": img})
        messages.append(HumanMessage(content=human_parts))
    else:
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
        
        # Handle specific Gemini API errors
        if "list index out of range" in error_msg or "IndexError" in error_msg:
            error_response = "I apologize, but I encountered an issue processing your request. This may be due to content safety filters or an empty response from the AI. Please try rephrasing your question or asking something different."
        elif "SAFETY" in error_msg.upper() or "BLOCKED" in error_msg.upper():
            error_response = "I apologize, but this query was blocked by content safety filters. Please try rephrasing your question."
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


# --- API Key Validation Endpoint ---
@app.post("/validate-api-key")
async def validate_api_key_endpoint(request: Request):
    """Validates the provided API key by attempting to create a simple embeddings model."""
    try:
        api_key = get_api_key_from_request(request)
        
        # Try to create an embeddings model to test the API key
        test_embeddings = get_embeddings_model(api_key)
        
        # Perform a simple test to validate the key works
        # This will raise an exception if the key is invalid
        await run_in_threadpool(test_embeddings.embed_query, "test")
        
        return {"valid": True, "message": "API key is valid"}
    except HTTPException as e:
        raise e
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid API key. Please check your Google Gemini API key.")
        raise HTTPException(status_code=500, detail=f"Failed to validate API key: {error_msg}")

@app.post("/upload")
async def upload_file_endpoint(request: Request, file: UploadFile = File(...)):
    """Uploads a file, saves it permanently, then streams the indexing process."""
    try:
        # Validate API key first
        api_key = get_api_key_from_request(request)
        
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
async def get_documents_endpoint():
    """Returns the list of all indexed documents from the manifest."""
    try:
        return await read_json_async(DOCUMENTS_FILE)
    except FileNotFoundError:
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read documents list: {e}")

@app.get("/documents/{doc_id}/file")
async def get_document_file_endpoint(doc_id: str):
    """Serves the original document file."""
    doc = await get_document_by_id(doc_id)
    if not doc or not doc.get("path") or not os.path.exists(doc["path"]):
        raise HTTPException(status_code=404, detail="Document file not found.")
    return FileResponse(doc["path"], media_type='application/pdf')

# --- Chat History Endpoints ---

@app.post("/chats")
async def create_chat_endpoint(request: NewChatRequest):
    """(DEPRECATED) Creating a chat is now handled by the /upload endpoint."""
    raise HTTPException(
        status_code=410, 
        detail="This endpoint is deprecated. Upload a document to create a new chat."
    )

@app.get("/documents/{doc_id}/chats")
async def get_document_chats_endpoint(doc_id: str):
    """(DEPRECATED) Use GET /chats instead."""
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Please use GET /chats to list all conversations."
    )

@app.post("/chats/{chat_id}/query")
async def query_chat_endpoint(chat_id: str, req: Request, request: QueryRequest):
    """Receives a query, saves the user message, and returns a streaming RAG response."""
    # Get API key from headers
    api_key = get_api_key_from_request(req)
    
    chat_history = await read_json_async(CHAT_HISTORY_FILE)
    
    if chat_id not in chat_history:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    # Save user message before starting the stream
    user_message = {"sender": "user", "text": request.query}
    chat_history[chat_id]["messages"].append(user_message)
    await write_json_async(CHAT_HISTORY_FILE, chat_history)
    
    return StreamingResponse(answer_generator(chat_id, request.query, request.k, api_key), media_type="text/event-stream")


@app.get("/chats/{chat_id}")
async def get_chat_history_endpoint(chat_id: str):
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
async def delete_chat_endpoint(chat_id: str):
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
                
                for i, doc in enumerate(documents):
                    if doc.get('id') == document_id:
                        doc_to_delete = doc
                        documents.pop(i)
                        break
                
                if doc_to_delete:
                    # Delete the physical file
                    file_path = doc_to_delete.get('path')
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"🗑️  Deleted file: {file_path}")
                    
                    # Update documents.json
                    await write_json_async(DOCUMENTS_FILE, documents)
                    print(f"🗑️  Deleted document: {document_id}")
                    
                    return {
                        "message": "Chat and associated document deleted successfully",
                        "chat_id": chat_id,
                        "document_deleted": True
                    }
        
        return {
            "message": "Chat deleted successfully",
            "chat_id": chat_id,
            "document_deleted": False
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat history not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat: {str(e)}")

@app.get("/chats")
async def get_all_chats_endpoint():
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
async def query_endpoint(request: QueryRequest):
    """(DEPRECATED) Use POST /chats/{chat_id}/query instead."""
    raise HTTPException(
        status_code=410, 
        detail="This endpoint is deprecated. Please use POST /chats/{chat_id}/query instead."
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
