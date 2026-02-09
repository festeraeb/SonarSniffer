import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'

export default function Errors() {
    const [errors, setErrors] = useState([])
    const [filter, setFilter] = useState('all')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        loadErrors()
        const interval = setInterval(loadErrors, 10000) // Refresh every 10 seconds
        return () => clearInterval(interval)
    }, [filter])

    const loadErrors = async () => {
        try {
            const severity = filter === 'all' ? null : filter
            const result = await invoke('get_errors', { limit: 100, severity }) as any
            setErrors(result)
            setError(null)
        } catch (err) {
            console.error('Failed to load errors:', err)
            setError(String(err))
        } finally {
            setLoading(false)
        }
    }

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'critical':
                return '#dc3545'
            case 'warning':
                return '#ffc107'
            case 'info':
                return '#0dcaf0'
            default:
                return '#667eea'
        }
    }

    const getSeverityBackground = (severity: string) => {
        switch (severity) {
            case 'critical':
                return '#ffe5e5'
            case 'warning':
                return '#fff9e5'
            case 'info':
                return '#e5f9ff'
            default:
                return '#f0f7ff'
        }
    }

    if (loading) {
        return <div className="spinner"></div>
    }

    return (
        <div className="page">
            <h1 className="page-title">🚨 Error Reports</h1>

            {error && <div className="alert alert-danger">{error}</div>}

            <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <div>
                        <label htmlFor="severity-filter" style={{ marginRight: '0.5rem' }}>Filter by severity:</label>
                        <select
                            id="severity-filter"
                            value={filter}
                            onChange={(e) => setFilter(e.target.value)}
                            style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ddd' }}
                        >
                            <option value="all">All Errors</option>
                            <option value="critical">Critical Only</option>
                            <option value="warning">Warnings Only</option>
                            <option value="info">Info Only</option>
                        </select>
                    </div>
                    <button className="button button-secondary" onClick={loadErrors}>
                        🔄 Refresh
                    </button>
                </div>
            </div>

            {errors.length === 0 ? (
                <div className="alert alert-info">
                    ✓ No errors found in the last 24 hours
                </div>
            ) : (
                <ul className="error-list">
                    {errors.map((error: any, idx) => (
                        <li key={idx}>
                            <div
                                className="error-item"
                                style={{
                                    borderLeftColor: getSeverityColor(error.severity),
                                    background: getSeverityBackground(error.severity),
                                }}
                            >
                                <div className="error-message">
                                    [{error.severity.toUpperCase()}] {error.error_type}
                                </div>
                                <div className="error-details">
                                    {error.error_message}
                                </div>
                                <div className="error-details" style={{ marginTop: '0.5rem' }}>
                                    Component: <strong>{error.component}</strong>
                                    {error.platform && ` • Platform: ${error.platform}`}
                                    {error.details && ` • Details: ${JSON.stringify(error.details)}`}
                                </div>
                                <div className="error-details" style={{ marginTop: '0.5rem', color: '#999' }}>
                                    {new Date(error.timestamp).toLocaleString()}
                                </div>
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}
