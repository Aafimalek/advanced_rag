import React from 'react';

const DocumentViewer = ({ document }) => {
  console.log('DocumentViewer received document:', document);

  if (!document) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center glass-effect p-8 gap-4">
        <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-orange-500/10 to-amber-500/10 flex items-center justify-center border border-orange-500/20">
          <svg className="w-12 h-12 text-orange-500/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <div className="text-center">
          <p className="text-gray-300 text-sm font-medium mb-2">No Document Available</p>
          <p className="text-gray-500 text-xs max-w-sm">
            {document === null 
              ? 'The document for this chat could not be found. It may have been deleted.' 
              : 'Select a chat to view its associated document'}
          </p>
        </div>
      </div>
    );
  }

  const fileUrl = `http://127.0.0.1:8000/documents/${document.id}/file`;

  return (
    <div className="basis-[45%] flex flex-col glass-effect overflow-hidden border-r border-white/5">
      {/* Header */}
      <div className="p-5 border-b border-white/5 glass-effect flex items-center gap-3 z-10">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-orange-500/20 to-amber-500/20 flex items-center justify-center border border-orange-500/30">
          <svg className="w-5 h-5 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <div className="flex-1 flex flex-col">
          <h2 className="text-sm font-semibold text-white truncate" title={document.name}>
            {document.name}
          </h2>
          <p className="text-xs text-gray-400">
            PDF Document
          </p>
        </div>
        <a 
          href={fileUrl} 
          target="_blank" 
          rel="noopener noreferrer"
          className="p-2 rounded-lg border border-white/10 hover:bg-white/10 hover:border-orange-500/30 transition-all"
          title="Open in new tab"
        >
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      </div>

      {/* PDF Viewer */}
      <div className="flex-1 relative overflow-hidden">
        <iframe
          src={`${fileUrl}#view=FitH`}
          title={document.name}
          className="absolute inset-0 w-full h-full border-0"
          style={{ background: '#1a1a2e' }}
        />
      </div>
    </div>
  );
};

export default DocumentViewer;
