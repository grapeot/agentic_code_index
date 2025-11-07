import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './FileTree.css'

function FileTree({ onFileSelect, selectedFile }) {
  const [tree, setTree] = useState([])
  const [expanded, setExpanded] = useState(new Set())

  useEffect(() => {
    // Load file tree from backend
    // For now, we'll use a simple approach - get files from index metadata
    loadFileTree()
  }, [])

  const loadFileTree = async () => {
    try {
      // Get real filesystem tree from backend
      const response = await fetch('/api/file-tree')
      
      // Check if response is OK
      if (!response.ok) {
        const text = await response.text()
        console.error('Failed to load file tree:', response.status, text)
        setTree([])
        return
      }
      
      // Check content type
      const contentType = response.headers.get('content-type')
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text()
        console.error('Invalid response type:', contentType, text.substring(0, 200))
        setTree([])
        return
      }
      
      const data = await response.json()
      
      if (data.error) {
        console.error('Failed to load file tree:', data.error)
        setTree([])
        return
      }
      
      if (data && data.children) {
        // Convert backend tree structure to frontend format
        setTree(convertTreeStructure(data.children))
      } else {
        setTree([])
      }
    } catch (error) {
      console.error('Failed to load file tree:', error)
      // If it's a JSON parse error, log more details
      if (error instanceof SyntaxError) {
        console.error('JSON parse error - response might not be JSON')
      }
      setTree([])
    }
  }

  const convertTreeStructure = (children) => {
    if (!children || !Array.isArray(children)) {
      return []
    }
    
    return children.map(item => ({
      name: item.name,
      path: item.path,
      isFile: item.type === 'file',
      children: item.type === 'directory' && item.children 
        ? convertTreeStructure(item.children).reduce((acc, child) => {
            acc[child.name] = child
            return acc
          }, {})
        : {}
    }))
  }

  const toggleExpand = (path) => {
    const newExpanded = new Set(expanded)
    if (newExpanded.has(path)) {
      newExpanded.delete(path)
    } else {
      newExpanded.add(path)
    }
    setExpanded(newExpanded)
  }

  const renderNode = (node, level = 0) => {
    const isExpanded = expanded.has(node.path)
    const isSelected = selectedFile === node.path

    if (node.isFile) {
      return (
        <div
          key={node.path}
          className={`file-node ${isSelected ? 'selected' : ''}`}
          style={{ paddingLeft: `${level * 16}px` }}
          onClick={() => onFileSelect(node.path)}
        >
          <span className="file-icon">📄</span>
          <span className="file-name">{node.name}</span>
        </div>
      )
    } else {
      return (
        <div key={node.path}>
          <div
            className="folder-node"
            style={{ paddingLeft: `${level * 16}px` }}
            onClick={() => toggleExpand(node.path)}
          >
            <span className="folder-icon">{isExpanded ? '📂' : '📁'}</span>
            <span className="folder-name">{node.name}</span>
          </div>
          {isExpanded && (
            <div className="folder-children">
              {Object.values(node.children).map(child => renderNode(child, level + 1))}
            </div>
          )}
        </div>
      )
    }
  }

  return (
    <div className="file-tree">
      <div className="file-tree-header">
        <h3>文件树</h3>
      </div>
      <div className="file-tree-content">
        {tree.map(node => renderNode(node))}
      </div>
    </div>
  )
}

export default FileTree

