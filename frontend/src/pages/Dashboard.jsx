import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [vendors, setVendors] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [statsRes, vendorsRes] = await Promise.all([
        api.get('/api/dashboard/stats'),
        api.get('/api/vendors'),
      ])
      setStats(statsRes.data.data)
      setVendors(vendorsRes.data.data || [])
    } catch (err) {
      console.error('Failed to load dashboard:', err)
    } finally {
      setLoading(false)
    }
  }

  const triggerScheduler = async () => {
    try {
      await api.post('/api/trigger-scheduler')
      alert('Scheduler job completed!')
      loadData()
    } catch (err) {
      alert('Scheduler failed: ' + (err.response?.data?.detail || err.message))
    }
  }

  if (loading) {
    return <div className="loading"><div className="spinner" /> Loading dashboard...</div>
  }

  const formatCurrency = (val) => `₹${Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`

  const getStatusBadge = (status) => (
    <span className={`badge badge-${(status || '').toLowerCase()}`}>{status || 'N/A'}</span>
  )

  const getVendorTotalDue = (vendor) => {
    return (vendor.dues || []).reduce((sum, d) => sum + Number(d.amount || 0), 0)
  }

  const getMaxOverdue = (vendor) => {
    const dues = vendor.dues || []
    return dues.length ? Math.max(...dues.map(d => d.days_overdue || 0)) : 0
  }

  return (
    <>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Overview of vendor dues and email automation</p>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="card stat-card">
          <div className="stat-value">{stats?.total_vendors || 0}</div>
          <div className="stat-label">Total Vendors</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{formatCurrency(stats?.total_due)}</div>
          <div className="stat-label">Total Due</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{formatCurrency(stats?.pending_due)}</div>
          <div className="stat-label">Pending Due</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{stats?.thread_counts?.WAITING || 0}</div>
          <div className="stat-label">Awaiting Reply</div>
        </div>
      </div>

      {/* Actions */}
      <div className="actions-bar">
        <Link to="/upload" className="btn btn-primary">Upload CSV</Link>
        <button className="btn btn-secondary" onClick={triggerScheduler}>Run Scheduler</button>
      </div>

      {/* Vendors Table */}
      <div className="card">
        <h3 style={{ marginBottom: 12 }}>Vendors</h3>
        {vendors.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon text-muted">No Data</div>
            <p>No vendors yet. Upload a CSV to get started.</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Vendor</th>
                  <th>Company</th>
                  <th>Total Due</th>
                  <th>Max Overdue</th>
                  <th>Email</th>
                </tr>
              </thead>
              <tbody>
                {vendors.map((v) => (
                  <tr key={v.id} className="clickable">
                    <td><Link to={`/vendor/${v.id}`} style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 500 }}>{v.name}</Link></td>
                    <td>{v.company_name || '—'}</td>
                    <td style={{ fontWeight: 600 }}>{formatCurrency(getVendorTotalDue(v))}</td>
                    <td>{getMaxOverdue(v)} days</td>
                    <td style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{v.email}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
