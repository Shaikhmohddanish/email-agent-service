import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../lib/api'

export default function VendorDetail() {
  const { id } = useParams()
  const [vendor, setVendor] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [replyText, setReplyText] = useState('')
  const [replyThread, setReplyThread] = useState(null)

  useEffect(() => {
    loadVendor()
  }, [id])

  const loadVendor = async () => {
    try {
      const res = await api.get(`/api/vendors/${id}`)
      setVendor(res.data.data)
    } catch (err) {
      console.error('Failed to load vendor:', err)
    } finally {
      setLoading(false)
    }
  }

  const sendEmail = async () => {
    setSending(true)
    try {
      await api.post(`/api/send-email/${id}`)
      alert('Email sent successfully!')
      loadVendor()
    } catch (err) {
      alert('Failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSending(false)
    }
  }

  const sendReply = async (threadId) => {
    if (!replyText.trim()) return
    try {
      await api.post(`/api/send-reply/${threadId}`, {
        content: replyText,
        thread_id: threadId,
      })
      setReplyText('')
      setReplyThread(null)
      alert('Reply sent!')
      loadVendor()
    } catch (err) {
      alert('Failed: ' + (err.response?.data?.detail || err.message))
    }
  }

  const formatCurrency = (val) => `₹${Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
  const formatDate = (d) => d ? new Date(d).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—'

  if (loading) return <div className="loading"><div className="spinner" /> Loading...</div>
  if (!vendor) return <div className="empty-state"><p>Vendor not found</p></div>

  const threads = vendor.email_threads || []

  return (
    <>
      <Link to="/" className="back-link">← Back to Dashboard</Link>

      {/* Vendor Header */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h2 style={{ fontSize: 20, marginBottom: 4 }}>{vendor.name}</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              {vendor.company_name && `${vendor.company_name} · `}{vendor.email}
              {vendor.phone && ` · ${vendor.phone}`}
            </p>
          </div>
          <button className="btn btn-primary" onClick={sendEmail} disabled={sending}>
            {sending ? 'Sending...' : 'Send Reminder'}
          </button>
        </div>
      </div>

      {/* Dues Table */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h3 style={{ marginBottom: 12 }}>Outstanding Dues</h3>
        {(vendor.dues || []).length === 0 ? (
          <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>No dues recorded.</p>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Branch</th>
                  <th>Amount</th>
                  <th>Due Date</th>
                  <th>Overdue</th>
                  <th>Promised Date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {vendor.dues.map((d) => (
                  <tr key={d.id}>
                    <td>{d.branch_name}</td>
                    <td style={{ fontWeight: 600 }}>{formatCurrency(d.amount)}</td>
                    <td>{d.due_date || '—'}</td>
                    <td>{d.days_overdue || 0} days</td>
                    <td>
                      {d.promised_date ? (
                        <div>
                          <span style={{ color: 'var(--success)', fontWeight: 600 }}>
                            {new Date(d.promised_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                          </span>
                          {d.promised_note && (
                            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>{d.promised_note}</div>
                          )}
                        </div>
                      ) : '—'}
                    </td>
                    <td><span className={`badge badge-${(d.status || '').toLowerCase()}`}>{d.status}</span></td>
                  </tr>
                ))}
                <tr style={{ fontWeight: 700 }}>
                  <td>Total</td>
                  <td>{formatCurrency(vendor.dues.reduce((s, d) => s + Number(d.amount || 0), 0))}</td>
                  <td colSpan={4}></td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Email Threads */}
      <div className="card">
        <h3 style={{ marginBottom: 16 }}>Email Threads</h3>
        {threads.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon text-muted">No Messages</div>
            <p>No email threads yet. Send a reminder to start one.</p>
          </div>
        ) : (
          threads.map((thread) => (
            <div key={thread.id} style={{ marginBottom: 24, padding: 16, background: 'var(--bg)', borderRadius: 'var(--radius)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
                <div>
                  <strong style={{ fontSize: 14 }}>{thread.subject || 'No subject'}</strong>
                  <span className={`badge badge-${(thread.status || '').toLowerCase()}`} style={{ marginLeft: 8 }}>{thread.status}</span>
                </div>
                <button className="btn btn-sm btn-secondary" onClick={() => setReplyThread(replyThread === thread.id ? null : thread.id)}>
                  Reply
                </button>
              </div>

              {/* Messages timeline */}
              <div className="timeline">
                {(thread.messages || []).map((msg) => (
                  <div key={msg.id} className={`timeline-item ${msg.sender === 'VENDOR' ? 'vendor' : ''}`}>
                    <div className="msg-sender">
                      {msg.sender === 'AI' ? 'AI Agent' : msg.sender === 'HUMAN' ? 'You' : 'Vendor'}
                    </div>
                    <div className="msg-content">{msg.content}</div>
                    <div className="msg-time">{formatDate(msg.sent_at)}</div>
                  </div>
                ))}
              </div>

              {/* Reply box */}
              {replyThread === thread.id && (
                <div style={{ marginTop: 12 }}>
                  <textarea
                    className="form-group"
                    style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: 'var(--radius)', minHeight: 80, fontSize: 14 }}
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder="Type your reply..."
                  />
                  <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
                    <button className="btn btn-primary btn-sm" onClick={() => sendReply(thread.id)}>Send Reply</button>
                    <button className="btn btn-secondary btn-sm" onClick={() => { setReplyThread(null); setReplyText(''); }}>Cancel</button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </>
  )
}
