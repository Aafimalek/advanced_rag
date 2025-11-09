# 📚 DocChat AI - Intelligent Document Q&A System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![React](https://img.shields.io/badge/React-18.3.1-61dafb.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**A powerful RAG (Retrieval-Augmented Generation) application for intelligent document analysis and question answering.**

[Features](#-features) • [Architecture](#-architecture) • [Installation](#-installation) • [Usage](#-usage) • [API](#-api-documentation)

</div>

---

## 🌟 Features

### Core Capabilities
- 📄 **Multi-Format Support**: Upload and analyze PDF, DOCX, and PPTX documents
- 🧠 **Advanced RAG System**: Multi-vector retrieval with Google Gemini embeddings
- 💬 **Real-time Streaming**: Live AI responses with Server-Sent Events (SSE)
- 🎯 **Accurate Citations**: Every answer includes page number references
- 🖼️ **Multimodal Processing**: Extracts and analyzes text, tables, and images
- 🗂️ **Chat History**: Persistent conversation management with multiple chats LocalStorage
- 🗑️ **Easy Management**: Delete chats and associated documents with one click
- 🎨 **Modern UI**: Beautiful sunset-themed interface with glassmorphism effects

### Technical Highlights
- ⚡ **High Performance**: FAISS vector search with optimized chunking
- 🔄 **Async Processing**: Non-blocking document processing and queries
- 📊 **Smart Context**: Retrieves 20 most relevant chunks with 2500-char chunks
- 🎭 **Clean Formatting**: Bold highlights, bullet lists, and citation badges
- 🔐 **CORS Enabled**: Secure cross-origin resource sharing
- 📝 **Type Safety**: Pydantic models for request/response validation

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React + Vite)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Sidebar    │  │  Document    │  │ Chat Panel   │         │
│  │  (Chats)     │  │   Viewer     │  │  (Messages)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                            ↕ REST API + SSE
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI + LangChain)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Document    │→ │   FAISS      │→ │    Gemini    │         │
│  │  Processing  │  │Vector Store  │  │   LLM API    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         ↓                 ↓                   ↓                  │
│  [Unstructured]    [Embeddings]      [Streaming Response]      │
└─────────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────────┐
│                    Persistence Layer                             │
│  [chat_history.json] [documents.json] [faiss_index/] [uploads/] │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

#### Backend
- **Framework**: FastAPI 0.115+
- **LLM**: Google Gemini 2.5 Flash (via LangChain)
- **Embeddings**: Google Gemini Embeddings
- **Vector Store**: FAISS (Facebook AI Similarity Search)
- **Document Processing**: Unstructured.io, PyMuPDF, python-docx
- **Async Runtime**: asyncio, aiofiles

#### Frontend
- **Framework**: React 18.3.1
- **Build Tool**: Vite
- **Styling**: Tailwind CSS with custom sunset theme
- **State Management**: React Hooks (useState, useEffect, useCallback)

---

## 🚀 Installation

### Prerequisites
- Python 3.11 or higher
- Node.js 18+ and npm
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/chat_rag.git
cd chat_rag
```

### 2. Backend Setup

#### Create Virtual Environment
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

#### Install Dependencies
```bash
pip install -r requirements.txt
```

#### Configure Environment
Create a `.env` file in the `backend` directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

#### Start Backend Server
```bash
python main.py
```
Server will run on `http://localhost:8000`

### 3. Frontend Setup

#### Install Dependencies
```bash
cd ../frontend
npm install
```

#### Start Development Server
```bash
npm run dev
```
Frontend will run on `http://localhost:5173`

---

## 📖 Usage

### Basic Workflow

