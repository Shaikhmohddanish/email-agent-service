import { useState, useEffect } from 'react'
import api from '../lib/api'

export default function Activities() {
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadActivities()
  }, [])

  const loadActivities = async () => {
    try {
      const res = await api.get('/api/activities?limit=100')
      setActivities(res.data.data || [])
    } catch (err) {
      console.error('Failed to load activities:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (d) => d ? new Date(d).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—'

  const getActionIcon = (action) => {
    const icons = {
      'EMAIL_SENT': 'Send',
      'MANUAL_EMAIL': 'Send',
      'MANUAL_REPLY': 'Reply',
      'FOLLOWUP_SENT': 'Follow-up',
      'CSV_IMPORT': 'Upload',
      'EMAIL_FAILED': 'Failed',
      'REPLY_PAID': 'Paid',
      'REPLY_WILL_PAY': 'Will Pay',
      'REPLY_DISPUTE': 'Disputed',
      'REPLY_QUESTION': 'Question',
      'REPLY_NEEDS_HUMAN': 'Review',
    }
    return icons[action] || 'Action'
  }

  if (loading) return <div className="loading"><div className="spinner" /> Loading activities...</div>

  return (
    <>
      <div className="page-header">
        <h1>Activity Log</h1>
        <p>Chronological log of all system actions</p>
      </div>

      <div className="card">
        {activities.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon text-muted">No Activities</div>
            <p>No activities yet.</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 50 }}></th>
                  <th>Action</th>
                  <th>Vendor</th>
                  <th>Details</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {activities.map((a) => (
                  <tr key={a.id}>
                    <td style={{ textAlign: 'center' }}>{getActionIcon(a.action)}</td>
                    <td>
                      <span className={`badge ${a.action.includes('FAIL') ? 'badge-needs_human' : a.action.includes('PAID') ? 'badge-paid' : 'badge-sent'}`}>
                        {a.action.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td style={{ fontWeight: 500 }}>{a.vendors?.name || '—'}</td>
                    <td style={{ fontSize: 13, color: 'var(--text-secondary)', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {a.details || '—'}
                    </td>
                    <td style={{ fontSize: 13, whiteSpace: 'nowrap' }}>{formatDate(a.created_at)}</td>
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
