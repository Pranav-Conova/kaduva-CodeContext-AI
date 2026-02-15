import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import './UploadPage.css'

const API = 'http://localhost:8000'

function UploadPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('github')
  const [githubUrl, setGithubUrl] = useState('')
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [statusMsg, setStatusMsg] = useState('')
  const [error, setError] = useState('')
  const [projects, setProjects] = useState([])

  // Load existing projects
  useEffect(() => {
    fetch(`${API}/api/projects`)
      .then(r => r.json())
      .then(setProjects)
      .catch(() => {})
  }, [])

  const handleGithubUpload = async (e) => {
    e.preventDefault()
    if (!githubUrl.trim()) return

    setUploading(true)
    setError('')
    setProgress(10)
    setStatusMsg('Cloning repository...')

    try {
      const formData = new FormData()
      formData.append('url', githubUrl.trim())

      const res = await fetch(`${API}/api/upload/github`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Upload failed')
      }

      const data = await res.json()
      setProgress(40)
      setStatusMsg('Processing codebase...')

      // Poll for completion
      await pollProject(data.project_id)
    } catch (err) {
      setError(err.message)
      setUploading(false)
    }
  }

  const handleZipUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    setUploading(true)
    setError('')
    setProgress(10)
    setStatusMsg('Uploading ZIP...')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(`${API}/api/upload/zip`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Upload failed')
      }

      const data = await res.json()
      setProgress(40)
      setStatusMsg('Processing codebase...')

      await pollProject(data.project_id)
    } catch (err) {
      setError(err.message)
      setUploading(false)
    }
  }

  const pollProject = async (projectId) => {
    let attempts = 0
    const maxAttempts = 120 // 2 minutes

    const interval = setInterval(async () => {
      attempts++
      try {
        const res = await fetch(`${API}/api/projects/${projectId}`)
        const data = await res.json()

        if (data.status === 'ready') {
          clearInterval(interval)
          setProgress(100)
          setStatusMsg('Done! Redirecting...')
          setTimeout(() => navigate(`/project/${projectId}`), 600)
        } else if (data.status === 'error') {
          clearInterval(interval)
          setError('Processing failed. Please check the backend logs.')
          setUploading(false)
        } else {
          // Still processing
          const newProgress = Math.min(40 + (attempts / maxAttempts) * 55, 95)
          setProgress(newProgress)
          setStatusMsg(`Indexing codebase... (${data.total_files || 0} files found)`)
        }
      } catch {
        // Keep polling
      }

      if (attempts >= maxAttempts) {
        clearInterval(interval)
        setError('Processing timed out. The repo may be too large.')
        setUploading(false)
      }
    }, 1000)
  }

  return (
    <div className="upload-page">
      <div className="upload-hero slide-up">
        <div className="hero-badge">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
            <path d="M7 0L8.56 5.44L14 7L8.56 8.56L7 14L5.44 8.56L0 7L5.44 5.44L7 0Z"/>
          </svg>
          AI-Powered Code Intelligence
        </div>
        <h1 className="hero-title">
          Understand any codebase<br />
          <span className="hero-gradient">in seconds.</span>
        </h1>
        <p className="hero-subtitle">
          Upload a repository. Ask questions. Get intelligent code edits.
          Powered by Gemini AI and semantic search.
        </p>
      </div>

      <div className="upload-card glass-card slide-up" style={{ animationDelay: '0.1s' }}>
        {/* Tabs */}
        <div className="upload-tabs">
          <button
            className={`upload-tab ${activeTab === 'github' ? 'active' : ''}`}
            onClick={() => setActiveTab('github')}
            disabled={uploading}
          >
            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
            </svg>
            GitHub URL
          </button>
          <button
            className={`upload-tab ${activeTab === 'zip' ? 'active' : ''}`}
            onClick={() => setActiveTab('zip')}
            disabled={uploading}
          >
            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
              <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5zM7 3V2h2v1H7zm2 1H7v1h2V4zm0 2H7v1h2V6zm0 2H7v1h2V8zm0 2H7v2h2v-2z"/>
            </svg>
            Upload ZIP
          </button>
        </div>

        {/* Content */}
        <div className="upload-content">
          {activeTab === 'github' && (
            <form className="upload-form" onSubmit={handleGithubUpload}>
              <div className="input-group">
                <label className="input-label">Repository URL</label>
                <input
                  id="github-url-input"
                  type="url"
                  className="input"
                  placeholder="https://github.com/user/repo"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  disabled={uploading}
                  required
                />
              </div>
              <button
                id="submit-github"
                type="submit"
                className="btn btn-primary btn-lg upload-submit"
                disabled={uploading || !githubUrl.trim()}
              >
                {uploading ? (
                  <>
                    <span className="spinner"></span>
                    Processing...
                  </>
                ) : (
                  <>
                    <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0zm3.5 7.5h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3a.5.5 0 0 1 1 0v3h3a.5.5 0 0 1 0 1z"/>
                    </svg>
                    Analyze Repository
                  </>
                )}
              </button>
            </form>
          )}

          {activeTab === 'zip' && (
            <div className="upload-form">
              <label className="zip-dropzone" htmlFor="zip-input">
                <input
                  id="zip-input"
                  type="file"
                  accept=".zip"
                  onChange={handleZipUpload}
                  disabled={uploading}
                  hidden
                />
                <div className="dropzone-icon">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <span className="dropzone-text">
                  {uploading ? 'Processing...' : 'Click to select a ZIP file'}
                </span>
                <span className="dropzone-hint">Max recommended: 100MB</span>
              </label>
            </div>
          )}

          {/* Progress */}
          {uploading && (
            <div className="upload-progress fade-in">
              <div className="progress-bar">
                <div
                  className={`progress-bar-fill ${progress < 40 ? 'indeterminate' : ''}`}
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <p className="progress-status">{statusMsg}</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="upload-error fade-in">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0zm1 12H7v-2h2v2zm0-3H7V4h2v5z"/>
              </svg>
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Existing Projects */}
      {projects.length > 0 && (
        <div className="projects-section slide-up" style={{ animationDelay: '0.2s' }}>
          <h2 className="projects-title">Your Projects</h2>
          <div className="projects-grid">
            {projects.map(p => (
              <button
                key={p.id}
                className="project-card glass-card"
                onClick={() => p.status === 'ready' && navigate(`/project/${p.id}`)}
                disabled={p.status !== 'ready'}
              >
                <div className="project-card-header">
                  <span className="project-name">{p.name}</span>
                  <span className={`badge badge-${p.status}`}>{p.status}</span>
                </div>
                <div className="project-card-meta">
                  <span>{p.total_files} files</span>
                  <span>·</span>
                  <span>{p.total_chunks} chunks</span>
                  <span>·</span>
                  <span>{p.source_type}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default UploadPage
