import React, { useState, useEffect } from 'react'
import FileTree from './components/FileTree'
import CodeViewer from './components/CodeViewer'
import ChatPanel from './components/ChatPanel'
import './App.css'

function App() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileContent, setFileContent] = useState('')
  const [highlightedLines, setHighlightedLines] = useState(null)
  const [fileTree, setFileTree] = useState([])

  useEffect(() => {
    // Load file tree
    fetch('/api/')
      .then(res => res.json())
      .then(data => {
        // For now, we'll need to implement a file tree endpoint
        // Or load from index metadata
      })
      .catch(err => console.error('Failed to load file tree:', err))
  }, [])

  const handleFileSelect = async (filePath) => {
    setSelectedFile(filePath)
    setHighlightedLines(null)
    
    try {
      // Load file directly from filesystem via API
      const response = await fetch(`/api/file?file_path=${encodeURIComponent(filePath)}`)
      if (response.ok) {
        const data = await response.json()
        setFileContent(data.content || '')
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to load file' }))
        setFileContent(`// Error: ${errorData.detail || 'File not found'}`)
      }
    } catch (error) {
      console.error('Failed to load file:', error)
      setFileContent(`// Error: Failed to load file content - ${error.message}`)
    }
  }

  const handleCodeReference = (filePath, startLine, endLine) => {
    setSelectedFile(filePath)
    setHighlightedLines({ start: startLine, end: endLine })
    handleFileSelect(filePath)
  }

  return (
    <div className="app">
      <div className="file-tree-panel">
        <FileTree 
          onFileSelect={handleFileSelect}
          selectedFile={selectedFile}
        />
      </div>
      <div className="code-viewer-panel">
        <CodeViewer
          filePath={selectedFile}
          content={fileContent}
          highlightedLines={highlightedLines}
        />
      </div>
      <div className="chat-panel">
        <ChatPanel
          onCodeReference={handleCodeReference}
        />
      </div>
    </div>
  )
}

export default App

