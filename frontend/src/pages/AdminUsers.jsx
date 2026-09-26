import { useEffect, useState } from 'react'
import client from '../api/client'

const emptyForm = { full_name: '', email: '', password: '', role: 'procurement_officer', department: '' }

export default function AdminUsers() {
  const [users, setUsers] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function loadUsers() {
    const response = await client.get('/auth/users')
    setUsers(response.data)
  }

  useEffect(() => { loadUsers().catch(() => setError('Could not load users.')) }, [])

  function updateForm(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function createUser(event) {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      await client.post('/auth/users', form)
      setForm(emptyForm)
      setMessage('User created successfully.')
      await loadUsers()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not create user.')
    }
  }

  async function updateUser(user) {
    const role = window.prompt('Role: admin, procurement_officer, or reviewer', user.role)
    if (!role) return
    const department = window.prompt('Department (leave blank for all departments)', user.department || '')
    try {
      await client.patch(`/auth/users/${user.id}`, { role, department: department || null })
      await loadUsers()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not update user.')
    }
  }

  async function resetPassword(user) {
    const password = window.prompt('Enter a new password (at least 10 characters)')
    if (!password) return
    try {
      await client.post(`/auth/users/${user.id}/reset-password`, { new_password: password })
      setMessage(`Password reset for ${user.email}.`)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not reset password.')
    }
  }

  return (
    <div>
      <div className="topline"><h1>User access</h1></div>
      <div className="subhead">Manage roles and department access for procurement staff and reviewers.</div>

      <div className="panel">
        <div className="panel-title"><span>Create user</span></div>
        <form className="user-form" onSubmit={createUser}>
          <input value={form.full_name} onChange={(e) => updateForm('full_name', e.target.value)} placeholder="Full name" required />
          <input type="email" value={form.email} onChange={(e) => updateForm('email', e.target.value)} placeholder="Email" required />
          <input type="password" minLength="10" value={form.password} onChange={(e) => updateForm('password', e.target.value)} placeholder="Temporary password" required />
          <select value={form.role} onChange={(e) => updateForm('role', e.target.value)}>
            <option value="procurement_officer">Procurement officer</option>
            <option value="reviewer">Reviewer</option>
            <option value="admin">Admin</option>
          </select>
          <input value={form.department} onChange={(e) => updateForm('department', e.target.value)} placeholder="Department" />
          <button className="btn btn-primary">Create user</button>
        </form>
        {message && <div className="success-message">{message}</div>}
        {error && <div className="login-error">{error}</div>}
      </div>

      <div className="panel">
        <div className="panel-title"><span>Users</span></div>
        {users.length === 0 ? <div className="empty-state">No users found.</div> : (
          <table>
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Department</th><th>Actions</th></tr></thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.full_name}</td>
                  <td>{user.email}</td>
                  <td>{user.role.replaceAll('_', ' ')}</td>
                  <td>{user.department || 'All departments'}</td>
                  <td className="user-actions">
                    <button className="link-btn" onClick={() => updateUser(user)}>Edit access</button>
                    <button className="link-btn" onClick={() => resetPassword(user)}>Reset password</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
