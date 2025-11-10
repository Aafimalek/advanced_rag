import React, { useState, useEffect, useRef } from 'react';

const ApiKeySettings = ({ apiKey, onApiKeyChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const handleClearKey = () => {
    localStorage.removeItem('gemini_api_key');
    onApiKeyChange(null);
    setIsOpen(false);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  if (!apiKey) {
    return null; // Don't show anything if there is no key
  }

  const maskedKey = `${apiKey.substring(0, 4)}...${apiKey.substring(apiKey.length - 4)}`;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 p-2.5 rounded-xl hover:bg-gradient-to-br hover:from-orange-500/10 hover:to-amber-500/10 transition-all duration-300 border border-transparent hover:border-orange-500/20"
        title="API Key Settings"
      >
        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
        </svg>
        <span className="text-sm text-gray-300 font-mono hidden md:inline">{maskedKey}</span>
      </button>

      {isOpen && (
        <div className="absolute top-full right-0 mt-2 w-64 bg-gradient-to-br from-[#2d2640] to-[#1a1625] border border-white/10 rounded-xl shadow-2xl z-[200] p-4 animate-fade-in-up">
          <p className="text-sm font-medium text-white mb-2">API Key Settings</p>
          <p className="text-xs text-gray-400 mb-4">
            The API key is currently active.
          </p>
          <button
            onClick={handleClearKey}
            className="w-full text-left px-4 py-2 text-sm text-red-400 rounded-lg hover:bg-red-500/10 transition-colors"
          >
            Clear API Key & Reset
          </button>
        </div>
      )}
    </div>
  );
};

export default ApiKeySettings;

