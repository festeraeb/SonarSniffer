import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'

export default function Dashboard() {
    const [data, setData] = useState({
        total_errors: 0,
        critical_errors: 0,
        total_jobs: 0,
        successful_jobs: 0,
        failed_jobs: 0,
        total_records_processed: 0,
        parsers_used: {},
        encoders_used: {},
        benchmarks: {}
    })
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        loadDashboard()
        const interval = setInterval(loadDashboard, 5000) // Refresh every 5 seconds
        return () => clearInterval(interval)
    }, [])

    const loadDashboard = async () => {
        try {
            const result = await invoke('get_dashboard_data') as any
            setData(result)
            setError(null)
        } catch (err) {
            console.error('Failed to load dashboard:', err)
            setError(String(err))
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return <div className="spinner"></div>
    }

    return (
        <div className="page">
            <h1 className="page-title">📊 Dashboard</h1>

            {error && <div className="alert alert-danger">{error}</div>}

            <div className="grid">
                <div className="metric-card">
                    <div className="metric-label">Total Errors (24h)</div>
                    <div className="metric-value" style={{ color: data.total_errors > 0 ? '#dc3545' : '#28a745' }}>
                        {data.total_errors}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#666' }}>
                        {data.critical_errors > 0 && `${data.critical_errors} critical`}
                    </div>
                </div>

                <div className="metric-card">
                    <div className="metric-label">Job Execution</div>
                    <div className="metric-value" style={{ color: '#28a745' }}>
                        {data.successful_jobs}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#666' }}>
                        {data.successful_jobs + data.failed_jobs > 0
                            ? `Success rate: ${Math.round((data.successful_jobs / (data.successful_jobs + data.failed_jobs)) * 100)}%`
                            : 'No jobs yet'
                        }
                    </div>
                </div>

                <div className="metric-card">
                    <div className="metric-label">Records Processed</div>
                    <div className="metric-value">
                        {(data.total_records_processed / 1000).toFixed(1)}K
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#666' }}>
                        Total sonar records
                    </div>
                </div>
            </div>

            <div className="card">
                <div className="card-title">🦀 Parsers Used</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                    {Object.entries(data.parsers_used).map(([parser, count]: any) => (
                        <div key={parser} style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                            <div style={{ fontWeight: 'bold' }}>{parser}</div>
                            <div style={{ fontSize: '1.5rem', color: '#667eea', fontWeight: 'bold' }}>
                                {count}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="card">
                <div className="card-title">🎥 Encoders Used</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                    {Object.entries(data.encoders_used).map(([encoder, count]: any) => (
                        <div key={encoder} style={{ padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                            <div style={{ fontWeight: 'bold' }}>{encoder}</div>
                            <div style={{ fontSize: '1.5rem', color: '#667eea', fontWeight: 'bold' }}>
                                {count}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <button className="button mt-2" onClick={loadDashboard}>
                🔄 Refresh Now
            </button>
        </div>
    )
}
