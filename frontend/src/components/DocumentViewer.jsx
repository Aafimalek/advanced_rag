import React, { useState, useEffect, useRef } from 'react';
import * as XLSX from 'xlsx';
import Papa from 'papaparse';
import mammoth from 'mammoth';

// Helper function to get file type label
const getFileTypeLabel = (filename) => {
  if (!filename) return 'Document';
  const ext = filename.split('.').pop()?.toLowerCase();
  const labels = {
    'pdf': 'PDF Document',
    'docx': 'Word Document',
    'doc': 'Word Document',
    'csv': 'CSV File',
    'xlsx': 'Excel Spreadsheet',
    'xls': 'Excel Spreadsheet'
  };
  return labels[ext] || 'Document';
};

// Helper function to get file extension
const getFileExtension = (filename) => {
  if (!filename) return '';
  return filename.split('.').pop()?.toLowerCase() || '';
};

const DocumentViewer = ({ document }) => {
  const [fileUrl, setFileUrl] = useState(null);
  const [fileBlob, setFileBlob] = useState(null);
  const [error, setError] = useState(null);
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeSheet, setActiveSheet] = useState(null);
  const docxContainerRef = useRef(null);
  
  console.log('DocumentViewer received document:', document);

  useEffect(() => {
    // Clean up the object URL when the component unmounts or the document changes
    return () => {
      if (fileUrl && fileUrl.startsWith('blob:')) {
        URL.revokeObjectURL(fileUrl);
      }
    };
  }, [fileUrl]);

  useEffect(() => {
    if (document) {
      setError(null);
      setLoading(true);
      setContent(null);
      const fetchDocument = async () => {
        try {
          const response = await fetch(`http://127.0.0.1:8000/documents/${document.id}/file`);

          if (!response.ok) {
            throw new Error(`Failed to fetch document: ${response.status} ${response.statusText}`);
          }

          const blob = await response.blob();
          const objectUrl = URL.createObjectURL(blob);
          setFileUrl(objectUrl);
          setFileBlob(blob);
          
          // Process file based on extension
          const ext = getFileExtension(document.name);
          await processFile(blob, ext);
        } catch (err) {
          console.error('Error fetching document:', err);
          setError('Could not load document. Please check the console for details.');
          setFileUrl(null);
          setFileBlob(null);
        } finally {
          setLoading(false);
        }
      };

      fetchDocument();
    } else {
      setFileUrl(null);
      setFileBlob(null);
      setContent(null);
      setLoading(false);
    }
  }, [document]);

  const processFile = async (blob, ext) => {
    try {
      if (ext === 'csv') {
        const text = await blob.text();
        Papa.parse(text, {
          header: true,
          skipEmptyLines: true,
          complete: (results) => {
            setContent({ type: 'csv', data: results.data, headers: results.meta.fields || [] });
          },
          error: (error) => {
            console.error('CSV parsing error:', error);
            setContent({ type: 'error', message: 'Failed to parse CSV file' });
          }
        });
      } else if (ext === 'xlsx' || ext === 'xls') {
        const arrayBuffer = await blob.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer, { type: 'array' });
        const sheets = {};
        
        workbook.SheetNames.forEach((sheetName) => {
          const worksheet = workbook.Sheets[sheetName];
          const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
          sheets[sheetName] = jsonData;
        });
        
        setContent({ type: 'excel', sheets, sheetNames: workbook.SheetNames });
        // Set first sheet as active
        if (workbook.SheetNames.length > 0) {
          setActiveSheet(workbook.SheetNames[0]);
        }
      } else if (ext === 'docx') {
        const arrayBuffer = await blob.arrayBuffer();
        const result = await mammoth.convertToHtml({ arrayBuffer });
        setContent({ type: 'docx', html: result.value });
        if (result.messages.length > 0) {
          console.warn('DOCX conversion warnings:', result.messages);
        }
      } else if (ext === 'pdf') {
        // PDF will be handled by iframe
        setContent({ type: 'pdf' });
      } else {
        // DOC and other unsupported formats
        setContent({ type: 'unsupported' });
      }
    } catch (err) {
      console.error('Error processing file:', err);
      setContent({ type: 'error', message: err.message });
    }
  };

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

  const downloadUrl = `http://127.0.0.1:8000/documents/${document.id}/file`;
  const ext = getFileExtension(document.name);

  const renderContent = () => {
    if (loading) {
      return (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
            <p className="text-gray-500">Loading document...</p>
          </div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center">
          <p className="text-red-400 font-semibold">Error</p>
          <p className="text-gray-400 text-sm">{error}</p>
        </div>
      );
    }

    if (!content) {
      return (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-gray-500">Loading...</p>
        </div>
      );
    }

    // PDF - use iframe
    if (content.type === 'pdf' && fileUrl) {
      return (
        <iframe
          src={`${fileUrl}#view=FitH`}
          title={document.name}
          className="absolute inset-0 w-full h-full border-0"
        />
      );
    }

    // DOCX - render HTML
    if (content.type === 'docx') {
      return (
        <div className="absolute inset-0 overflow-auto p-6 bg-white">
          <div 
            ref={docxContainerRef}
            className="max-w-4xl mx-auto prose prose-sm"
            dangerouslySetInnerHTML={{ __html: content.html }}
            style={{
              color: '#1f2937',
              fontFamily: 'Georgia, serif',
              lineHeight: '1.6'
            }}
          />
        </div>
      );
    }

    // CSV - render as table
    if (content.type === 'csv') {
      return (
        <div className="absolute inset-0 overflow-auto p-6">
          <div className="max-w-full">
            <table className="min-w-full border-collapse border border-gray-700 bg-[#1a1625]">
              <thead>
                <tr>
                  {content.headers.map((header, idx) => (
                    <th key={idx} className="border border-gray-600 px-4 py-2 text-left text-white font-semibold bg-[#241e30]">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {content.data.slice(0, 1000).map((row, rowIdx) => (
                  <tr key={rowIdx} className="hover:bg-[#241e30]">
                    {content.headers.map((header, colIdx) => (
                      <td key={colIdx} className="border border-gray-700 px-4 py-2 text-gray-300">
                        {row[header] || ''}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {content.data.length > 1000 && (
              <p className="text-gray-400 text-sm mt-4">
                Showing first 1000 rows of {content.data.length} total rows
              </p>
            )}
          </div>
        </div>
      );
    }

    // Excel - render sheets as tables
    if (content.type === 'excel') {
      const currentSheet = activeSheet || content.sheetNames[0];
      
      return (
        <div className="absolute inset-0 flex flex-col overflow-hidden">
          {content.sheetNames.length > 1 && (
            <div className="flex gap-2 p-4 border-b border-gray-700 bg-[#1a1625] overflow-x-auto">
              {content.sheetNames.map((sheetName) => (
                <button
                  key={sheetName}
                  onClick={() => setActiveSheet(sheetName)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    currentSheet === sheetName
                      ? 'bg-orange-500 text-white'
                      : 'bg-[#241e30] text-gray-300 hover:bg-[#2d2640]'
                  }`}
                >
                  {sheetName}
                </button>
              ))}
            </div>
          )}
          <div className="flex-1 overflow-auto p-6">
            <div className="max-w-full">
              <h3 className="text-white font-semibold mb-4">{currentSheet}</h3>
              <table className="min-w-full border-collapse border border-gray-700 bg-[#1a1625]">
                <tbody>
                  {content.sheets[currentSheet]?.slice(0, 1000).map((row, rowIdx) => (
                    <tr key={rowIdx} className="hover:bg-[#241e30]">
                      {row.map((cell, colIdx) => (
                        <td key={colIdx} className="border border-gray-700 px-4 py-2 text-gray-300">
                          {cell || ''}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {(content.sheets[currentSheet]?.length || 0) > 1000 && (
                <p className="text-gray-400 text-sm mt-4">
                  Showing first 1000 rows of {content.sheets[currentSheet].length} total rows
                </p>
              )}
            </div>
          </div>
        </div>
      );
    }

    // Unsupported formats (DOC, etc.)
    if (content.type === 'unsupported' || content.type === 'error') {
      return (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center">
          <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-orange-500/10 to-amber-500/10 flex items-center justify-center border border-orange-500/20 mb-4">
            <svg className="w-12 h-12 text-orange-500/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">{document.name}</h3>
          <p className="text-gray-400 text-sm mb-6">
            {content.type === 'error' 
              ? content.message 
              : 'This file type cannot be previewed in the browser. Click the download button to open it.'}
          </p>
          <a
            href={downloadUrl}
            download={document.name}
            className="px-6 py-3 bg-gradient-to-br from-orange-500 to-amber-500 text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-orange-500/30 transition-all"
          >
            Download File
          </a>
        </div>
      );
    }

    return null;
  };

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
            {getFileTypeLabel(document.name)}
          </p>
        </div>
        <a 
          href={downloadUrl} 
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

      {/* Document Viewer */}
      <div className="flex-1 relative overflow-hidden bg-[#241e30]">
        {renderContent()}
      </div>
    </div>
  );
};

export default DocumentViewer;
