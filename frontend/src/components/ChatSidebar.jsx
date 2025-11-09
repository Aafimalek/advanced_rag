import React, { useState } from 'react';

const ChatSidebar = ({
  chats,
  activeChatId,
  onSelectChat,
  onDeleteChat,
  isSidebarOpen,
}) => {
  const [deletingChatId, setDeletingChatId] = useState(null);
  return (
    <aside
      className={`
        glass-effect border-r border-white/5 shadow-2xl flex flex-col transition-all duration-300 ease-in-out
        ${isSidebarOpen ? 'w-[320px]' : 'w-0'}
      `}
    >
      <div className="p-6 border-b border-white/5 flex items-center gap-3 overflow-hidden">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500/20 to-amber-500/20 flex items-center justify-center border border-orange-500/30">
          <svg className="w-4 h-4 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </div>
        <h2 className="m-0 text-sm font-semibold text-gray-200 tracking-wide whitespace-nowrap">
          Conversations
        </h2>
      </div>
      
      <ul className="list-none p-4 m-0 overflow-y-auto custom-scrollbar flex-1 space-y-2">
        {chats.length === 0 ? (
          <li className="py-16 px-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-orange-500/10 to-amber-500/10 flex items-center justify-center border border-orange-500/20">
              <svg className="w-8 h-8 text-orange-500/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
            </div>
            <p className="text-gray-400 text-sm leading-relaxed">Upload a document to start chatting</p>
          </li>
        ) : (
          chats.map((chat) => (
            <li
              key={chat.id}
              className={`group relative p-4 transition-all duration-300 flex items-start gap-3 rounded-xl overflow-hidden ${
                chat.id === activeChatId
                  ? 'bento-card border-orange-500/40 bg-gradient-to-br from-orange-500/10 to-amber-500/10 shadow-lg shadow-orange-500/10'
                  : 'bento-card hover:scale-[1.02]'
              }`}
            >
              <div 
                onClick={() => onSelectChat(chat.id)}
                className="flex items-start gap-3 flex-1 min-w-0 cursor-pointer"
              >
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-all ${
                  chat.id === activeChatId 
                    ? 'bg-gradient-to-br from-orange-500 to-amber-500 shadow-lg shadow-orange-500/30' 
                    : 'bg-gradient-to-br from-orange-500/20 to-amber-500/20 group-hover:from-orange-500/30 group-hover:to-amber-500/30'
                }`}>
                  <svg className={`w-5 h-5 ${chat.id === activeChatId ? 'text-white' : 'text-orange-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                </div>
                
                <div className="flex-1 min-w-0 flex flex-col gap-1.5">
                  <div className={`font-medium text-sm m-0 whitespace-nowrap overflow-hidden text-ellipsis ${
                    chat.id === activeChatId ? 'text-white' : 'text-gray-200 group-hover:text-white'
                  }`}>
                    {chat.title}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="whitespace-nowrap overflow-hidden text-ellipsis">
                      {new Date(chat.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Delete Button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (window.confirm(`Delete chat "${chat.title}"?\n\nThis will also delete the associated document if no other chats use it.`)) {
                    setDeletingChatId(chat.id);
                    onDeleteChat(chat.id);
                  }
                }}
                disabled={deletingChatId === chat.id}
                className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-red-500/20 border border-transparent hover:border-red-500/30 transition-all disabled:opacity-50"
                title="Delete chat"
              >
                {deletingChatId === chat.id ? (
                  <svg className="w-4 h-4 text-gray-400 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-gray-400 hover:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                )}
              </button>
              
              {chat.id === activeChatId && (
                <div className="absolute right-2 top-2">
                  <div className="w-2 h-2 rounded-full bg-orange-500 shadow-lg shadow-orange-500/50 animate-pulse"></div>
                </div>
              )}
            </li>
          ))
        )}
      </ul>
    </aside>
  );
};

export default ChatSidebar;

