import { useState, useRef } from 'react'
import api from '../lib/api'

export default function CsvUpload() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef()

  const handleFile = (f) => {
    if (!f) return
    if (!f.name.match(/\.(csv|xlsx|xls)$/i)) {
      setError('Please select a CSV or Excel file')
      return
    }
    setFile(f)
    setError('')
    setResult(null)

    // Preview first few rows (CSV only, Excel shows filename)
    if (f.name.toLowerCase().endsWith('.csv')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        const text = e.target.result
        const lines = text.split('\n').filter(l => l.trim())
        const headers = lines[0].split(',').map(h => h.trim())
        const rows = lines.slice(1, 6).map(l => l.split(',').map(c => c.trim()))
        setPreview({ headers, rows, totalRows: lines.length - 1 })
      }
      reader.readAsText(f)
    } else {
      // Excel files can't be previewed client-side easily
      setPreview({ headers: [], rows: [], totalRows: 0, isExcel: true })
    }
  }

  const upload = async () => {
    if (!file) return
    setUploading(true)
    setError('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await api.post('/api/upload-csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(res.data)
      setFile(null)
      setPreview(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    handleFile(f)
  }

  return (
    <>
      <div className="page-header">
        <h1>Upload CSV / Excel</h1>
        <p>Import vendor dues from a CSV or Excel file</p>
      </div>

      {/* Expected format */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h4 style={{ marginBottom: 8, fontSize: 14 }}>Expected CSV Format</h4>
        <div className="table-container">
          <table style={{ fontSize: 13 }}>
            <thead>
              <tr>
                <th>vendor_name</th>
                <th>vendor_email</th>
                <th>company_name</th>
                <th>branch_name</th>
                <th>amount</th>
                <th>due_date</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Rahul Sharma</td>
                <td>rahul@example.com</td>
                <td>ABC Traders</td>
                <td>Mumbai</td>
                <td>50000</td>
                <td>2025-01-15</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Upload area */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div
          className={`upload-area ${dragging ? 'dragging' : ''}`}
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <div className="upload-icon text-muted">Upload File</div>
          <p>{file ? file.name : 'Drop a CSV or Excel file here or click to browse'}</p>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          style={{ display: 'none' }}
          onChange={(e) => handleFile(e.target.files[0])}
        />
      </div>

      {error && <div className="error-message" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Preview */}
      {preview && (
        <div className="card" style={{ marginBottom: 20 }}>
          {preview.isExcel ? (
            <div style={{ marginTop: 16 }}>
              <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 12 }}>Excel file selected. Preview not available for Excel files — data will be processed on upload.</p>
              <button className="btn btn-primary" onClick={upload} disabled={uploading}>
                {uploading ? 'Uploading...' : 'Upload Excel File'}
              </button>
            </div>
          ) : (
            <>
              <h4 style={{ marginBottom: 8, fontSize: 14 }}>Preview ({preview.totalRows} rows)</h4>
              <div className="table-container">
                <table style={{ fontSize: 13 }}>
                  <thead>
                    <tr>{preview.headers.map((h, i) => <th key={i}>{h}</th>)}</tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row, i) => (
                      <tr key={i}>{row.map((c, j) => <td key={j}>{c}</td>)}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {preview.totalRows > 5 && (
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8 }}>
                  Showing first 5 of {preview.totalRows} rows
                </p>
              )}
              <div style={{ marginTop: 16 }}>
                <button className="btn btn-primary" onClick={upload} disabled={uploading}>
                  {uploading ? 'Uploading...' : `Upload ${preview.totalRows} rows`}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="card" style={{ background: '#f0fff4', borderColor: '#c6f6d5' }}>
          <h4 style={{ color: 'var(--success)', marginBottom: 8 }}>Upload Successful</h4>
          <p style={{ fontSize: 14 }}>
            Processed {result.vendors_processed} vendors and {result.dues_processed} dues.
          </p>
          {result.errors?.length > 0 && (
            <div style={{ marginTop: 8, fontSize: 13, color: 'var(--danger)' }}>
              <p>Errors:</p>
              <ul>{result.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
            </div>
          )}
        </div>
      )}
    </>
  )
}
