import React, { useState } from 'react';

const ApiKeyModal = ({ onApiKeySet }) => {
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleValidateAndSet = async () => {
    if (!apiKeyInput.trim()) {
      setError('API key cannot be empty.');
      return;
    }
    setError('');
    setIsLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/validate-api-key', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKeyInput,
        },
      });

      if (response.ok) {
        localStorage.setItem('gemini_api_key', apiKeyInput);
        onApiKeySet(apiKeyInput);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to validate API key. Please check the key and your connection.');
      }
    } catch (err) {
      console.error('Validation error:', err);
      setError('An error occurred. Is the backend server running?');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[200] flex items-center justify-center">
      <div className="bg-gradient-to-br from-[#2d2640] to-[#1a1625] border border-white/10 rounded-2xl shadow-2xl p-8 max-w-lg w-full text-center animate-fade-in-up">
        <h2 className="text-2xl font-bold gradient-text mb-4">Enter Your Gemini API Key</h2>
        <p className="text-[#c4b5d6] mb-6">
          To use this application, you need a Google Gemini API key. Your key is stored securely in your browser's local storage and is never sent anywhere else.
        </p>
        <div className="flex flex-col gap-4">
          <input
            type="password"
            value={apiKeyInput}
            onChange={(e) => setApiKeyInput(e.target.value)}
            placeholder="Enter your API key here..."
            className="bg-[#1a1625]/80 border border-[#4a4062] rounded-xl px-4 py-3 text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-[#ff6b35] transition-all"
            onKeyPress={(e) => e.key === 'Enter' && handleValidateAndSet()}
          />
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button
            onClick={handleValidateAndSet}
            disabled={isLoading}
            className={`w-full bg-gradient-to-r from-[#ff6b35] to-[#ff8c42] text-white px-6 py-3 rounded-xl font-semibold transition-all duration-300
              ${isLoading ? 'opacity-70 cursor-not-allowed' : 'hover:shadow-lg hover:shadow-[#ff6b35]/40 hover:-translate-y-0.5'}`}
          >
            {isLoading ? 'Validating...' : 'Save and Continue'}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-6">
          You can get your API key from the{' '}
          <a
            href="https://aistudio.google.com/app/apikey"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#ff8c42] hover:underline"
          >
            Google AI Studio
          </a>.
        </p>
      </div>
    </div>
  );
};

export default ApiKeyModal;

