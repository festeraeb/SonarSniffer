import { useState } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import { open } from '@tauri-apps/api/dialog'

export default function ProcessVideo() {
    const [formData, setFormData] = useState({
        input_path: '',
        output_path: '',
        parser: 'rust',
        encoder: 'gstreamer',
    })
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<any>(null)
    const [error, setError] = useState<string | null>(null)

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target
        setFormData(prev => ({ ...prev, [name]: value }))
    }

    const selectInputFile = async () => {
        const file = await open({ multiple: false, filters: [{ name: 'RSD Files', extensions: ['rsd'] }] })
        if (file && typeof file === 'string') {
            setFormData(prev => ({ ...prev, input_path: file }))
        }
    }

    const selectOutputFile = async () => {
        const file = await open({ multiple: false, save: true, filters: [{ name: 'Video Files', extensions: ['mp4', 'mkv'] }] })
        if (file && typeof file === 'string') {
            setFormData(prev => ({ ...prev, output_path: file }))
        }
    }

    const handleProcessVideo = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!formData.input_path || !formData.output_path) {
            setError('Please select both input and output files')
            return
        }

        setLoading(true)
        setError(null)
        setResult(null)

        try {
            const response = await invoke('process_video', formData) as any
            setResult(response)
            setError(null)
            // Reset form
            setFormData({
                input_path: '',
                output_path: '',
                parser: 'rust',
                encoder: 'gstreamer',
            })
        } catch (err) {
            console.error('Processing failed:', err)
            setError(String(err))
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="page">
            <h1 className="page-title">🎬 Process Video</h1>

            <div className="card">
                <div className="card-title">Video Processing Options</div>

                {error && <div className="alert alert-danger">{error}</div>}
                {result && (
                    <div className="alert alert-success">
                        ✓ Processing completed successfully!
                        <div className="error-details" style={{ color: '#155724', marginTop: '0.5rem' }}>
                            Records processed: {result.records_processed?.toLocaleString() || 'N/A'}
                            <br />
                            Duration: {result.duration_ms}ms
                        </div>
                    </div>
                )}

                <form onSubmit={handleProcessVideo}>
                    <div className="form-group">
                        <label htmlFor="input_path">Input RSD File *</label>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <input
                                type="text"
                                id="input_path"
                                name="input_path"
                                value={formData.input_path}
                                readOnly
                                placeholder="Click browse to select RSD file"
                            />
                            <button type="button" className="button button-secondary" onClick={selectInputFile}>
                                Browse
                            </button>
                        </div>
                    </div>

                    <div className="form-group">
                        <label htmlFor="output_path">Output Video File *</label>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <input
                                type="text"
                                id="output_path"
                                name="output_path"
                                value={formData.output_path}
                                readOnly
                                placeholder="Click browse to select output location"
                            />
                            <button type="button" className="button button-secondary" onClick={selectOutputFile}>
                                Browse
                            </button>
                        </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div className="form-group">
                            <label htmlFor="parser">Parser</label>
                            <select
                                id="parser"
                                name="parser"
                                value={formData.parser}
                                onChange={handleInputChange}
                            >
                                <option value="rust">🦀 Rust (Faster)</option>
                                <option value="python">🐍 Python (Standard)</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label htmlFor="encoder">Encoder</label>
                            <select
                                id="encoder"
                                name="encoder"
                                value={formData.encoder}
                                onChange={handleInputChange}
                            >
                                <option value="gstreamer">GStreamer (Hardware accelerated)</option>
                                <option value="ffmpeg">FFmpeg (Software)</option>
                            </select>
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="button"
                        disabled={loading}
                        style={{ width: '100%', marginTop: '1rem', opacity: loading ? 0.6 : 1, cursor: loading ? 'not-allowed' : 'pointer' }}
                    >
                        {loading ? '⏳ Processing...' : '▶️ Start Processing'}
                    </button>
                </form>
            </div>

            <div className="card mt-2">
                <div className="card-title">ℹ️ Information</div>
                <p>Select an RSD sonar file and a destination for the encoded video.</p>
                <p style={{ marginTop: '0.5rem' }}>
                    <strong>Parser:</strong> Rust is faster but Python provides better compatibility.
                </p>
                <p style={{ marginTop: '0.5rem' }}>
                    <strong>Encoder:</strong> GStreamer uses hardware acceleration if available, FFmpeg uses software encoding.
                </p>
            </div>
        </div>
    )
}
