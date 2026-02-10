import { useState, useRef, useEffect } from 'react';
import './App.css';

const API_URL = 'http://localhost:8000';
const USERNAME_STORAGE_KEY = 'nft_chat_username';

// Simple markdown parser
const parseMarkdown = (text) => {
  if (!text) return '';
  
  return text
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Code blocks
    .replace(/```(.+?)```/gs, '<pre><code>$1</code></pre>')
    // Inline code
    .replace(/`(.+?)`/g, '<code>$1</code>')
    // Links
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>')
    // Headings
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Line breaks
    .replace(/\n/g, '<br/>');
};

// Check if HTML is a full document
const isFullHtmlDocument = (html) => {
  if (!html) return false;
  const trimmed = html.trim();
  return trimmed.startsWith('<!DOCTYPE') || 
         trimmed.startsWith('<html') || 
         trimmed.includes('<head>');
};

// HTML Iframe Component with auto-height
const HtmlIframe = ({ html, template }) => {
  const iframeRef = useRef(null);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    const adjustHeight = () => {
      try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
        if (iframeDoc?.body) {
          const height = iframeDoc.body.scrollHeight;
          iframe.style.height = `${Math.max(height + 40, 500)}px`;
        }
      } catch (e) {
        console.log('Could not adjust iframe height:', e.message);
      }
    };

    iframe.addEventListener('load', adjustHeight);
    const timer = setTimeout(adjustHeight, 200);
    
    return () => {
      iframe.removeEventListener('load', adjustHeight);
      clearTimeout(timer);
    };
  }, [html]);

  return (
    <iframe
      ref={iframeRef}
      className={`block-iframe block-${template}`}
      srcDoc={html}
      title={`NFT ${template}`}
      sandbox="allow-scripts allow-same-origin"
    />
  );
};

function App() {
  const [username, setUsername] = useState(() => localStorage.getItem(USERNAME_STORAGE_KEY) || '');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);

  const handleUsernameSubmit = (e) => {
    e.preventDefault();
    const value = (e.target.username?.value || '').trim();
    if (!value) return;
    setUsername(value);
    localStorage.setItem(USERNAME_STORAGE_KEY, value);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    
    // Add user message to UI
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          user_id: username,
          session_id: sessionId
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      
      // Debug: Log the response
      console.log('API Response:', data);
      console.log('Blocks:', data.blocks);
      data.blocks?.forEach((block, idx) => {
        console.log(`Block ${idx}:`, {
          type: block.type,
          hasMarkdown: !!block.markdown,
          hasHtml: !!block.html,
          htmlPreview: block.html?.substring(0, 100),
          template: block.template
        });
      });
      
      // Update session ID
      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }

      // Add assistant response blocks
      setMessages(prev => [...prev, { role: 'assistant', blocks: data.blocks }]);
      
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { 
        role: 'error', 
        content: `Error: ${error.message}` 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const renderMessage = (msg, idx) => {
    if (msg.role === 'user') {
      return (
        <div key={idx} className="message user-message">
          <div className="message-content">{msg.content}</div>
        </div>
      );
    }

    if (msg.role === 'error') {
      return (
        <div key={idx} className="message error-message">
          <div className="message-content">{msg.content}</div>
        </div>
      );
    }

    // Assistant message with blocks - single container for consistency
    return (
      <div key={idx} className="message assistant-message">
        <div className="assistant-message-inner">
          {msg.blocks?.map((block, blockIdx) => (
            <div key={blockIdx} className="message-block">
              {block.type === 'text' && block.markdown && (
                <div
                  className="block-text"
                  dangerouslySetInnerHTML={{ __html: parseMarkdown(block.markdown) }}
                />
              )}
              {block.type === 'html_component' && block.html && (
                <>
                  {isFullHtmlDocument(block.html) ? (
                    <HtmlIframe html={block.html} template={block.template} />
                  ) : (
                    <div
                      className={`block-html block-${block.template}`}
                      dangerouslySetInnerHTML={{ __html: block.html }}
                    />
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  if (!username) {
    return (
      <div className="app username-screen">
        <div className="username-card">
          <h1>NFT Marketplace Chatbot</h1>
          <p>Enter your username to start</p>
          <form onSubmit={handleUsernameSubmit} className="username-form">
            <input
              type="text"
              name="username"
              placeholder="Username (required)"
              required
              autoFocus
              className="username-input"
              minLength={1}
            />
            <button type="submit" className="send-button">Enter</button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>NFT Marketplace Chatbot</h1>
        <div className="user-info">
          <span className="user-info-name">{username}</span>
          <button
            type="button"
            onClick={() => {
              setUsername('');
              localStorage.removeItem(USERNAME_STORAGE_KEY);
              setMessages([]);
              setSessionId(null);
            }}
            className="user-info-change"
            title="Change username"
          >
            Change
          </button>
        </div>
      </header>

      <div className="scroll-wrapper">
        <div className="chat-container">
          <div className="messages">
            {messages.length === 0 && (
              <div className="welcome-message">
                <h2>Welcome to NFT Marketplace Assistant</h2>
                <p>Try asking:</p>
                <ul>
                  <li>"Show me some NFTs"</li>
                  <li>"Find rare NFTs under 5 ETH"</li>
                  <li>"Show NFTs from Meta Legends collection"</li>
                  <li>"Tell me about NFT nft-042"</li>
                </ul>
              </div>
            )}
            {messages.map(renderMessage)}
            {loading && (
              <div className="message assistant-message loading">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      <div className="input-bar">
        <form onSubmit={sendMessage} className="input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about NFTs..."
            disabled={loading}
            className="message-input"
          />
          <button type="submit" disabled={loading || !input.trim()} className="send-button">
            {loading ? 'Sending...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
