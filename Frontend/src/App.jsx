import React, { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Upload } from 'lucide-react';

/**
 * Defines custom components for ReactMarkdown rendering to apply Tailwind styles.
 */
const markdownComponents = {
  h2: ({ node, ...props }) => (
    <h2
      className="text-lg font-bold text-slate-100 mt-6 mb-2 pt-2 border-t border-slate-700/50 first:mt-0 first:pt-0 first:border-t-0"
      {...props}
    />
  ),
  ul: ({ node, ...props }) => (
    <ul
      className="list-disc pl-5 space-y-1 text-slate-300"
      {...props}
    />
  ),
  li: ({ node, ...props }) => (
    <li
      className="text-sm md:text-base leading-relaxed"
      {...props}
    />
  ),
  strong: ({ node, ...props }) => (
    <strong
      className="text-slate-200 font-semibold"
      {...props}
    />
  ),
  p: ({ node, ...props }) => (
    <p
      className="mt-2 mb-2"
      {...props}
    />
  )
};

/**
 * Renders an individual chat message bubble.
 */
const AuditMessage = ({ message, isLoading, nextMessageId }) => {
  const isUser = message.sender === 'user';
  const isAI = message.sender === 'ai';

  const baseClasses = `p-3 md:p-4 rounded-lg max-w-[85%] break-words text-sm md:text-base`;
  const senderClasses = isUser
    ? 'bg-slate-700 text-slate-100 ml-auto border border-slate-600'
    : isAI
      ? 'bg-slate-800 text-slate-200 border border-slate-700'
      : 'bg-slate-800/50 text-slate-300 border-l-4 border-slate-600';

  if (isLoading && message.id === nextMessageId.current - 1) {
    return (
      <div className="p-4 rounded-lg bg-slate-800 text-slate-200 border border-slate-700 w-fit">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse delay-150"></div>
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse delay-300"></div>
          <span className="text-sm">Thinking...</span>
        </div>
      </div>
    );
  }

  return (
    <div key={message.id} className={`${baseClasses} ${senderClasses}`}>
      {isAI ? (
        <ReactMarkdown components={markdownComponents}>{message.text}</ReactMarkdown>
      ) : (
        message.text
      )}
    </div>
  );
};

