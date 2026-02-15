import { Link, useLocation } from 'react-router-dom'
import './Navbar.css'

function Navbar() {
  const location = useLocation()

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand">
          <div className="navbar-logo">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect x="2" y="2" width="24" height="24" rx="6" stroke="url(#logo-grad)" strokeWidth="2" />
              <path d="M9 10L13 14L9 18" stroke="url(#logo-grad)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <line x1="15" y1="18" x2="20" y2="18" stroke="url(#logo-grad)" strokeWidth="2" strokeLinecap="round" />
              <defs>
                <linearGradient id="logo-grad" x1="2" y1="2" x2="26" y2="26">
                  <stop stopColor="#6366f1" />
                  <stop offset="1" stopColor="#a78bfa" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span className="navbar-title">CodeContext<span className="navbar-title-accent"> AI</span></span>
        </Link>

        <div className="navbar-links">
          <Link
            to="/"
            className={`navbar-link ${location.pathname === '/' ? 'active' : ''}`}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V4.414A1 1 0 0 0 12.707 4L10 1.293A1 1 0 0 0 9.293 1H4zm5 1.5L12.5 6H10a1 1 0 0 1-1-1V2.5z"/>
            </svg>
            New Project
          </Link>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
