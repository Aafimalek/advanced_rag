import { useState } from 'react';

export default function ApiKeySettings({ apiKey, onApiKeyChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [newApiKey, setNewApiKey] = useState('');
  const [error, setError] = useState('');
  const [isValidating, setIsValidating] = useState(false);

  const maskApiKey = (key) => {
    if (!key) return '';
    return `${key.substring(0, 8)}${'•'.repeat(20)}${key.substring(key.length - 4)}`;
  };

  const handleUpdateKey = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!newApiKey.trim()) {
      setError('Please enter your API key');
      return;
    }

    if (!newApiKey.startsWith('AIzaSy')) {
      setError('Invalid API key format. Google Gemini API keys start with "AIzaSy"');
      return;
    }

    setIsValidating(true);

    try {
      const response = await fetch('http://localhost:8000/validate-api-key', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': newApiKey
        }
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Invalid API key');
      }

      localStorage.setItem('gemini_api_key', newApiKey);
      onApiKeyChange(newApiKey);
      setNewApiKey('');
      setIsOpen(false);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to validate API key. Please check and try again.');
    } finally {
      setIsValidating(false);
    }
  };

  const handleRemoveKey = () => {
    if (confirm('Are you sure you want to remove your API key? You will need to enter it again to use the app.')) {
      localStorage.removeItem('gemini_api_key');
      onApiKeyChange(null);
      setIsOpen(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="p-2.5 bg-[#0f0f1e]/50 border border-[#ff6b35]/30 rounded-xl text-gray-300 hover:text-white hover:border-[#ff6b35] transition-all"
        title="API Key Settings"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
        </svg>
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setIsOpen(false)}>
          <div className="relative w-full max-w-md mx-4 bg-gradient-to-br from-[#1a1a2e] to-[#16213e] border border-[#ff6b35]/30 rounded-2xl shadow-2xl p-8 animate-slideUp" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white">API Key Settings</h3>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Current API Key */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Current API Key
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={maskApiKey(apiKey)}
                  readOnly
                  className="flex-1 px-4 py-2.5 bg-[#0f0f1e]/50 border border-[#ff6b35]/20 rounded-xl text-gray-400 text-sm"
                />
                <button
                  onClick={handleRemoveKey}
                  className="px-4 py-2.5 bg-red-500/20 border border-red-500/30 text-red-400 hover:bg-red-500/30 rounded-xl transition-all text-sm font-medium"
                  title="Remove API key"
                >
                  Remove
                </button>
              </div>
            </div>

            {/* Update API Key Form */}
            <form onSubmit={handleUpdateKey} className="space-y-4">
              <div>
                <label htmlFor="newApiKey" className="block text-sm font-medium text-gray-300 mb-2">
                  Update API Key
                </label>
                <div className="relative">
                  <input
                    type={showKey ? "text" : "password"}
                    id="newApiKey"
                    value={newApiKey}
                    onChange={(e) => setNewApiKey(e.target.value)}
                    placeholder="Enter new API key..."
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
                  'Update API Key'
                )}
              </button>
            </form>

            {/* Info */}
            <div className="mt-6 p-4 bg-[#ff6b35]/10 border border-[#ff6b35]/30 rounded-xl">
              <p className="text-xs text-gray-300">
                <strong className="text-[#ff6b35]">Note:</strong> Your API key is stored locally in your browser and is never saved on our servers.
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

