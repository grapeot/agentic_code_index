import React, { useState, useEffect } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism'
import axios from 'axios'
import './CodeViewer.css'

function CodeViewer({ filePath, content, highlightedLines }) {
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [language, setLanguage] = useState('python')

  useEffect(() => {
    if (filePath) {
      loadFileContent(filePath)
      detectLanguage(filePath)
    } else {
      setCode('')
    }
  }, [filePath])

  useEffect(() => {
    if (content) {
      setCode(content)
    }
  }, [content])

  const detectLanguage = (path) => {
    const ext = path.split('.').pop().toLowerCase()
    const langMap = {
      'py': 'python',
      'js': 'javascript',
      'jsx': 'jsx',
      'ts': 'typescript',
      'tsx': 'tsx',
      'go': 'go',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'c',
      'rs': 'rust',
      'rb': 'ruby',
      'php': 'php',
      'md': 'markdown',
      'json': 'json',
      'yaml': 'yaml',
      'yml': 'yaml',
      'html': 'html',
      'css': 'css'
    }
    setLanguage(langMap[ext] || 'text')
  }

  const loadFileContent = async (path) => {
    setLoading(true)
    try {
      // Load file directly from filesystem via API
      const response = await axios.get('/api/file', {
        params: { file_path: path }
      })
      if (response.data && response.data.content) {
        setCode(response.data.content)
      } else {
        setCode('// File content not available')
      }
    } catch (error) {
      console.error('Failed to load file:', error)
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to load file content'
      setCode(`// Error: ${errorMsg}`)
    } finally {
      setLoading(false)
    }
  }

  const lineProps = (lineNumber) => {
    if (highlightedLines && 
        lineNumber >= highlightedLines.start && 
        lineNumber <= highlightedLines.end) {
      return {
        style: {
          backgroundColor: '#ffeb3b40',
          display: 'block',
          width: '100%'
        }
      }
    }
    return {}
  }

  if (!filePath) {
    return (
      <div className="code-viewer empty">
        <div className="empty-message">
          <p>选择一个文件查看代码</p>
        </div>
      </div>
    )
  }

  return (
    <div className="code-viewer">
      <div className="code-viewer-header">
        <span className="file-path">{filePath}</span>
        {highlightedLines && (
          <span className="highlight-info">
            高亮: {highlightedLines.start}-{highlightedLines.end}
          </span>
        )}
      </div>
      <div className="code-viewer-content">
        {loading ? (
          <div className="loading">加载中...</div>
        ) : (
          <SyntaxHighlighter
            language={language}
            style={vscDarkPlus}
            showLineNumbers
            lineNumberStyle={{ minWidth: '3em', paddingRight: '1em' }}
            customStyle={{ margin: 0, padding: '16px' }}
            lineProps={lineProps}
          >
            {code || '// No content'}
          </SyntaxHighlighter>
        )}
      </div>
    </div>
  )
}

export default CodeViewer

