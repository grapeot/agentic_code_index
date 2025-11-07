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
      // Get file list from backend
      const response = await fetch('/api/files')
      const data = await response.json()
      
      if (data.files && data.files.length > 0) {
        setTree(buildTreeFromPaths(data.files))
      } else {
        // Fallback to mock structure if no index
        setTree(buildTreeFromPaths([
          'agent.py',
          'main.py',
          'models.py',
          'tools.py',
          'indexing.py',
          'search.py',
          'test_mvp.py',
          'test_query.py'
        ]))
      }
    } catch (error) {
      console.error('Failed to load file tree:', error)
      // Fallback to mock structure
      setTree(buildTreeFromPaths([
        'agent.py',
        'main.py',
        'models.py',
        'tools.py'
      ]))
    }
  }

  const buildTreeFromPaths = (paths) => {
    const tree = {}
    paths.forEach(path => {
      const parts = path.split('/')
      let current = tree
      parts.forEach((part, index) => {
        if (!current[part]) {
          current[part] = {
            name: part,
            path: parts.slice(0, index + 1).join('/'),
            children: {},
            isFile: index === parts.length - 1
          }
        }
        current = current[part].children
      })
    })
    return Object.values(tree)
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

