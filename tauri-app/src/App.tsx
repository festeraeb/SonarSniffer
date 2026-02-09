import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ProcessVideo from './pages/ProcessVideo'
import Errors from './pages/Errors'
import Settings from './pages/Settings'
import './App.css'

function App() {
    const [activeTab, setActiveTab] = useState('dashboard')

    useEffect(() => {
        document.addEventListener('DOMContentLoaded', () => {
            invoke('get_dashboard_data').catch(err => console.error(err))
        })
    }, [])

    return (
        <Router>
            <div className="app">
                <nav className="navbar">
                    <div className="navbar-brand">
                        <h1>🐟 SonarSniffer</h1>
                        <span className="beta-badge">Beta v0.1</span>
                    </div>
                    <ul className="nav-links">
                        <li>
                            <Link
                                to="/"
                                className={activeTab === 'dashboard' ? 'active' : ''}
                                onClick={() => setActiveTab('dashboard')}
                            >
                                📊 Dashboard
                            </Link>
                        </li>
                        <li>
                            <Link
                                to="/process"
                                className={activeTab === 'process' ? 'active' : ''}
                                onClick={() => setActiveTab('process')}
                            >
                                🎬 Process Video
                            </Link>
                        </li>
                        <li>
                            <Link
                                to="/errors"
                                className={activeTab === 'errors' ? 'active' : ''}
                                onClick={() => setActiveTab('errors')}
                            >
                                🚨 Errors
                            </Link>
                        </li>
                        <li>
                            <Link
                                to="/settings"
                                className={activeTab === 'settings' ? 'active' : ''}
                                onClick={() => setActiveTab('settings')}
                            >
                                ⚙️ Settings
                            </Link>
                        </li>
                    </ul>
                </nav>

                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/process" element={<ProcessVideo />} />
                        <Route path="/errors" element={<Errors />} />
                        <Route path="/settings" element={<Settings />} />
                    </Routes>
                </main>
            </div>
        </Router>
    )
}

export default App
