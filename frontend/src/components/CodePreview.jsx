import './CodePreview.css'

function CodePreview({ filePath, content, language }) {
  if (!content) {
    return (
      <div className="code-preview-empty">
        <p>No content to display</p>
      </div>
    )
  }

  const lines = content.split('\n')

  return (
    <div className="code-preview">
      <div className="code-preview-header">
        <span className="code-preview-path">{filePath}</span>
        <span className="code-preview-lang">{language}</span>
      </div>
      <div className="code-preview-body">
        <div className="code-line-numbers">
          {lines.map((_, i) => (
            <span key={i} className="line-number">{i + 1}</span>
          ))}
        </div>
        <pre className="code-preview-content">
          <code>{content}</code>
        </pre>
      </div>
    </div>
  )
}

export default CodePreview
