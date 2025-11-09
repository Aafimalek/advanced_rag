import React, { useState, useEffect, useCallback, Component } from 'react';
import Spinner from './components/ui/Spinner';
import Toast from './components/ui/Toast';
import DocumentViewer from './components/DocumentViewer';
import ChatPanel from './components/ChatPanel';
import ChatSidebar from './components/ChatSidebar.jsx';
import ApiKeyModal from './components/ApiKeyModal';
import ApiKeySettings from './components/ApiKeySettings';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('React rendering error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen flex flex-col items-center justify-center bg-gradient-to-br from-[#1a1625] via-[#241e30] to-[#1a1625] text-[#fef3f0] p-8">
          <h1 className="text-2xl font-bold mb-4 gradient-text">Something went wrong</h1>
          <p className="text-lg mb-4 text-center max-w-md">An error occurred while rendering the app. Please check the browser console (F12) for details.</p>
          <button 
            onClick={() => window.location.reload()} 
            className="bg-gradient-to-br from-[#ff6b35] to-[#ff8c42] text-white px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-[#ff6b35]/30 transition-all"
          >
            Reload App
          </button>
          {this.state.error && (
            <details className="mt-6 p-4 bg-[#2d2640]/80 rounded-xl border border-[#4a4062]">
              <summary className="cursor-pointer font-medium">Error details (click to expand)</summary>
              <pre className="mt-2 text-sm text-[#c4b5d6] overflow-auto max-h-40">{this.state.error.toString()}</pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

const API_URL = 'http://127.0.0.1:8000';

function App() {
  // API Key State
  const [apiKey, setApiKey] = useState(null);
  
  // Global State
  const [toast, setToast] = useState(null);
  const [error, setError] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  
  // Chat-centric State
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isAnswering, setIsAnswering] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // --- Utility Functions ---
  const showToast = useCallback((message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }, []);

  // --- Data Fetching Effects ---

  // Fetch all chats on initial load
  useEffect(() => {
    if (!apiKey) return; // Don't fetch if no API key
    
    const fetchChats = async () => {
      try {
        const response = await fetch(`${API_URL}/chats`, {
          headers: {
            'X-API-Key': apiKey
          }
        });
        if (!response.ok) throw new Error('Failed to fetch chats');
        const chatData = await response.json();
        
        // Ensure chatData is an array
        const validChats = Array.isArray(chatData) ? chatData : [];
        setChats(validChats);
        
        if (validChats.length > 0) {
          // If there's no active chat selected, select the most recent one
          if (!activeChatId) {
            setActiveChatId(validChats[0].id);
          }
        }
      } catch (err) {
        console.error('Error fetching chats:', err);
        setError(`Could not load chats: ${err.message}. Is the backend running at ${API_URL}?`);
        // Set empty array so the app doesn't crash
        setChats([]);
      }
    };
    fetchChats();
  }, [apiKey]); // Reload chats when API key changes

  // Fetch full chat details (messages and document) when activeChatId changes
  useEffect(() => {
    if (!apiKey || !activeChatId || activeChatId.startsWith('uploading-')) {
      if (!activeChatId) {
        setActiveChat(null);
        setMessages([]);
      }
      return;
    }
    const fetchChatDetails = async () => {
      setIsAnswering(true);
      try {
        const response = await fetch(`${API_URL}/chats/${activeChatId}`, {
          headers: {
            'X-API-Key': apiKey
          }
        });
        if (!response.ok) throw new Error('Failed to fetch chat details');
        const chatData = await response.json();
        console.log('Fetched chat data:', chatData);
        console.log('Document in chat:', chatData.document);
        setActiveChat(chatData);
        setMessages(chatData.messages || []);
      } catch (err) {
        console.error('Error fetching chat details:', err);
        setError(`Could not load chat details: ${err.message}`);
        // Don't crash - just clear the active chat
        setActiveChat(null);
        setMessages([]);
      } finally {
        setIsAnswering(false);
      }
    };
    fetchChatDetails();
  }, [activeChatId, apiKey]);


  // --- Event Handlers ---

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !activeChatId) return;

    const userMessage = { sender: 'user', text: inputValue };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsAnswering(true);
    setError('');

    // Add a placeholder for the bot's response
    const botMessageId = `bot-${Date.now()}`;
    const initialBotMessage = { id: botMessageId, sender: 'bot', text: '', chunks: [] };
    setMessages(prev => [...prev, initialBotMessage]);

    try {
      const response = await fetch(`${API_URL}/chats/${activeChatId}/query`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({ query: userMessage.text, k: 20 }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to get response');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n').filter(line => line.trim().startsWith('data:'));

        for (const line of lines) {
          const jsonData = line.substring(5);
          try {
            const parsedData = JSON.parse(jsonData);

            setMessages(prev => prev.map(msg => {
              if (msg.id !== botMessageId) return msg;
              
              let newText = msg.text;
              let newChunks = msg.chunks;

              if (parsedData.type === 'chunk' && parsedData.content) {
                newText += parsedData.content;
              }
              if (parsedData.type === 'context' && parsedData.chunks) {
                newChunks = parsedData.chunks;
              }
              
              return { ...msg, text: newText, chunks: newChunks };
            }));

          } catch (e) {
            console.error("Failed to parse JSON from stream:", jsonData, e);
          }
        }
      }

    } catch (err) {
      setError(err.message);
      setMessages(prev => prev.map(msg =>
        msg.id === botMessageId
          ? { ...msg, text: `Sorry, an error occurred: ${err.message}` }
          : msg
      ));
    } finally {
      setIsAnswering(false);
    }
  };

  const handleDeleteChat = async (chatId) => {
    try {
      const response = await fetch(`${API_URL}/chats/${chatId}`, {
        method: 'DELETE',
        headers: {
          'X-API-Key': apiKey
        }
      });

      if (!response.ok) {
        throw new Error('Failed to delete chat');
      }

      const result = await response.json();
      console.log('Delete result:', result);

      // Remove chat from local state
      setChats(prev => prev.filter(c => c.id !== chatId));

      // If the deleted chat was active, clear the active chat
      if (activeChatId === chatId) {
        setActiveChatId(null);
        setActiveChat(null);
        setMessages([]);
      }

      // Show success message
      showToast(
        result.document_deleted 
          ? 'Chat and document deleted successfully' 
          : 'Chat deleted successfully',
        'success'
      );
    } catch (err) {
      console.error('Error deleting chat:', err);
      setError(`Failed to delete chat: ${err.message}`);
    }
  };

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    event.target.value = '';
    setIsUploading(true);
    
    // Create a temporary chat to show progress
    const tempChatId = `uploading-${Date.now()}`;
    const tempChat = {
      id: tempChatId,
      title: file.name,
      created_at: new Date().toISOString(),
      messages: [],
      document: null,
      isTemporary: true,
      isProcessing: true, // Flag to show special processing state
    };
    
    setChats(prev => [tempChat, ...prev]);
    setActiveChatId(tempChatId);
    setActiveChat(tempChat);
    setMessages([]);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        headers: {
          'X-API-Key': apiKey
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed with status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let finalData = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n').filter((line) => line.trim().startsWith('data:'));
        
        for (const line of lines) {
          const jsonData = line.substring(5);
          try {
            const parsedData = JSON.parse(jsonData);
            console.log("Received stream data:", parsedData); // For debugging
            
            // Add progress message to temporary chat
            const progressMessage = {
              sender: 'bot',
              text: `[${parsedData.step}] ${parsedData.message}`,
            };
            setMessages(prev => [...prev, progressMessage]);

            if (parsedData.step === 'complete') {
              finalData = parsedData;
            } else if (parsedData.step === 'error') {
               showToast(parsedData.message, 'error');
            }
          } catch (e) { console.error("Failed to parse JSON from stream:", jsonData, e); }
        }
      }
      
      if (finalData && finalData.chat) {
        showToast('Document processed successfully!', 'success');
        const realChat = finalData.chat;
        
        // Replace temporary chat with the real one
        setChats(prev => prev.map(c => c.id === tempChatId ? realChat : c));
        setActiveChatId(realChat.id); // Switch to the real chat ID
      } else {
        throw new Error("Did not receive final chat object from server.");
      }

    } catch (err) {
      setError(err.message);
      showToast(`Upload error: ${err.message}`, 'error');
      // Remove temporary chat on error
      setChats(prev => prev.filter(c => c.id !== tempChatId));
    } finally {
      setIsUploading(false);
    }
  };
  
  return (
    <ErrorBoundary>
      {/* API Key Modal */}
      {!apiKey && <ApiKeyModal onApiKeySet={setApiKey} />}
      
      <div className="h-screen flex flex-col bg-gradient-to-br from-[#1a1625] via-[#241e30] to-[#1a1625] text-[#fef3f0]">
        {/* Header - Modern Glassmorphism */}
        <header className="h-[72px] glass-effect border-b border-white/5 flex items-center px-6 gap-4 relative z-[100] shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="group p-2.5 rounded-xl hover:bg-gradient-to-br hover:from-orange-500/10 hover:to-amber-500/10 transition-all duration-300 border border-transparent hover:border-orange-500/20"
            title="Toggle Sidebar"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400 group-hover:text-[#ff6b35] transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          
          <div className="flex-1 flex items-center justify-center">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#ff6b35] to-[#ff8c42] flex items-center justify-center shadow-lg shadow-[#ff6b35]/25">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold gradient-text tracking-tight">DocChat AI</h1>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <ApiKeySettings apiKey={apiKey} onApiKeyChange={setApiKey} />
            
            <label 
              htmlFor="upload-input"
              className={`group relative px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 inline-flex items-center gap-2 overflow-hidden
                ${isUploading 
                  ? 'bg-gradient-to-r from-[#ff6b35]/50 to-[#ff8c42]/50 cursor-not-allowed' 
                  : 'bg-gradient-to-r from-[#ff6b35] to-[#ff8c42] hover:from-[#ff8c42] hover:to-[#ffa07a] cursor-pointer hover:shadow-lg hover:shadow-[#ff6b35]/40 hover:-translate-y-0.5 active:translate-y-0'
                } border border-white/10`}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-[#ffa07a]/0 via-white/25 to-[#ff8c42]/0 translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-1000"></div>
              <span className="relative flex items-center gap-2">
                {isUploading ? (
                  <Spinner />
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                )}
                <span className="text-white">{isUploading ? 'Processing...' : 'New Chat'}</span>
              </span>
            </label>
            <input
              id="upload-input" 
              type="file" 
              accept=".pdf,.docx,.pptx"
              onChange={handleUpload} 
              disabled={isUploading} 
              className="hidden"
            />
          </div>
        </header>

        <div className="flex-1 flex overflow-hidden h-[calc(100vh-72px)]">
          {/* Chats Sidebar */}
          <ChatSidebar
            chats={chats}
            activeChatId={activeChatId}
            onSelectChat={setActiveChatId}
            onDeleteChat={handleDeleteChat}
            isSidebarOpen={isSidebarOpen}
          />

          {/* Main Content Area */}
          <main className="flex-1 flex overflow-hidden gap-0.5 bg-white/5">
            <DocumentViewer document={activeChat?.document} />
            <ChatPanel
              activeChat={activeChat}
              messages={messages}
              isAnswering={isAnswering}
              inputValue={inputValue}
              onSendMessage={handleSendMessage}
              onInputChange={(e) => setInputValue(e.target.value)}
            />
          </main>
        </div>
        
        {/* Toast Notifications */}
        {toast && (
          <div className="fixed top-20 right-6 z-[1000] animate-slide-in-right">
            <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
          </div>
        )}
        
        {/* Error Notification */}
        {error && (
          <div className="fixed bottom-6 right-6 glass-effect border border-red-500/30 text-white py-4 px-6 rounded-2xl shadow-2xl shadow-red-500/20 z-[1000] animate-slide-in-right max-w-md">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="font-medium text-sm mb-1">Error</p>
                <p className="text-sm text-gray-300">{error}</p>
              </div>
              <button 
                onClick={() => setError('')} 
                className="text-gray-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/10"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}

export default App;
