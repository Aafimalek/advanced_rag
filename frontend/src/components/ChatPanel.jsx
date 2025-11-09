import React, { useRef, useEffect } from 'react';
import Spinner from './ui/Spinner';

const ChatPanel = ({
  activeChat,
  messages,
  isAnswering,
  inputValue,
  onSendMessage,
  onInputChange,
}) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <aside className="basis-[55%] glass-effect flex flex-col">
      {/* Message Area */}
      <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-4 relative z-[1] chat-scrollbar">
        {!activeChat ? (
          <div className="flex-1 flex flex-col justify-center items-center text-center py-10 px-4 gap-6">
            <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-orange-500/20 to-amber-500/20 flex items-center justify-center border border-orange-500/30 mb-4">
              <svg className="w-10 h-10 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <div>
              <h2 className="text-2xl font-bold gradient-text mb-2">Welcome to DocChat AI</h2>
              <p className="text-gray-400 text-sm max-w-md">Upload a PDF, DOCX, or PPTX to start an intelligent conversation about your document</p>
            </div>
          </div>
        ) : activeChat.isProcessing ? (
          <div className="flex-1 flex flex-col justify-center items-center text-center py-10 px-4 gap-8">
            {/* AI Brain Animation */}
            <div className="relative">
              <div className="w-32 h-32 rounded-3xl bg-gradient-to-br from-orange-500/20 to-amber-500/20 flex items-center justify-center border border-orange-500/30 animate-pulse">
                <svg className="w-16 h-16 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              {/* Orbiting dots */}
              <div className="absolute inset-0 animate-spin" style={{ animationDuration: '3s' }}>
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-orange-500 shadow-lg shadow-orange-500/50"></div>
              </div>
              <div className="absolute inset-0 animate-spin" style={{ animationDuration: '2s', animationDirection: 'reverse' }}>
                <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-amber-400 shadow-lg shadow-amber-400/50"></div>
              </div>
              <div className="absolute inset-0 animate-spin" style={{ animationDuration: '2.5s' }}>
                <div className="absolute top-1/2 right-0 -translate-y-1/2 w-3 h-3 rounded-full bg-pink-400 shadow-lg shadow-pink-400/50"></div>
              </div>
            </div>
            
            {/* Status Messages */}
            <div className="max-w-md">
              <h2 className="text-2xl font-bold gradient-text mb-3">AI is Processing</h2>
              <p className="text-gray-300 text-sm mb-4">Analyzing your document with advanced AI...</p>
              
              {/* Progress Steps */}
              <div className="space-y-3 text-left">
                {messages.map((msg, index) => (
                  <div key={index} className="flex items-start gap-3 animate-slide-up">
                    <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-orange-500/20 to-amber-500/20 flex items-center justify-center flex-shrink-0 border border-orange-500/30">
                      <svg className="w-3.5 h-3.5 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <p className="text-sm text-gray-400 flex-1">{msg.text}</p>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Animated thinking dots */}
            <div className="flex gap-2">
              <div className="w-2 h-2 rounded-full bg-orange-500 animate-bounce" style={{ animationDelay: '0s' }}></div>
              <div className="w-2 h-2 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              <div className="w-2 h-2 rounded-full bg-pink-400 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, index) => (
              <div key={index} className={`flex max-w-[85%] animate-slide-up ${msg.sender === 'user' ? 'self-end' : 'self-start'}`}>
                <div className={`group relative
                  ${msg.sender === 'user'
                    ? 'bg-gradient-to-br from-orange-500 to-amber-500 text-white rounded-2xl rounded-br-md shadow-lg shadow-orange-500/20'
                    : 'bento-card rounded-2xl rounded-bl-md'
                  } p-5 px-6 max-w-full break-words leading-relaxed`}>
                  {/* Message content with improved typography */}
                  <div className={`prose prose-sm max-w-none ${msg.sender === 'user' ? 'prose-invert' : 'prose-gray'}`}>
                    {msg.sender === 'user' ? (
                      <p className="m-0 whitespace-pre-wrap text-[15px]">{msg.text}</p>
                    ) : (
                      <div className="space-y-3 text-[15px] text-gray-200">
                        {msg.text.split('\n\n').map((paragraph, pIndex) => {
                          // Check if it's a bullet point list item
                          const isBulletPoint = paragraph.trim().match(/^[•\-\*]\s/);
                          
                          // Check if it's a numbered list item (e.g., "* **28.4 BLEU**")
                          const isListItem = paragraph.trim().match(/^\*\s/);
                          
                          return (
                            <div key={pIndex} className={`${isBulletPoint || isListItem ? 'flex items-start gap-2' : ''}`}>
                              {isBulletPoint && (
                                <span className="text-orange-400 mt-0.5 flex-shrink-0">•</span>
                              )}
                              <p className={`m-0 leading-relaxed ${isBulletPoint || isListItem ? 'flex-1' : ''}`}>
                                {paragraph
                                  .replace(/^\*\s/, '') // Remove leading asterisk
                                  .replace(/^[•\-]\s/, '') // Remove bullet
                                  .split(/(\[Page\s+[\d,\s]+\]|\*\*.*?\*\*)/g)
                                  .map((part, partIndex) => {
                                    // Handle citations
                                    if (part.match(/\[Page\s+[\d,\s]+\]/)) {
                                      return (
                                        <span
                                          key={partIndex}
                                          className="inline-flex items-center ml-1 px-2 py-0.5 rounded-md bg-orange-500/20 text-orange-400 text-xs font-medium border border-orange-500/30 hover:bg-orange-500/30 transition-colors"
                                          title="Source citation"
                                        >
                                          {part}
                                        </span>
                                      );
                                    }
                                    // Handle bold text (e.g., **28.4 BLEU**)
                                    if (part.match(/^\*\*(.*?)\*\*$/)) {
                                      const boldText = part.replace(/\*\*/g, '');
                                      return (
                                        <span key={partIndex} className="font-semibold text-orange-300">
                                          {boldText}
                                        </span>
                                      );
                                    }
                                    return <span key={partIndex}>{part}</span>;
                                  })}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                  
                  {/* Timestamp on hover */}
                  <div className="absolute -bottom-5 text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity">
                    {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ))}
            {isAnswering && (
              <div className="flex max-w-[75%] self-start">
                <div className="bento-card rounded-2xl rounded-bl-md p-4 px-5 flex items-center gap-3">
                  <Spinner />
                  <div className="flex flex-col gap-1">
                    <p className="m-0 text-sm font-medium text-gray-200">AI is thinking</p>
                    <p className="m-0 text-xs text-gray-400">Analyzing your query...</p>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="p-6 border-t border-white/5 glass-effect flex gap-3 items-end relative z-[10]">
        <div className="flex-1 relative">
          <input
            type="text"
            value={inputValue}
            onChange={onInputChange}
            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && onSendMessage()}
            placeholder={activeChat ? `Ask anything about this document...` : 'Upload a document to start'}
            disabled={isAnswering || !activeChat}
            className="w-full py-4 pl-5 pr-12 border border-white/10 rounded-2xl text-sm outline-none bg-white/5 text-white transition-all duration-300 placeholder:text-gray-500 focus:border-orange-500/50 focus:bg-white/10 focus:shadow-lg focus:shadow-orange-500/10 disabled:opacity-50 disabled:cursor-not-allowed hover:not-disabled:border-white/20"
          />
          <div className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-gray-500">
            {inputValue.length > 0 && `${inputValue.length} chars`}
          </div>
        </div>
        <button
          onClick={onSendMessage}
          disabled={isAnswering || !activeChat || !inputValue.trim()}
          className="group relative px-6 py-4 rounded-2xl font-medium transition-all duration-300 flex items-center justify-center gap-2 overflow-hidden
            disabled:opacity-50 disabled:cursor-not-allowed
            enabled:bg-gradient-to-r enabled:from-orange-500 enabled:to-amber-500 enabled:hover:from-orange-500 enabled:hover:to-amber-500 enabled:shadow-lg enabled:shadow-orange-500/30 enabled:hover:-translate-y-0.5 enabled:active:translate-y-0
            border border-white/10"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-orange-500/0 via-white/25 to-amber-400/0 translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-1000"></div>
          <span className="relative flex items-center gap-2 text-white">
            {isAnswering ? (
              <Spinner />
            ) : (
              <>
                <span>Send</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </>
            )}
          </span>
        </button>
      </div>
    </aside>
  );
};

export default ChatPanel;
