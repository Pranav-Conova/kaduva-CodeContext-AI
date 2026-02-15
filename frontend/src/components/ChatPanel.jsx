import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import './ChatPanel.css'

const API = 'http://localhost:8000'

function ChatPanel({ projectId, onPatchGenerated, selectedFile, provider = 'gemini' }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Load chat history
  useEffect(() => {
    fetch(`${API}/api/chat/${projectId}/history`)
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) setMessages(data)
      })
      .catch(() => {})
  }, [projectId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const question = input.trim()
    setInput('')
    setLoading(true)

    // Add user message
    const userMsg = { role: 'user', content: question, id: Date.now() }
    setMessages(prev => [...prev, userMsg])

    try {
      const res = await fetch(`${API}/api/chat/${projectId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, provider }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Chat failed')
      }

      const data = await res.json()
      const assistantMsg = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        id: Date.now() + 1,
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        content: `❌ Error: ${err.message}`,
        id: Date.now() + 1,
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleEditRequest = async () => {
    if (!selectedFile || !input.trim()) return

    setLoading(true)
    const instruction = input.trim()
    setInput('')

    const userMsg = { role: 'user', content: `✏️ Edit: ${instruction}\n📄 File: ${selectedFile}`, id: Date.now() }
    setMessages(prev => [...prev, userMsg])

    try {
      const res = await fetch(`${API}/api/edit/${projectId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction, file_path: selectedFile, provider }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Edit failed')
      }

      const data = await res.json()
      onPatchGenerated(data)

      const assistantMsg = {
        role: 'assistant',
        content: `✅ Generated edit for \`${selectedFile}\`. Switch to the **Edit** tab to review the patch.`,
        id: Date.now() + 1,
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        content: `❌ Edit error: ${err.message}`,
        id: Date.now() + 1,
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" style={{ opacity: 0.5 }}>
          <path d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14zm0-1A6 6 0 1 1 8 2a6 6 0 0 1 0 12zm-1-4h2v1H7v-1zm.22-5.26A1.97 1.97 0 0 1 8 4.5c.87 0 1.68.56 1.97 1.38.13.36.2.75.03 1.12-.17.37-.5.6-.78.82-.14.1-.27.2-.36.32-.1.14-.12.25-.12.36v.5H7.26v-.5c0-.39.13-.72.35-1 .21-.25.47-.44.69-.6.22-.16.38-.3.46-.47a.57.57 0 0 0-.01-.47A.97.97 0 0 0 8 5.5a.96.96 0 0 0-.87.55l-.01.02-.93-.47.01-.02a1.97 1.97 0 0 1 .02-.04z"/>
        </svg>
        <span>AI Assistant</span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-welcome fade-in">
            <div className="chat-welcome-icon">🤖</div>
            <h3>Ask me anything</h3>
            <p>about this codebase</p>
            <div className="chat-suggestions">
              {[
                'What does this project do?',
                'Where is authentication handled?',
                'List all API endpoints',
                'Find potential bugs',
              ].map((s, i) => (
                <button
                  key={i}
                  className="chat-suggestion"
                  onClick={() => setInput(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`chat-message chat-${msg.role} fade-in`}>
            <div className="chat-message-avatar">
              {msg.role === 'user' ? '👤' : '🤖'}
            </div>
            <div className="chat-message-body">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
              {msg.sources && msg.sources.length > 0 && (
                <div className="chat-sources">
                  <span className="sources-label">Sources:</span>
                  {msg.sources.slice(0, 5).map((src, i) => (
                    <span key={i} className="source-tag font-mono">{src.file_path}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="chat-message chat-assistant fade-in">
            <div className="chat-message-avatar">🤖</div>
            <div className="chat-message-body">
              <div className="chat-thinking">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-area" onSubmit={handleSend}>
        <input
          ref={inputRef}
          id="chat-input"
          type="text"
          className="input chat-input"
          placeholder="Ask about this codebase..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <div className="chat-actions">
          <button
            type="submit"
            className="btn btn-primary btn-sm"
            disabled={!input.trim() || loading}
          >
            Ask
          </button>
          {selectedFile && (
            <button
              type="button"
              className="btn btn-success btn-sm"
              disabled={!input.trim() || loading}
              onClick={handleEditRequest}
              title={`Edit ${selectedFile}`}
            >
              ✏️ Edit
            </button>
          )}
        </div>
      </form>
    </div>
  )
}

export default ChatPanel
