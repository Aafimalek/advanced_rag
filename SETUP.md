# 🚀 Quick Setup Guide

This guide will help you get DocChat AI up and running in under 5 minutes!

---

## Prerequisites Checklist

Before starting, make sure you have:

- [ ] Python 3.11 or higher ([Download](https://www.python.org/downloads/))
- [ ] Node.js 18+ and npm ([Download](https://nodejs.org/))
- [ ] Git ([Download](https://git-scm.com/downloads))
- [ ] Google Gemini API key ([Get one FREE](https://makersuite.google.com/app/apikey))
- [ ] 2GB free disk space
- [ ] Stable internet connection

---

## 📥 Step-by-Step Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/chat_rag.git
cd chat_rag
```

### Step 2: Backend Setup (3 minutes)

#### 2.1 Navigate to backend directory
```bash
cd backend
```

#### 2.2 Create and activate virtual environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prompt.

#### 2.3 Install Python dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will take 2-3 minutes. ☕

#### 2.4 Configure API Key

Create a file named `.env` in the `backend` directory:

**Windows (Command Prompt):**
```cmd
echo GEMINI_API_KEY=your_actual_api_key_here > .env
```

**macOS/Linux or Windows (PowerShell):**
```bash
echo "GEMINI_API_KEY=your_actual_api_key_here" > .env
```

**Or manually:**
1. Create a file named `.env` in the `backend` folder
2. Add this line: `GEMINI_API_KEY=your_actual_api_key_here`
3. Replace `your_actual_api_key_here` with your real API key

#### 2.5 Start the backend server
```bash
python main.py
```

✅ You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
✔ Models, stores, and retriever initialized.
```

**Keep this terminal open!** The backend needs to stay running.

---

### Step 3: Frontend Setup (2 minutes)

Open a **NEW terminal window** and navigate to the project:

```bash
cd chat_rag/frontend
```

#### 3.1 Install Node dependencies
```bash
npm install
```

This will take 1-2 minutes. ☕

#### 3.2 Start the development server
```bash
npm run dev
```

✅ You should see:
```
  VITE v5.x.x  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h + enter to show help
```

---

## 🎉 You're Done!

Open your browser and go to: **http://localhost:5173**

You should see the DocChat AI interface! 🚀

---

## 🧪 Test Your Installation

### Upload Your First Document

1. Click the **"New Chat"** button (top right, orange button)
2. Select a PDF file (try a research paper or any PDF)
3. Wait 30-60 seconds for processing
4. Ask a question like: "What is this document about?"

### Example Test Questions

If you uploaded "Attention Is All You Need" paper:
- "Who are the authors?"
- "What BLEU scores did the model achieve?"
- "Explain the Transformer architecture"

---

## 🐛 Troubleshooting

### Backend won't start

**Error: `ModuleNotFoundError: No module named 'fastapi'`**
```bash
# Make sure virtual environment is activated
# You should see (.venv) in your prompt
pip install -r requirements.txt
```

**Error: `No API key found`**
```bash
# Check your .env file exists in backend directory
# It should contain: GEMINI_API_KEY=your_key
```

### Frontend won't start

**Error: `Cannot find module`**
```bash
# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Error: `Port 5173 already in use`**
```bash
# Kill the process using port 5173
# Windows:
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# macOS/Linux:
lsof -ti:5173 | xargs kill -9
```

### Connection Issues

**Error: `Failed to fetch`**
- Make sure backend is running (check terminal)
- Backend should be on `http://localhost:8000`
- Frontend should be on `http://localhost:5173`
- Check if firewall is blocking the connection

---

## 🔄 Daily Usage

### Starting the Application

**Every time you want to use the app:**

1. **Start Backend** (Terminal 1):
   ```bash
   cd chat_rag/backend
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   python main.py
   ```

2. **Start Frontend** (Terminal 2):
   ```bash
   cd chat_rag/frontend
   npm run dev
   ```

3. **Open Browser**: http://localhost:5173

### Stopping the Application

- Press `Ctrl+C` in both terminal windows
- Close the browser tab

---

## 📦 Optional: Create Shortcuts

### Windows Batch File

Create `start_backend.bat`:
```batch
@echo off
cd backend
call .venv\Scripts\activate
python main.py
pause
```

Create `start_frontend.bat`:
```batch
@echo off
cd frontend
npm run dev
pause
```

### macOS/Linux Shell Script

Create `start_backend.sh`:
```bash
#!/bin/bash
cd backend
source .venv/bin/activate
python main.py
```

Create `start_frontend.sh`:
```bash
#!/bin/bash
cd frontend
npm run dev
```

Make them executable:
```bash
chmod +x start_backend.sh start_frontend.sh
```

---

## 🎓 Next Steps

1. ✅ Read the [README.md](README.md) for detailed documentation
2. ✅ Try uploading different document types (PDF, DOCX, PPTX)
3. ✅ Experiment with different questions
4. ✅ Check the [API Documentation](README.md#-api-documentation)
5. ✅ Customize the [Configuration](README.md#-configuration)

---

## 💬 Need Help?

- **Documentation**: See [README.md](README.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/chat_rag/issues)
- **Community**: [Discussions](https://github.com/yourusername/chat_rag/discussions)

---

## ⚡ Pro Tips

1. **Faster Processing**: Use smaller documents for testing
2. **Better Answers**: Ask specific questions with context
3. **Citations**: Always check the `[Page X]` references
4. **Multiple Chats**: Create separate chats for different documents
5. **Clean Up**: Delete old chats to free up space

---

**Happy Chatting! 🎉**