1. **Upload a Document**
   - Click the "New Chat" button in the header
   - Select a PDF, DOCX, or PPTX file
   - Wait for AI processing (you'll see live progress updates)

2. **Ask Questions**
   - Type your question in the input box
   - Press Enter or click Send
   - Get streaming AI responses with page citations

3. **View Citations**
   - Hover over citation badges like `[Page 5]`
   - Referenced pages are highlighted in orange

4. **Manage Chats**
   - Click on any chat in the sidebar to view it
   - Hover over a chat and click the trash icon to delete

### Example Questions

For a research paper:
```
- "What is this research paper about?"
- "Who are the authors?"
- "What BLEU scores did the model achieve?"
- "Explain the Transformer architecture in detail"
- "List the main contributions of this paper"
```

For a resume:
```
- "What programming languages does the candidate know?"
- "List all projects mentioned in this resume"
- "What is the candidate's educational background?"
```

---

## 🔧 Configuration

### Backend Configuration (`backend/main.py`)

```python
# Model Settings
LLM_MODEL = "gemini-2.5-flash"
EMBED_MODEL = "models/gemini-embedding-001"

# Chunking Parameters
chunk_size = 2500  # Characters per chunk
chunk_overlap = 500  # Overlap between chunks

# Retrieval Settings
k = 20  # Number of chunks to retrieve per query

# LLM Settings
temperature = 0.3  # Lower = more deterministic
max_retries = 2  # Retry on API failures
```

### Frontend Configuration (`frontend/src/App.jsx`)

```javascript
// API Configuration
const API_URL = 'http://127.0.0.1:8000';

// Query Settings
const k = 20;  // Number of chunks to retrieve
```

---

## 📡 API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Upload Document
```http
POST /upload
Content-Type: multipart/form-data

Parameters:
  - file: Binary file (PDF/DOCX/PPTX)

Response: SSE Stream
  - Extraction progress
  - Chunking updates
  - Indexing status
  - Final chat object
```

#### 2. List Chats
```http
GET /chats

Response: 200 OK
[
  {
    "id": "uuid",
    "title": "Attention Is All You Need",
    "document_id": "doc-uuid",
    "messages": [...]
  }
]
```

#### 3. Get Chat Details
```http
GET /chats/{chat_id}

Response: 200 OK
{
  "id": "uuid",
  "title": "Chat Title",
  "document_id": "doc-uuid",
  "messages": [...],
  "document": {...}
}
```

#### 4. Query Chat
```http
POST /chats/{chat_id}/query
Content-Type: application/json

Body:
{
  "query": "What is this paper about?",
  "k": 20
}

Response: SSE Stream
  - context: Retrieved document chunks
  - chunk: Streaming answer text
  - complete: Final answer
```

#### 5. Delete Chat
```http
DELETE /chats/{chat_id}

Response: 200 OK
{
  "message": "Chat deleted successfully",
  "chat_id": "uuid",
  "document_deleted": true
}
```

#### 6. Get Document File
```http
GET /documents/{document_id}/file

Response: 200 OK
Content-Type: application/pdf
```

---

## 📂 Project Structure

```
chat_rag/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # Environment variables
│   ├── chat_history.json       # Chat persistence
│   ├── documents.json          # Document metadata
│   ├── uploads/                # Uploaded files
│   ├── faiss_index/            # Vector store
│   └── docstore/               # Document chunks
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main application
│   │   ├── components/
│   │   │   ├── ChatPanel.jsx        # Chat interface
│   │   │   ├── ChatSidebar.jsx      # Chat list
│   │   │   ├── DocumentViewer.jsx   # PDF viewer
│   │   │   └── ui/
│   │   │       ├── Spinner.jsx      # Loading spinner
│   │   │       └── Toast.jsx        # Notifications
│   │   ├── index.css          # Global styles
│   │   └── main.jsx           # React entry
│   ├── package.json           # Node dependencies
│   ├── vite.config.js         # Vite configuration
│   └── tailwind.config.js     # Tailwind setup
│
└── README.md                  # This file
```

---

## 🎨 UI Features

### Design Highlights
- **Sunset Theme**: Warm orange and amber accent colors
- **Glassmorphism**: Translucent panels with blur effects
- **Responsive**: Works on desktop and tablet
- **Animations**: Smooth transitions and hover effects
- **Icons**: SVG icons for all actions
- **Dark Mode**: Built-in dark color scheme

### Color Palette
```css
Primary Background: #1a1625 (Deep purple-black)
Secondary Background: #241e30 (Dark violet)
Primary Accent: #ff6b35 (Vibrant orange)
Secondary Accent: #ff8c42 (Warm tangerine)
Text Primary: #fef3f0 (Warm off-white)
Citation Badge: #ff6b35 with 20% opacity background
```

---

## 🔍 How RAG Works

### Document Processing Pipeline

1. **Document Upload**
   ```
   PDF/DOCX → Unstructured.io → Extract text, tables, images
   ```

2. **Chunking**
   ```
   Full text → RecursiveCharacterTextSplitter → 2500-char chunks
   Overlap: 500 chars for context continuity
   ```

3. **Embedding & Indexing**
   ```
   Chunks → Gemini Embeddings → FAISS Vector Store
   ```

4. **Query Processing**
   ```
   User Query → Embedding → FAISS Search → Top 20 chunks
   ```

5. **Answer Generation**
   ```
   Chunks + Query → Gemini LLM → Streaming Response
   Citations: [Page X] extracted from chunk metadata
   ```

### Multi-Vector Retrieval
- **Text Chunks**: Page-tracked, 2500 chars with 500 overlap
- **Tables**: Extracted as HTML, stored separately
- **Images**: Analyzed with Gemini Vision, stored as base64
- All elements embedded and searchable together

---

## ⚙️ Advanced Configuration

### Chunking Strategy
Adjust for different document types:

```python
# For technical papers (more context needed)
chunk_size = 3000
chunk_overlap = 600

# For shorter documents (faster processing)
chunk_size = 1500
chunk_overlap = 300
```

### Retrieval Tuning
Balance between context and speed:

```python
# More context (slower, more accurate)
k = 30

# Less context (faster, less accurate)
k = 10
```

### LLM Temperature
Control response creativity:

```python
# More deterministic (factual documents)
temperature = 0.1

# More creative (brainstorming)
temperature = 0.7
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "Failed to fetch" error
**Solution**: Ensure backend is running on port 8000
```bash
cd backend
python main.py
```

#### 2. Empty FAISS index
**Solution**: Delete existing index and re-upload documents
```bash
rm -rf backend/faiss_index/
rm -rf backend/docstore/
```

#### 3. Gemini API errors
**Solution**: Check your API key and quotas
- Verify `.env` file exists with correct key
- Check [Google AI Studio](https://makersuite.google.com) for usage limits

#### 4. "Cannot find this information"
**Solution**: The query might be too broad or info not in document
- Try more specific questions
- Check if document uploaded successfully
- Increase `k` value for more context

#### 5. Slow responses
**Solution**: Reduce chunk retrieval or upgrade API tier
- Lower `k` from 20 to 15
- Use `gemini-2.5-flash-lite` for faster responses

---

## 📊 Performance

### Benchmarks (On M1 MacBook Pro)
- **Document Upload**: ~30-60 seconds for 15-page PDF
- **Query Response**: ~2-5 seconds (streaming)
- **Context Retrieval**: ~200ms for 20 chunks
- **Embedding Generation**: ~100ms per chunk

### Optimization Tips
1. Use SSD for `faiss_index/` and `docstore/`
2. Enable GPU acceleration for FAISS (if available)
3. Batch process multiple documents
4. Cache frequently accessed chunks
5. Use CDN for static assets

---

## 🔐 Security Considerations

### Production Deployment
- [ ] Add authentication (JWT tokens)
- [ ] Implement rate limiting
- [ ] Enable HTTPS/TLS
- [ ] Validate file uploads (size, type)
- [ ] Sanitize user inputs
- [ ] Use environment variables for secrets
- [ ] Enable CORS only for trusted origins
- [ ] Implement request timeouts
- [ ] Add logging and monitoring
- [ ] Set up backup for data files

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use ESLint for JavaScript/React
- Write descriptive commit messages
- Add tests for new features
- Update documentation

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **LangChain**: For the RAG framework
- **Google Gemini**: For embeddings and LLM
- **Unstructured.io**: For document parsing
- **FAISS**: For vector similarity search
- **FastAPI**: For the backend framework
- **React**: For the frontend framework
- **Tailwind CSS**: For styling

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/chat_rag/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/chat_rag/discussions)
- **Email**: your.email@example.com

---

<div align="center">

**Built with ❤️ using React, FastAPI, and Google Gemini**

⭐ Star this repo if you find it helpful!

</div>

