import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import FileTree from '../components/FileTree'
import CodePreview from '../components/CodePreview'
import ChatPanel from '../components/ChatPanel'
import PatchViewer from '../components/PatchViewer'
import './DashboardPage.css'

const API = 'http://localhost:8000'

function DashboardPage() {
  const { projectId } = useParams()
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileContent, setFileContent] = useState('')
  const [fileLanguage, setFileLanguage] = useState('text')
  const [activePanel, setActivePanel] = useState('chat') // 'chat' | 'edit'
  const [patchData, setPatchData] = useState(null)
  const [providers, setProviders] = useState([])
  const [selectedProvider, setSelectedProvider] = useState('gemini')

  useEffect(() => {
    fetchProject()
    fetchProviders()
  }, [projectId])

  const fetchProject = async () => {
    try {
      const res = await fetch(`${API}/api/projects/${projectId}`)
      const data = await res.json()
      setProject(data)
    } catch (err) {
      console.error('Failed to load project:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchProviders = async () => {
    try {
      const res = await fetch(`${API}/api/providers`)
      const data = await res.json()
      setProviders(data.providers || [])
      if (data.default) setSelectedProvider(data.default)
    } catch (err) {
      console.error('Failed to load providers:', err)
    }
  }

  const handleFileSelect = async (filePath) => {
    setSelectedFile(filePath)
    try {
      const res = await fetch(`${API}/api/projects/${projectId}/file?path=${encodeURIComponent(filePath)}`)
      const data = await res.json()
      setFileContent(data.content)
      setFileLanguage(data.language)
    } catch (err) {
      setFileContent('// Failed to load file')
      setFileLanguage('text')
    }
  }

  const handlePatchGenerated = (data) => {
    setPatchData(data)
    setActivePanel('edit')
  }

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner spinner-lg"></div>
        <p>Loading project...</p>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="dashboard-loading">
        <p>Project not found.</p>
      </div>
    )
  }

  return (
    <div className="dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <h1 className="dashboard-project-name">{project.name}</h1>
          <span className={`badge badge-${project.status}`}>{project.status}</span>
          <span className="dashboard-stats">{project.total_files} files · {project.total_chunks} chunks</span>
        </div>
        <div className="dashboard-header-right">
          {/* Provider Selector */}
          {providers.length > 1 && (
            <div className="provider-selector">
              {providers.map((p) => (
                <button
                  key={p.id}
                  className={`provider-btn ${selectedProvider === p.id ? 'active' : ''}`}
                  onClick={() => setSelectedProvider(p.id)}
                  title={`${p.name} (${p.model})`}
                >
                  <span className="provider-icon">
                    {p.id === 'gemini' ? '✦' : p.id === 'grok' ? '𝕏' : '🌙'}
                  </span>
                  <span className="provider-name">{p.name}</span>
                </button>
              ))}
            </div>
          )}
          {providers.length === 1 && (
            <div className="provider-badge">
              <span className="provider-icon">
                {providers[0].id === 'gemini' ? '✦' : providers[0].id === 'grok' ? '𝕏' : '🌙'}
              </span>
              {providers[0].name}
            </div>
          )}

          <div className="panel-switcher">
            <button
              className={`panel-switch-btn ${activePanel === 'chat' ? 'active' : ''}`}
              onClick={() => setActivePanel('chat')}
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 1a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h9.586a2 2 0 0 1 1.414.586l2 2V2a1 1 0 0 0-1-1H2z"/>
              </svg>
              Chat
            </button>
            <button
              className={`panel-switch-btn ${activePanel === 'edit' ? 'active' : ''}`}
              onClick={() => setActivePanel('edit')}
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10z"/>
              </svg>
              Edit
            </button>
          </div>
        </div>
      </div>

      {/* Main 3-column layout */}
      <div className="dashboard-body">
        {/* Left: File Tree */}
        <div className="dashboard-sidebar glass-card">
          <div className="sidebar-header">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" style={{ opacity: 0.5 }}>
              <path d="M1 3.5A1.5 1.5 0 0 1 2.5 2h2.764c.958 0 1.76.56 2.311 1.184C7.985 3.648 8.48 4 9 4h4.5A1.5 1.5 0 0 1 15 5.5v7a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 12.5v-9z"/>
            </svg>
            <span>Files</span>
          </div>
          {project.file_tree ? (
            <FileTree
              tree={project.file_tree}
              selectedFile={selectedFile}
              onSelect={handleFileSelect}
            />
          ) : (
            <p className="sidebar-empty">No files indexed yet.</p>
          )}
        </div>

        {/* Center: Code Preview */}
        <div className="dashboard-center glass-card">
          {selectedFile ? (
            <CodePreview
              filePath={selectedFile}
              content={fileContent}
              language={fileLanguage}
            />
          ) : (
            <div className="center-placeholder">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.2 }}>
                <polyline points="16 18 22 12 16 6"></polyline>
                <polyline points="8 6 2 12 8 18"></polyline>
              </svg>
              <p>Select a file to preview</p>
            </div>
          )}
        </div>

        {/* Right: Chat or Edit Panel */}
        <div className="dashboard-panel glass-card">
          {activePanel === 'chat' ? (
            <ChatPanel
              projectId={projectId}
              onPatchGenerated={handlePatchGenerated}
              selectedFile={selectedFile}
              provider={selectedProvider}
            />
          ) : (
            <PatchViewer
              projectId={projectId}
              patchData={patchData}
              selectedFile={selectedFile}
              provider={selectedProvider}
            />
          )}
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
