import React, { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown'; // Import ReactMarkdown
import rehypeRaw from 'rehype-raw'; // Import rehype-raw for raw HTML support in markdown

// FinancialAuditUI component provides an interface for financial audit operations.
// It includes a chat interface for user interaction and a dashboard for displaying analysis status and quick actions.
const FinancialAuditUI = () => {
  // State to manage chat messages
  const [messages, setMessages] = useState([]);
  // State for the input field value in the chat
  const [inputValue, setInputValue] = useState('');
  // State to store information about the uploaded CSV file
  const [csvFile, setCsvFile] = useState(null);
  // State to store information about the uploaded PDF file
  const [pdfFile, setPdfFile] = useState(null);
  // State to manage loading indicator when waiting for AI response
  const [isLoading, setIsLoading] = useState(false);

  // Refs for file input elements to programmatically trigger clicks
  const csvInputRef = useRef(null);
  const pdfInputRef = useRef(null);

  /**
   * Handles file uploads for CSV and PDF types.
   * Performs basic file size validation (max 500MB) and updates the UI with upload status.
   * @param {Event} event - The file input change event.
   * @param {string} type - The type of file being uploaded ('csv' or 'pdf').
   */
  const handleFileUpload = (event, type) => {
    const file = event.target.files[0];
    if (!file) return; // If no file is selected, exit

    const maxSize = 500 * 1024 * 1024; // 500MB in bytes
    const fileName = file.name;

    // Check if the file size exceeds the maximum allowed size
    if (file.size > maxSize) {
      // Using a custom message box instead of alert() due to iframe restrictions
      const messageBox = document.createElement('div');
      messageBox.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
      messageBox.innerHTML = `
        <div class="bg-slate-800 p-6 rounded-lg shadow-xl border border-slate-700 text-slate-200">
          <h3 class="text-lg font-semibold mb-3">File Upload Error</h3>
          <p>File too large (max 500MB). Please select a smaller file.</p>
          <button id="closeMessageBox" class="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-white">Close</button>
        </div>
      `;
      document.body.appendChild(messageBox);
      document.getElementById('closeMessageBox').onclick = () => document.body.removeChild(messageBox);
      // Clear the file input value to allow re-uploading the same file after an error
      event.target.value = null; 
      return;
    }

    // Update state based on file type
    if (type === 'csv') {
      setCsvFile(file); // Store the actual file object, not just its name
    } else {
      setPdfFile(file); // Store the actual file object
    }

    // Add messages to the chat to indicate file upload and processing
    addMessage(`📁 Uploaded: ${fileName}`, 'user');
    addMessage('🔄 Processing document... Analysis will appear in the results panel.', 'system');
  };

  /**
   * Adds a new message to the chat interface.
   * @param {string} text - The content of the message.
   * @param {string} sender - The sender of the message ('user', 'ai', or 'system').
   */
  const addMessage = (text, sender) => {
    // Update messages state by adding the new message
    setMessages(prev => [...prev, { text, sender, id: Date.now() }]);
  };

  /**
   * Clears all messages from the chat interface.
   */
  const clearChat = () => {
    setMessages([]);
    setCsvFile(null); // Also clear uploaded files
    setPdfFile(null);
    if (csvInputRef.current) csvInputRef.current.value = null; // Clear file input visually
    if (pdfInputRef.current) pdfInputRef.current.value = null; // Clear file input visually
  };

  /**
   * Sends a user message to the backend API and handles the AI response.
   * Clears the input field and sets loading state.
   */
  const sendMessage = async () => {
    if (inputValue.trim() === '' || isLoading) { // Only send if input is not empty and not already loading
      return;
    }

    const userMessage = inputValue;
    addMessage(userMessage, 'user'); // Add user message to chat
    setInputValue(''); // Clear input field
    setIsLoading(true); // Set loading state

    try {
      const formData = new FormData();
      formData.append('message', userMessage);
      if (csvFile) {
        formData.append('csv_file', csvFile);
      }
      if (pdfFile) {
        formData.append('pdf_file', pdfFile);
      }

      const apiUrl = import.meta.env.VITE_API_URL;

      // Make a fetch call to the backend API
      const response = await fetch(`${apiUrl}/audit`, {
        method: 'POST',
        body: formData, // Send as FormData for file uploads
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP error! status: ${response.status}, detail: ${errorData.detail || 'Unknown error'}`);
      }

      const data = await response.json();
      addMessage(data.response, 'ai'); // Add AI response (markdown summary) to chat
    } catch (error) {
      console.error('Error sending message to backend:', error);
      addMessage(`❌ Error: Could not get a response from the audit engine. ${error.message}`, 'system');
    } finally {
      setIsLoading(false); // Clear loading state
    }
  };

  /**
   * Sets the input value to a suggested prompt and sends it.
   * @param {string} prompt - The suggested prompt text.
   */
  const suggestedPrompt = (prompt) => {
    setInputValue(prompt); // Set input value
    // Use a timeout to ensure inputValue state updates before sendMessage is called
    setTimeout(() => sendMessage(), 100); 
  };

  /**
   * Handles key press events in the input field.
   * Sends the message if the 'Enter' key is pressed.
   * @param {Event} e - The keyboard event.
   */
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      sendMessage();
    }
  };

  return (
    // Main container for the UI, using flexbox for layout and gradient background
    <div className="flex h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 overflow-hidden font-sans">
      {/* Left Side - Chat Interface */}
      <div className="flex-1 flex flex-col">
        {/* Chat messages display area */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-900/50 custom-scrollbar">
          {messages.length === 0 ? (
            // Welcome message when no messages are present
            <div className="text-center py-16 text-slate-300">
              <div className="text-5xl mb-6 text-slate-400">💬</div>
              <div className="text-xl font-semibold mb-3 text-slate-200">Welcome to Financial Audit AI</div>
              <div className="text-slate-400 leading-relaxed max-w-sm mx-auto">
                Upload your financial documents and start conversing to receive comprehensive audit insights and recommendations.
              </div>
            </div>
          ) : (
            // Display chat messages
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`p-4 rounded-lg max-w-4/5 break-words ${
                    message.sender === 'user'
                      ? 'bg-slate-700 text-slate-100 ml-auto border border-slate-600' // User message styling
                      : message.sender === 'ai'
                      ? 'bg-slate-800 text-slate-200 border border-slate-700' // AI message styling
                      : 'bg-slate-800/50 text-slate-300 border-l-4 border-slate-600' // System message styling
                  }`}
                >
                  {/* Conditionally render as Markdown if sender is 'ai', otherwise plain text */}
                  {message.sender === 'ai' ? (
                    <ReactMarkdown rehypePlugins={[rehypeRaw]}>{message.text}</ReactMarkdown>
                  ) : (
                    message.text
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="p-4 rounded-lg max-w-4/5 bg-slate-800 text-slate-200 border border-slate-700">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-blue-400 rounded-full animate-pulse"></div>
                    <div className="w-3 h-3 bg-blue-400 rounded-full animate-pulse delay-150"></div>
                    <div className="w-3 h-3 bg-blue-400 rounded-full animate-pulse delay-300"></div>
                    <span>AI is thinking...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Chat Input and File Upload Section */}
        <div className="p-6 bg-slate-800/30 border-t border-slate-700/30">
          {/* File Upload Status Display */}
          {(csvFile || pdfFile) && (
            <div className="mb-4 space-y-2">
              {csvFile && (
                <div className="flex items-center justify-between bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3">
                  <div className="flex items-center space-x-3">
                    <span className="w-8 h-8 bg-emerald-500/20 rounded-lg flex items-center justify-center text-emerald-400">📊</span>
                    <div>
                      <p className="text-emerald-400 font-medium text-sm">{csvFile.name}</p>
                      <p className="text-emerald-300 text-xs">CSV file uploaded</p>
                    </div>
                  </div>
                  {/* Button to remove CSV file */}
                  <button
                    onClick={() => { setCsvFile(null); if (csvInputRef.current) csvInputRef.current.value = null; }}
                    className="w-6 h-6 text-emerald-400 hover:text-red-400 rounded-full hover:bg-red-500/20 flex items-center justify-center transition-all duration-200"
                    title="Remove file"
                  >
                    ✕
                  </button>
                </div>
              )}
              
              {pdfFile && (
                <div className="flex items-center justify-between bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                  <div className="flex items-center space-x-3">
                    <span className="w-8 h-8 bg-red-500/20 rounded-lg flex items-center justify-center text-red-400">📄</span>
                    <div>
                      <p className="text-red-400 font-medium text-sm">{pdfFile.name}</p>
                      <p className="text-red-300 text-xs">PDF file uploaded</p>
                    </div>
                  </div>
                  {/* Button to remove PDF file */}
                  <button
                    onClick={() => { setPdfFile(null); if (pdfInputRef.current) pdfInputRef.current.value = null; }}
                    className="w-6 h-6 text-red-400 hover:text-red-300 rounded-full hover:bg-red-500/20 flex items-center justify-center transition-all duration-200"
                    title="Remove file"
                  >
                    ✕
                  </button>
                </div>
              )}
            </div>
          )}
          
          {/* Clear Chat Button */}
          {messages.length > 0 && (
            <div className="mb-4 flex justify-center">
              <button
                onClick={clearChat}
                className="px-4 py-2 bg-slate-700/50 hover:bg-red-600/50 text-slate-300 hover:text-white text-sm rounded-lg transition-all duration-200 hover:shadow-md border border-slate-600/30 hover:border-red-500/50 flex items-center space-x-2 group"
              >
                <span className="group-hover:rotate-12 transition-transform">🗑️</span>
                <span>Clear Chat</span>
              </button>
            </div>
          )}
          
          {/* Input field and send button */}
          <div className="flex items-center bg-slate-700/50 rounded-lg p-3 border border-slate-600/50 focus-within:border-slate-500 focus-within:bg-slate-700/70 transition-all duration-300">
            {/* File Upload Buttons */}
            <div className="flex items-center space-x-2 mr-3">
              {/* Hidden CSV file input */}
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileUpload(e, 'csv')}
                ref={csvInputRef}
                className="hidden"
              />
              {/* Button to trigger CSV file input */}
              <button
                onClick={() => csvInputRef.current?.click()}
                className="w-9 h-9 bg-slate-600/70 hover:bg-emerald-600/70 text-slate-300 hover:text-white rounded-lg flex items-center justify-center transition-all duration-200 hover:scale-105 group"
                title="Upload CSV file"
              >
                <span className="text-sm group-hover:scale-110 transition-transform">📊</span>
              </button>
              
              {/* Hidden PDF file input */}
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => handleFileUpload(e, 'pdf')}
                ref={pdfInputRef}
                className="hidden"
              />
              {/* Button to trigger PDF file input */}
              <button
                onClick={() => pdfInputRef.current?.click()}
                className="w-9 h-9 bg-slate-600/70 hover:bg-red-600/70 text-slate-300 hover:text-white rounded-lg flex items-center justify-center transition-all duration-200 hover:scale-105 group"
                title="Upload PDF file"
              >
                <span className="text-sm group-hover:scale-110 transition-transform">📄</span>
              </button>
            </div>
            
            {/* Chat input text field */}
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              className="flex-1 bg-transparent outline-none text-slate-200 placeholder-slate-400"
              placeholder="Ask about financial audits, compliance, or document analysis..."
              disabled={isLoading} // Disable input when loading
            />
            {/* Send message button */}
            <button
              onClick={sendMessage}
              className="ml-3 w-10 h-10 bg-slate-600 hover:bg-slate-500 text-slate-200 rounded-lg flex items-center justify-center transition-all duration-200 hover:scale-105"
              disabled={isLoading} // Disable button when loading
            >
              ➤
            </button>
          </div>
        </div>
      </div>

      {/* Right Side - Professional Dashboard */}
      <div className="w-1/2 bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 flex flex-col border-l border-slate-700/30">
        
        {/* Dashboard Header */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-700 text-white p-6 border-b border-slate-600/30 shadow-xl">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-slate-100">📋 Audit Dashboard</h2>
              <p className="text-slate-300 text-sm mt-1">Real-time analysis and insights</p>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
              <span className="text-xs text-slate-300">Live</span>
            </div>
          </div>
        </div>

        {/* Dashboard Content Area */}
        <div className="flex-1 p-8 bg-gradient-to-br from-slate-900/50 to-slate-800/50 overflow-y-auto custom-scrollbar">
          {/* Stats Cards */}
          <div className="grid grid-cols-2 gap-4 mb-8">
            <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700/50 shadow-lg backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-xs font-medium uppercase tracking-wider">Documents</p>
                  <p className="text-2xl font-bold text-slate-100 mt-1">{(csvFile ? 1 : 0) + (pdfFile ? 1 : 0)}</p>
                </div>
                <div className="w-10 h-10 bg-slate-700/50 rounded-lg flex items-center justify-center text-slate-300">
                  📁
                </div>
              </div>
            </div>
            
            <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700/50 shadow-lg backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-xs font-medium uppercase tracking-wider">Queries</p>
                  <p className="text-2xl font-bold text-slate-100 mt-1">{messages.filter(m => m.sender === 'user').length}</p>
                </div>
                <div className="w-10 h-10 bg-slate-700/50 rounded-lg flex items-center justify-center text-slate-300">
                  💬
                </div>
              </div>
            </div>
          </div>

          {/* Analysis Status Section */}
          <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 shadow-lg backdrop-blur-sm p-6 mb-6">
            <h3 className="font-semibold text-slate-100 mb-4 flex items-center">
              <span className="w-6 h-6 bg-slate-700/50 rounded-full flex items-center justify-center mr-3 text-sm text-slate-300">⚡</span>
              Analysis Status
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg border border-slate-600/30">
                <span className="text-slate-200 text-sm">Document Processing</span>
                <span className="text-xs px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded-full border border-emerald-500/30">{csvFile || pdfFile ? 'Ready' : 'Pending'}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg border border-slate-600/30">
                <span className="text-slate-200 text-sm">AI Analysis Engine</span>
                <span className="text-xs px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded-full border border-emerald-500/30">{isLoading ? 'Processing' : 'Active'}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg border border-slate-600/30">
                <span className="text-slate-200 text-sm">Compliance Checker</span>
                <span className="text-xs px-2 py-1 bg-slate-600/50 text-slate-300 rounded-full border border-slate-500/30">Standby</span>
              </div>
            </div>
          </div>

          {/* Quick Actions Section */}
          <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 shadow-lg backdrop-blur-sm p-6">
            <h3 className="font-semibold text-slate-100 mb-4 flex items-center">
              <span className="w-6 h-6 bg-slate-700/50 rounded-full flex items-center justify-center mr-3 text-sm text-slate-300">🎯</span>
              Quick Actions
            </h3>
            <div className="space-y-3">
              {[
                { icon: '🔍', text: 'Analyze invoice discrepancies', prompt: 'Analyze invoice discrepancies' },
                { icon: '⚠️', text: 'Check for duplicate transactions', prompt: 'Check for duplicate transactions' },
                { icon: '✅', text: 'Validate expense compliance', prompt: 'Validate expense compliance' },
                { icon: '📊', text: 'Generate comprehensive audit report', prompt: 'Generate audit summary' }
              ].map((item, index) => (
                <button
                  key={index}
                  onClick={() => suggestedPrompt(item.prompt)}
                  className="w-full text-left p-3 bg-slate-700/30 hover:bg-slate-700/50 rounded-lg transition-all duration-200 hover:shadow-md border border-slate-600/30 hover:border-slate-500/50 group"
                  disabled={isLoading} // Disable quick actions when loading
                >
                  <div className="flex items-center">
                    <span className="w-8 h-8 bg-slate-600/50 rounded-lg flex items-center justify-center mr-3 text-sm group-hover:scale-110 transition-transform text-slate-300">
                      {item.icon}
                    </span>
                    <span className="text-slate-200 text-sm font-medium">{item.text}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Footer Information */}
          <div className="mt-8 text-center">
            <p className="text-xs text-slate-400">
              Powered by advanced AI • Secure & Compliant • Real-time Processing
            </p>
          </div>
        </div>
      </div>
      {/* Custom CSS for scrollbar - For better aesthetics */}
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #334155; /* slate-700 */
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #64748b; /* slate-500 */
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #94a3b8; /* slate-400 */
        }
      `}</style>
    </div>
  );
};

export default FinancialAuditUI;
