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
      // Try to load file directly from filesystem first
      const response = await fetch(`/api/file?path=${encodeURIComponent(filePath)}`)
      if (response.ok) {
        const data = await response.json()
        setFileContent(data.content || '')
      } else {
        // Fallback: use query endpoint
        const queryResponse = await fetch(`/api/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: `读取文件 ${filePath} 的完整内容`,
            max_iterations: 3
          })
        })
        const queryData = await queryResponse.json()
        setFileContent(queryData.answer || '')
      }
    } catch (error) {
      console.error('Failed to load file:', error)
      setFileContent('// Failed to load file content')
    }
  }

  const handleCodeReference = (filePath, startLine, endLine) => {
    setSelectedFile(filePath)
    setHighlightedLines({ start: startLine, end: endLine })
    handleFileSelect(filePath)
  }

  return (
    <div className="app">
      <div className="left-panel">
        <FileTree 
          onFileSelect={handleFileSelect}
          selectedFile={selectedFile}
        />
        <CodeViewer
          filePath={selectedFile}
          content={fileContent}
          highlightedLines={highlightedLines}
        />
      </div>
      <div className="right-panel">
        <ChatPanel
          onCodeReference={handleCodeReference}
        />
      </div>
    </div>
  )
}

export default App

