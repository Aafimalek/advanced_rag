import React from 'react';

const Toast = ({ message, type = 'success', onClose }) => (
  <div className={`
    glass-effect rounded-2xl px-6 py-4 mb-3 flex items-start gap-4
    min-w-[320px] max-w-[420px] shadow-2xl border
    ${type === 'success' 
      ? 'border-green-500/30 bg-green-500/10' 
      : 'border-red-500/30 bg-red-500/10'
    }
    animate-slide-in-right
  `}>
    <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
      type === 'success' 
        ? 'bg-green-500/20 border border-green-500/30' 
        : 'bg-red-500/20 border border-red-500/30'
    }`}>
      {type === 'success' ? (
        <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      )}
    </div>
    <div className="flex-1">
      <p className={`m-0 text-sm font-medium ${type === 'success' ? 'text-green-100' : 'text-red-100'}`}>
        {type === 'success' ? 'Success' : 'Error'}
      </p>
      <p className="m-0 text-sm text-gray-300 mt-1">{message}</p>
    </div>
    <button 
      onClick={onClose}
      className="text-gray-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/10 flex-shrink-0"
    >
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
);

export default Toast;
