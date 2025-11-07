import React, { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import { apiUrl } from '../utils/api'
import './ChatPanel.css'

function ChatPanel({ onCodeReference }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const parseAnswer = (answer) => {
    // Parse file references like "file.py:10-20" or "file.py:10"
    const fileRefRegex = /(\S+\.(py|js|ts|jsx|tsx|go|java|cpp|c|rs|rb|php)):(\d+)(?:-(\d+))?/g
    const parts = []
    let lastIndex = 0
    let match

    while ((match = fileRefRegex.exec(answer)) !== null) {
      // Add text before match
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: answer.substring(lastIndex, match.index)
        })
      }

      // Add file reference
      const filePath = match[1]
      const startLine = parseInt(match[3])
      const endLine = match[4] ? parseInt(match[4]) : startLine

      parts.push({
        type: 'fileRef',
        filePath,
        startLine,
        endLine,
        content: match[0]
      })

      lastIndex = match.index + match[0].length
    }

    // Add remaining text
    if (lastIndex < answer.length) {
      parts.push({
        type: 'text',
        content: answer.substring(lastIndex)
      })
    }

    return parts.length > 0 ? parts : [{ type: 'text', content: answer }]
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await axios.post(apiUrl('query'), {
        question: input,
        max_iterations: 6
      })

      const answer = response.data.answer
      const parsedAnswer = parseAnswer(answer)

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: answer,
        parsedAnswer,
        confidence: response.data.confidence,
        sources: response.data.sources,
        reasoning: response.data.reasoning
      }])
    } catch (error) {
      console.error('Query failed:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '抱歉，查询失败。请稍后重试。',
        error: true
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFileRefClick = (filePath, startLine, endLine) => {
    onCodeReference(filePath, startLine, endLine)
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h3>代码查询助手</h3>
      </div>
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="welcome-message">
            <p>👋 欢迎使用代码索引助手！</p>
            <p>你可以问我关于代码库的任何问题。</p>
            <p>例如：</p>
            <ul>
              <li>"这个项目使用了哪些模型？"</li>
              <li>"FinalAnswer 的数据格式是什么？"</li>
              <li>"如何调用 OpenAI API？"</li>
            </ul>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            {msg.role === 'user' ? (
              <div className="message-content">{msg.content}</div>
            ) : (
              <div className="message-content">
                {msg.parsedAnswer ? (
                  msg.parsedAnswer.map((part, i) => {
                    if (part.type === 'fileRef') {
                      return (
                        <span
                          key={i}
                          className="file-reference"
                          onClick={() => handleFileRefClick(part.filePath, part.startLine, part.endLine)}
                          title={`点击查看 ${part.filePath}:${part.startLine}-${part.endLine}`}
                        >
                          {part.content}
                        </span>
                      )
                    } else {
                      return <span key={i}>{part.content}</span>
                    }
                  })
                ) : (
                  msg.content
                )}
                {msg.confidence && (
                  <div className="message-meta">
                    <span className="confidence">置信度: {msg.confidence}</span>
                    {msg.sources && msg.sources.length > 0 && (
                      <span className="sources">来源: {msg.sources.length} 个</span>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="输入你的问题..."
          rows={3}
          disabled={loading}
        />
        <button onClick={handleSend} disabled={loading || !input.trim()}>
          发送
        </button>
      </div>
    </div>
  )
}

export default ChatPanel

