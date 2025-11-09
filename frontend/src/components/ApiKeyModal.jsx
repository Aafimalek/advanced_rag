import { useState, useEffect } from 'react';

export default function ApiKeyModal({ onApiKeySet }) {
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [error, setError] = useState('');
  const [isValidating, setIsValidating] = useState(false);

  useEffect(() => {
    // Check if API key exists in localStorage
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey) {
      onApiKeySet(savedKey);
    }
  }, [onApiKeySet]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!apiKey.trim()) {
      setError('Please enter your API key');
      return;
    }

    if (!apiKey.startsWith('AIzaSy')) {
      setError('Invalid API key format. Google Gemini API keys start with "AIzaSy"');
      return;
    }

    setIsValidating(true);

    try {
      // Validate the API key by making a test request to backend
      const response = await fetch('http://localhost:8000/validate-api-key', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        }
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Invalid API key');
      }

      // Save to localStorage
      localStorage.setItem('gemini_api_key', apiKey);
      onApiKeySet(apiKey);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to validate API key. Please check and try again.');
    } finally {
      setIsValidating(false);
    }
  };

  const handleClearKey = () => {
    localStorage.removeItem('gemini_api_key');
    setApiKey('');
    onApiKeySet(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-md mx-4 bg-gradient-to-br from-[#1a1a2e] to-[#16213e] border border-[#ff6b35]/30 rounded-2xl shadow-2xl p-8 animate-slideUp">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 mb-4 bg-gradient-to-br from-[#ff6b35] to-[#f7931e] rounded-full">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">
            Welcome to RAG Chat! 🚀
          </h2>
          <p className="text-gray-300 text-sm">
            To get started, please enter your Google Gemini API key
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="apiKey" className="block text-sm font-medium text-gray-300 mb-2">
              Google Gemini API Key
            </label>
            <div className="relative">
              <input
                type={showKey ? "text" : "password"}
                id="apiKey"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="AIzaSy..."
                className="w-full px-4 py-3 bg-[#0f0f1e]/50 border border-[#ff6b35]/30 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-[#ff6b35] focus:ring-2 focus:ring-[#ff6b35]/20 transition-all"
                disabled={isValidating}
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
              >
                {showKey ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                )}
              </button>
            </div>
            
            {error && (
              <p className="mt-2 text-sm text-red-400 flex items-center">
                <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                {error}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isValidating}
            className="w-full bg-gradient-to-r from-[#ff6b35] to-[#f7931e] text-white font-medium py-3 rounded-xl hover:shadow-lg hover:shadow-[#ff6b35]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {isValidating ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Validating...
              </>
            ) : (
              'Continue'
            )}
          </button>
        </form>

        {/* Info */}
        <div className="mt-6 p-4 bg-[#ff6b35]/10 border border-[#ff6b35]/30 rounded-xl">
          <p className="text-xs text-gray-300 leading-relaxed">
            <strong className="text-[#ff6b35]">🔒 Your API key is safe:</strong><br />
            • Stored only in your browser (localStorage)<br />
            • Never stored on our servers<br />
            • Sent securely with each request<br />
            • <a 
                href="https://aistudio.google.com/app/apikey" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-[#ff6b35] hover:underline"
              >
                Get your free API key here →
              </a>
          </p>
        </div>
      </div>
    </div>
  );
}

