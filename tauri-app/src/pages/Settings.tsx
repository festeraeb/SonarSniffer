import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'

export default function Settings() {
    const [settings, setSettings] = useState({
        default_parser: 'rust',
        default_encoder: 'gstreamer',
        enable_telemetry: true,
        telemetry_send_interval_minutes: 5,
        quality_preset: 'high',
        video_fps: 30,
        video_height: 1080,
        hardware_acceleration: true,
    })
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

    useEffect(() => {
        loadSettings()
    }, [])

    const loadSettings = async () => {
        try {
            const result = await invoke('get_settings') as any
            setSettings(result)
        } catch (err) {
            console.error('Failed to load settings:', err)
        } finally {
            setLoading(false)
        }
    }

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value, type } = e.target
        const finalValue = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
        setSettings(prev => ({ ...prev, [name]: finalValue }))
    }

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault()
        setSaving(true)
        setMessage(null)

        try {
            await invoke('update_settings', { settings })
            setMessage({ type: 'success', text: 'Settings saved successfully!' })
        } catch (err) {
            setMessage({ type: 'error', text: String(err) })
        } finally {
            setSaving(false)
        }
    }

    if (loading) {
        return <div className="spinner"></div>
    }

    return (
        <div className="page">
            <h1 className="page-title">⚙️ Settings</h1>

            {message && (
                <div className={`alert alert-${message.type}`}>
                    {message.type === 'success' ? '✓' : '✗'} {message.text}
                </div>
            )}

            <form onSubmit={handleSave}>
                <div className="card">
                    <div className="card-title">Processing Defaults</div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div className="form-group">
                            <label htmlFor="default_parser">Default Parser</label>
                            <select
                                id="default_parser"
                                name="default_parser"
                                value={settings.default_parser}
                                onChange={handleChange}
                            >
                                <option value="rust">🦀 Rust (Faster)</option>
                                <option value="python">🐍 Python (Standard)</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label htmlFor="default_encoder">Default Encoder</label>
                            <select
                                id="default_encoder"
                                name="default_encoder"
                                value={settings.default_encoder}
                                onChange={handleChange}
                            >
                                <option value="gstreamer">GStreamer (Hardware)</option>
                                <option value="ffmpeg">FFmpeg (Software)</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label htmlFor="quality_preset">Quality Preset</label>
                            <select
                                id="quality_preset"
                                name="quality_preset"
                                value={settings.quality_preset}
                                onChange={handleChange}
                            >
                                <option value="low">Low (Fast)</option>
                                <option value="medium">Medium</option>
                                <option value="high">High</option>
                                <option value="ultra">Ultra (Slow)</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label htmlFor="video_fps">Video FPS</label>
                            <input
                                type="number"
                                id="video_fps"
                                name="video_fps"
                                min="1"
                                max="120"
                                value={settings.video_fps}
                                onChange={handleChange}
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="video_height">Video Height (pixels)</label>
                            <input
                                type="number"
                                id="video_height"
                                name="video_height"
                                min="480"
                                max="4320"
                                value={settings.video_height}
                                onChange={handleChange}
                            />
                        </div>

                        <div className="form-group">
                            <label>
                                <input
                                    type="checkbox"
                                    name="hardware_acceleration"
                                    checked={settings.hardware_acceleration}
                                    onChange={handleChange}
                                    style={{ marginRight: '0.5rem' }}
                                />
                                Hardware Acceleration
                            </label>
                        </div>
                    </div>
                </div>

                <div className="card">
                    <div className="card-title">Telemetry & Tracking</div>

                    <div className="form-group">
                        <label>
                            <input
                                type="checkbox"
                                name="enable_telemetry"
                                checked={settings.enable_telemetry}
                                onChange={handleChange}
                                style={{ marginRight: '0.5rem' }}
                            />
                            Enable Telemetry Reporting (Send usage data for beta improvements)
                        </label>
                        <p style={{ fontSize: '0.9rem', color: '#666', marginTop: '0.5rem' }}>
                            Telemetry helps us identify issues and improve the application. Your privacy is important to us.
                        </p>
                    </div>

                    {settings.enable_telemetry && (
                        <div className="form-group">
                            <label htmlFor="telemetry_send_interval_minutes">Telemetry Send Interval (minutes)</label>
                            <input
                                type="number"
                                id="telemetry_send_interval_minutes"
                                name="telemetry_send_interval_minutes"
                                min="1"
                                max="60"
                                value={settings.telemetry_send_interval_minutes}
                                onChange={handleChange}
                            />
                        </div>
                    )}
                </div>

                <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
                    <button
                        type="submit"
                        className="button"
                        disabled={saving}
                        style={{ opacity: saving ? 0.6 : 1, cursor: saving ? 'not-allowed' : 'pointer' }}
                    >
                        {saving ? '💾 Saving...' : '💾 Save Settings'}
                    </button>
                    <button
                        type="button"
                        className="button button-secondary"
                        onClick={loadSettings}
                    >
                        🔄 Reload
                    </button>
                </div>
            </form>

            <div className="card mt-2">
                <div className="card-title">About This Beta</div>
                <p>
                    <strong>Version:</strong> 0.1.0 (Beta)
                </p>
                <p style={{ marginTop: '0.5rem' }}>
                    <strong>Platform:</strong> {navigator.platform}
                </p>
                <p style={{ marginTop: '0.5rem' }}>
                    Thank you for testing SonarSniffer! Your feedback helps us build a better product.
                </p>
            </div>
        </div>
    )
}