const FinancialAuditUI = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [csvFile, setCsvFile] = useState(null);
  const [pdfFile, setPdfFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [sessionId, setSessionId] = useState(null); // Track active audit session

  const fileInputRef = useRef(null);
  const nextMessageId = useRef(0);

  const addMessage = (text, sender) => {
    const newId = nextMessageId.current++;
    setMessages(prev => [...prev, { text, sender, id: newId }]);
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const fileName = file.name;
    const fileExtension = fileName.split('.').pop().toLowerCase();

    let fileType;
    if (fileExtension === 'csv') {
      fileType = 'csv';
    } else if (fileExtension === 'pdf') {
      fileType = 'pdf';
    } else {
      fileInputRef.current.value = null;
      showCustomMessageBox('File Upload Error', 'Invalid file type. Please upload a CSV or PDF file.');
      return;
    }

    const maxSize = 500 * 1024 * 1024;
    if (file.size > maxSize) {
      showCustomMessageBox('File Upload Error', 'File too large (max 500MB).');
      event.target.value = null;
      return;
    }

    setSessionId(null); // Reset session on new file upload to force new audit

    if (fileType === 'csv') {
      setCsvFile(file);
    } else {
      setPdfFile(file);
    }

    event.target.value = null;
    addMessage(`📁 Uploaded: ${fileName}`, 'user');
    addMessage('🔄 Processing document... Analysis will appear in the results panel.', 'system');
  };

  const showCustomMessageBox = (title, message) => {
    const messageBox = document.createElement('div');
    messageBox.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    messageBox.innerHTML = `
        <div class="bg-slate-800 p-6 rounded-lg shadow-xl border border-slate-700 text-slate-200">
          <h3 class="text-lg font-semibold mb-3">${title}</h3>
          <p>${message}</p>
          <button id="closeMessageBox" class="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-white">Close</button>
        </div>
      `;
    document.body.appendChild(messageBox);
    document.getElementById('closeMessageBox').onclick = () => document.body.removeChild(messageBox);
  }

  const clearChat = () => {
    setMessages([]);
    setCsvFile(null);
    setPdfFile(null);
    setSessionId(null); // Reset session
    nextMessageId.current = 0;
    if (fileInputRef.current) fileInputRef.current.value = null;
  };

  const sendMessage = async () => {
    if (inputValue.trim() === '' || isLoading) return;

    const userMessage = inputValue;
    addMessage(userMessage, 'user');
    setInputValue('');
    setIsLoading(true);

    const isNewAudit = csvFile || pdfFile || !sessionId; // Reactive routing

    try {
      const apiUrl = import.meta.env.VITE_API_URL;
      let response;
      let data;

      if (isNewAudit) {
        const formData = new FormData();
        formData.append('message', userMessage);
        if (csvFile) formData.append('csv_file', csvFile);
        if (pdfFile) formData.append('pdf_file', pdfFile);

        response = await fetch(`${apiUrl}/audit`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Audit failed');
        }

        data = await response.json();

        if (data.session_id) {
          setSessionId(data.session_id); // Save session ID for follow-ups
          addMessage(data.response, 'ai'); // Summary report
          addMessage(data.initial_chat_response, 'ai'); // Initial conversational reply
          setCsvFile(null);
          setPdfFile(null);
        } else {
          addMessage(data.response, 'ai');
        }

      } else {
        // Follow-up question for an existing Stateful Session
        response = await fetch(`${apiUrl}/chat/${sessionId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userMessage }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          if (response.status === 404) setSessionId(null);
          throw new Error(errorData.detail || 'Chat session lost');
        }

        data = await response.json();
        addMessage(data.response, 'ai');
      }

    } catch (error) {
      addMessage(`❌ Error: ${error.message}`, 'system');
    } finally {
      setIsLoading(false);
    }
  };

  const suggestedPrompt = (prompt) => {
    setInputValue(prompt);
    setActiveTab('chat');
    setTimeout(() => sendMessage(), 100);
  };

  const handleKeyDown = (e) => { // Updated from handleKeyPress
    if (e.key === 'Enter') {
      sendMessage();
    }
  };

  const MobileBottomNav = () => (
    <div className="md:hidden fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-700 p-2 flex justify-around z-50 pb-safe">
      <button
        onClick={() => setActiveTab('chat')}
        className={`flex-1 p-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'chat' ? 'bg-slate-700 text-white' : 'text-slate-400'}`}
      >
        💬 Chat
      </button>
      <div className="w-4"></div>
      <button
        onClick={() => setActiveTab('dashboard')}
        className={`flex-1 p-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'dashboard' ? 'bg-slate-700 text-white' : 'text-slate-400'}`}
      >
        📋 Dashboard
      </button>
    </div>
  );

  const FileStatusDisplay = () => (
    (csvFile || pdfFile) && (
      <div className="mb-4 space-y-2">
        {csvFile && (
          <div className="flex items-center justify-between bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-2">
            <div className="flex items-center space-x-3">
              <span className="text-emerald-400">📊</span>
              <p className="text-emerald-400 font-medium text-xs md:text-sm truncate max-w-[200px]">{csvFile.name}</p>
            </div>
            <button onClick={() => { setCsvFile(null); }} className="text-emerald-400 hover:text-red-400 px-2">✕</button>
          </div>
        )}
        {pdfFile && (
          <div className="flex items-center justify-between bg-red-500/10 border border-red-500/30 rounded-lg p-2">
            <div className="flex items-center space-x-3">
              <span className="text-red-400">📄</span>
              <p className="text-red-400 font-medium text-xs md:text-sm truncate max-w-[200px]">{pdfFile.name}</p>
            </div>
            <button onClick={() => { setPdfFile(null); }} className="text-red-400 hover:text-red-300 px-2">✕</button>
          </div>
        )}
      </div>
    )
  );

  return (
    <div className="flex flex-col md:flex-row h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 overflow-hidden font-sans">
      <div className={`flex-1 flex flex-col h-full ${activeTab === 'dashboard' ? 'hidden md:flex' : 'flex'}`}>
        <div className="flex-1 overflow-y-auto p-4 md:p-6 bg-slate-900/50 custom-scrollbar pb-20 md:pb-6">
          {messages.length === 0 ? (
            <div className="text-center py-16 text-slate-300">
              <div className="text-5xl mb-6 text-slate-400">💬</div>
              <div className="text-xl font-semibold mb-3 text-slate-200">Welcome to Financial Audit AI</div>
              <div className="text-slate-400 leading-relaxed max-w-sm mx-auto text-sm md:text-base">
                Upload documents and start conversing to receive audit insights.
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <AuditMessage
                  key={message.id}
                  message={message}
                  isLoading={isLoading}
                  nextMessageId={nextMessageId}
                />
              ))}
              {isLoading && (
                // This is the dedicated thinking indicator for when API call is pending
                <div className="p-4 rounded-lg bg-slate-800 text-slate-200 border border-slate-700 w-fit">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse delay-150"></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse delay-300"></div>
                    <span className="text-sm">Thinking...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="p-4 md:p-6 bg-slate-800/30 border-t border-slate-700/30 mb-14 md:mb-0">
          <FileStatusDisplay />
          {messages.length > 0 && (
            <div className="mb-2 flex justify-center hidden md:flex">
              <button onClick={clearChat} className="text-xs text-slate-400 hover:text-red-400 flex items-center space-x-1">
                <span>🗑️ Clear Chat</span>
              </button>
            </div>
          )}

          <div className="flex items-center bg-slate-700/50 rounded-lg p-2 md:p-3 border border-slate-600/50">
            <input
              type="file"
              accept=".csv, .pdf"
              onChange={handleFileUpload}
              ref={fileInputRef}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-2 bg-slate-600/70 hover:bg-slate-600/90 text-slate-300 rounded flex items-center justify-center transition-all duration-200 mr-2 md:mr-3"
              title="Upload CSV or PDF"
              disabled={isLoading}
            >
              <Upload size={20} />
            </button>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown} // Reactive Keyboard Event
              className="flex-1 bg-transparent outline-none text-slate-200 placeholder-slate-400 text-sm md:text-base min-w-0"
              placeholder={sessionId ? "Ask a follow-up question about the audit..." : "Ask a question or upload documents..."}
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              className="ml-2 p-2 bg-slate-600 text-slate-200 rounded hover:bg-slate-500"
              disabled={isLoading}
            >
              ➤
            </button>
          </div>
        </div>
      </div>

      <div className={`w-full md:w-1/2 bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 flex flex-col border-l border-slate-700/30 h-full ${activeTab === 'chat' ? 'hidden md:flex' : 'flex'}`}>
        <div className="bg-slate-800/80 p-4 border-b border-slate-600/30 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-100">📋 Audit Dashboard</h2>
              <p className="text-slate-300 text-xs mt-1">Real-time analysis</p>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
              <span className="text-xs text-slate-300">Live</span>
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 md:p-8 overflow-y-auto custom-scrollbar pb-20 md:pb-6">
          <div className="grid grid-cols-2 gap-3 md:gap-4 mb-6 md:mb-8">
            <div className="bg-slate-800/60 p-3 md:p-4 rounded-xl border border-slate-700/50">
              <p className="text-slate-400 text-[10px] md:text-xs font-medium uppercase">Documents</p>
              <p className="text-xl md:text-2xl font-bold text-slate-100">{(csvFile ? 1 : 0) + (pdfFile ? 1 : 0)}</p>
            </div>
            <div className="bg-slate-800/60 p-3 md:p-4 rounded-xl border border-slate-700/50">
              <p className="text-slate-400 text-[10px] md:text-xs font-medium uppercase">Queries</p>
              <p className="text-xl md:text-2xl font-bold text-slate-100">{messages.filter(m => m.sender === 'user').length}</p>
            </div>
          </div>

          <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4 md:p-6 mb-6">
            <h3 className="font-semibold text-slate-100 mb-4 text-sm md:text-base">⚡ Quick Actions</h3>
            <div className="space-y-2 md:space-y-3">
              {[
                { icon: '🔍', text: 'Analyze invoice discrepancies', prompt: 'Analyze invoice discrepancies' },
                { icon: '⚠️', text: 'Check for duplicates', prompt: 'Check for duplicate transactions' },
                { icon: '✅', text: 'Compliance Check', prompt: 'Validate expense compliance' },
                { icon: '📊', text: 'Generate Report', prompt: 'Generate audit summary' }
              ].map((item, index) => (
                <button
                  key={index}
                  onClick={() => suggestedPrompt(item.prompt)}
                  className="w-full text-left p-3 bg-slate-700/30 hover:bg-slate-700/50 rounded-lg border border-slate-600/30 flex items-center space-x-3 transition-colors"
                  disabled={isLoading}
                >
                  <span className="text-lg">{item.icon}</span>
                  <span className="text-slate-200 text-sm font-medium">{item.text}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4 md:p-6">
            <h3 className="font-semibold text-slate-100 mb-4 text-sm md:text-base">System Status</h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-slate-300">Engine</span>
                <span className={`px-2 py-0.5 rounded-full text-xs ${isLoading ? 'bg-yellow-500/20 text-yellow-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                  {isLoading ? 'Processing' : 'Ready'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-300">Chat Session</span>
                <span className={`px-2 py-0.5 rounded-full text-xs ${sessionId ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-500/20 text-slate-400'}`}>
                  {sessionId ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <MobileBottomNav />
      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #1e293b; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #475569; border-radius: 10px; }
        .pb-safe { padding-bottom: env(safe-area-inset-bottom, 20px); }
      `}</style>
    </div>
  );
};

export default FinancialAuditUI;