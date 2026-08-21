import React, { useState, useEffect } from 'react';
import {
  Users,
  UserPlus,
  Shield,
  ShieldAlert,
  UserCheck,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Mail,
  Calendar,
  Lock
} from 'lucide-react';
import {
  getUsers,
  createUser,
  updateUserRole,
  deactivateUser
} from '../../services/api';

export default function UserManagementPanel({ userRole = 'ADMIN' }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // New User Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [role, setRole] = useState('OPERATOR');
  const [email, setEmail] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getUsers();
      setUsers(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load user registry');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userRole === 'ADMIN') {
      fetchUsers();
    }
  }, [userRole]);

  const handleRoleChange = async (userId, newRole) => {
    try {
      setActionSuccess(null);
      await updateUserRole(userId, newRole);
      setActionSuccess(`User role updated to ${newRole}.`);
      fetchUsers();
    } catch (err) {
      alert(`Role change failed: ${err.message}`);
    }
  };

  const handleDeactivate = async (userId, userName) => {
    if (!window.confirm(`Deactivate user "${userName}"? They will no longer have access.`)) {
      return;
    }
    try {
      setActionSuccess(null);
      await deactivateUser(userId);
      setActionSuccess(`User "${userName}" deactivated.`);
      fetchUsers();
    } catch (err) {
      alert(`Deactivation failed: ${err.message}`);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await createUser({
        username: username.trim(),
        display_name: displayName.trim(),
        role,
        email: email.trim() || null,
        notes: notes.trim() || null
      });
      setModalOpen(false);
      setUsername('');
      setDisplayName('');
      setEmail('');
      setNotes('');
      setRole('OPERATOR');
      setActionSuccess('User successfully registered in identity registry.');
      fetchUsers();
    } catch (err) {
      alert(`User creation failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (userRole !== 'ADMIN') {
    return (
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 text-center text-gray-400">
        <ShieldAlert className="w-8 h-8 text-amber-400 mx-auto mb-2" />
        <h3 className="text-base font-bold text-white">Administrator Access Required</h3>
        <p className="text-xs text-gray-500 mt-1">
          User identity management and multi-admin governance is restricted to Administrators.
        </p>
      </div>
    );
  }

  const adminCount = users.filter(u => u.role === 'ADMIN' && u.is_active).length;

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 shadow-xl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
        <div>
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-white tracking-wide">Multi-Administrator & User Registry</h2>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Manage authorized operators, engineers, and platform administrators ({adminCount} active Admin{adminCount !== 1 ? 's' : ''}).
          </p>
        </div>

        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-indigo-600/20"
        >
          <UserPlus className="w-4 h-4" />
          Add User
        </button>
      </div>

      {actionSuccess && (
        <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-300 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          {actionSuccess}
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Users Table */}
      <div className="mt-6 overflow-x-auto">
        {loading ? (
          <div className="p-8 text-center text-gray-500 text-sm">Loading user registry...</div>
        ) : users.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">No registered users found.</div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-800 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                <th className="py-3 px-4">User</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Email</th>
                <th className="py-3 px-4">Last Login</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 text-sm">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-900/30 transition">
                  <td className="py-3 px-4">
                    <div className="font-medium text-white">{u.display_name}</div>
                    <div className="text-xs text-gray-500">@{u.username}</div>
                  </td>
                  <td className="py-3 px-4">
                    <select
                      value={u.role}
                      onChange={(e) => handleRoleChange(u.id, e.target.value)}
                      disabled={!u.is_active}
                      className={`text-xs font-semibold px-2.5 py-1 rounded border bg-gray-900 focus:outline-none ${
                        u.role === 'ADMIN'
                          ? 'border-purple-500/40 text-purple-300'
                          : 'border-blue-500/40 text-blue-300'
                      }`}
                    >
                      <option value="ADMIN">ADMIN</option>
                      <option value="OPERATOR">OPERATOR</option>
                    </select>
                  </td>
                  <td className="py-3 px-4">
                    {u.is_active ? (
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        Active
                      </span>
                    ) : (
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30">
                        Inactive
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-xs text-gray-400">{u.email || '—'}</td>
                  <td className="py-3 px-4 text-xs text-gray-400">
                    {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : 'Never'}
                  </td>
                  <td className="py-3 px-4 text-right">
                    {u.is_active && (
                      <button
                        onClick={() => handleDeactivate(u.id, u.username)}
                        disabled={u.role === 'ADMIN' && adminCount <= 1}
                        title={u.role === 'ADMIN' && adminCount <= 1 ? 'Cannot deactivate the last active Admin' : 'Deactivate user'}
                        className="p-1.5 text-gray-400 hover:text-red-400 transition disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add User Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-2 text-indigo-400 mb-2">
              <UserPlus className="w-5 h-5" />
              <h3 className="text-lg font-bold text-white">Register New Platform User</h3>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              Add authorized personnel with granular role-based permissions.
            </p>

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Username *</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. jsmith"
                  required
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Full / Display Name *</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="e.g. Jane Smith"
                  required
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Assigned Role *</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="OPERATOR">OPERATOR (Monitoring, Investigations & Work Orders)</option>
                  <option value="ADMIN">ADMIN (Full System Configuration & Governance)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Email Address (Optional)</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. jsmith@factorymind.ai"
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition"
                >
                  {submitting ? 'Creating...' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
