import { useState } from 'react'
import './PatchViewer.css'

const API = 'http://localhost:8000'

function PatchViewer({ projectId, patchData, selectedFile, provider = 'gemini' }) {
  const [instruction, setInstruction] = useState('')
  const [loading, setLoading] = useState(false)
  const [localPatch, setLocalPatch] = useState(patchData)
  const [applied, setApplied] = useState(false)
  const [error, setError] = useState('')

  const currentPatch = localPatch || patchData

  const handleGenerateEdit = async () => {
    if (!instruction.trim() || !selectedFile) return

    setLoading(true)
    setError('')
    setApplied(false)

    try {
      const res = await fetch(`${API}/api/edit/${projectId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instruction: instruction.trim(),
          file_path: selectedFile,
          provider,
        }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Edit generation failed')
      }

      const data = await res.json()
      setLocalPatch(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleApply = async () => {
    if (!currentPatch) return

    setLoading(true)
    setError('')

    try {
      const res = await fetch(`${API}/api/edit/${projectId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instruction: instruction.trim() || 'apply edit',
          file_path: currentPatch.file_path,
          provider,
        }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Apply failed')
      }

      setApplied(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const renderPatch = (patch) => {
    if (!patch) return null

    const lines = patch.split('\n')
    return lines.map((line, i) => {
      let className = 'patch-line'
      if (line.startsWith('+') && !line.startsWith('+++')) className += ' patch-add'
      else if (line.startsWith('-') && !line.startsWith('---')) className += ' patch-remove'
      else if (line.startsWith('@@')) className += ' patch-range'
      else if (line.startsWith('---') || line.startsWith('+++')) className += ' patch-header'

      return (
        <div key={i} className={className}>
          <span className="patch-line-content">{line}</span>
        </div>
      )
    })
  }

  return (
    <div className="patch-viewer">
      <div className="patch-header">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" style={{ opacity: 0.5 }}>
          <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10z"/>
        </svg>
        <span>Code Editor</span>
      </div>

      {/* Edit Input */}
      <div className="patch-input-area">
        <div className="patch-file-target">
          {selectedFile ? (
            <span className="font-mono" style={{ fontSize: '0.78rem', color: 'var(--accent-primary)' }}>
              📄 {selectedFile}
            </span>
          ) : (
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Select a file from the tree first
            </span>
          )}
        </div>
        <textarea
          className="input patch-instruction"
          placeholder="Describe the code change (e.g., 'Convert to async/await', 'Add error handling')"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          disabled={loading || !selectedFile}
          rows={3}
        />
        <button
          className="btn btn-primary btn-sm"
          onClick={handleGenerateEdit}
          disabled={loading || !instruction.trim() || !selectedFile}
        >
          {loading ? (
            <><span className="spinner"></span> Generating...</>
          ) : (
            '🧠 Generate Edit'
          )}
        </button>
      </div>

      {/* Patch Display */}
      {currentPatch && currentPatch.patch && (
        <div className="patch-result fade-in">
          <div className="patch-result-header">
            <span className="patch-result-title">Diff Preview</span>
            <div className="patch-result-actions">
              {!applied ? (
                <button
                  className="btn btn-success btn-sm"
                  onClick={handleApply}
                  disabled={loading}
                >
                  ✅ Apply Patch
                </button>
              ) : (
                <span className="badge badge-ready">Applied!</span>
              )}
            </div>
          </div>
          <div className="patch-diff-view">
            {renderPatch(currentPatch.patch)}
          </div>
        </div>
      )}

      {currentPatch && !currentPatch.patch && (
        <div className="patch-no-changes fade-in">
          <p>No changes detected. The AI returned identical code.</p>
        </div>
      )}

      {error && (
        <div className="upload-error fade-in" style={{ margin: 'var(--space-md)' }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0zm1 12H7v-2h2v2zm0-3H7V4h2v5z"/>
          </svg>
          {error}
        </div>
      )}
    </div>
  )
}

export default PatchViewer
