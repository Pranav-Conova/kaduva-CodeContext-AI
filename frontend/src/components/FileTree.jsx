import { useState } from 'react'
import './FileTree.css'

function FileTreeNode({ node, depth = 0, selectedFile, onSelect }) {
  const [expanded, setExpanded] = useState(depth < 2)

  if (node.type === 'file') {
    const isActive = selectedFile === node.path
    const ext = node.name.split('.').pop()

    return (
      <button
        className={`tree-file ${isActive ? 'active' : ''}`}
        style={{ paddingLeft: `${12 + depth * 16}px` }}
        onClick={() => onSelect(node.path)}
        title={node.path}
      >
        <span className={`tree-file-icon ext-${ext}`}>{getFileIcon(ext)}</span>
        <span className="tree-file-name">{node.name}</span>
      </button>
    )
  }

  // Directory
  return (
    <div className="tree-dir">
      <button
        className="tree-dir-header"
        style={{ paddingLeft: `${12 + depth * 16}px` }}
        onClick={() => setExpanded(!expanded)}
      >
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="currentColor"
          className={`tree-arrow ${expanded ? 'expanded' : ''}`}
        >
          <path d="M4 2l4 4-4 4V2z" />
        </svg>
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" className="tree-folder-icon">
          <path d={expanded
            ? "M1 3.5A1.5 1.5 0 0 1 2.5 2h2.764c.958 0 1.76.56 2.311 1.184C7.985 3.648 8.48 4 9 4h4.5A1.5 1.5 0 0 1 15 5.5v.5H1v-2.5z"
            : "M1 3.5A1.5 1.5 0 0 1 2.5 2h2.764c.958 0 1.76.56 2.311 1.184C7.985 3.648 8.48 4 9 4h4.5A1.5 1.5 0 0 1 15 5.5v7a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 12.5v-9z"
          } />
        </svg>
        <span className="tree-dir-name">{node.name}</span>
      </button>
      {expanded && node.children && (
        <div className="tree-children">
          {node.children
            .sort((a, b) => {
              if (a.type === b.type) return a.name.localeCompare(b.name)
              return a.type === 'directory' ? -1 : 1
            })
            .map((child, i) => (
              <FileTreeNode
                key={`${child.name}-${i}`}
                node={child}
                depth={depth + 1}
                selectedFile={selectedFile}
                onSelect={onSelect}
              />
            ))}
        </div>
      )}
    </div>
  )
}

function getFileIcon(ext) {
  const icons = {
    py: '🐍', js: '⚡', jsx: '⚛️', ts: '🔷', tsx: '⚛️',
    json: '📋', yaml: '📋', yml: '📋', md: '📝', go: '🔵',
    java: '☕', rs: '🦀', rb: '💎', php: '🐘', css: '🎨',
    html: '🌐', toml: '⚙️', env: '🔒',
  }
  return icons[ext] || '📄'
}

function FileTree({ tree, selectedFile, onSelect }) {
  if (!tree || !tree.children) return null

  return (
    <div className="file-tree">
      {tree.children
        .sort((a, b) => {
          if (a.type === b.type) return a.name.localeCompare(b.name)
          return a.type === 'directory' ? -1 : 1
        })
        .map((child, i) => (
          <FileTreeNode
            key={`${child.name}-${i}`}
            node={child}
            depth={0}
            selectedFile={selectedFile}
            onSelect={onSelect}
          />
        ))}
    </div>
  )
}

export default FileTree
