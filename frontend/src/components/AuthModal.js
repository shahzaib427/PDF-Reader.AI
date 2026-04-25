import React, { useState } from 'react';
import { login, register } from '../utils/api';

export default function AuthModal({ onAuth, onClose }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ username: '', email: '', password: '', display_name: '' });
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const upd = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const submit = async e => {
    e.preventDefault(); setErr(''); setLoading(true);
    try {
      const fn = mode === 'login' ? login : register;
      const res = await fn(form);
      localStorage.setItem('token', res.data.token);
      onAuth(res.data.user);
    } catch (ex) {
      setErr(ex.response?.data?.detail || 'Something went wrong');
    } finally { setLoading(false); }
  };

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-logo">
          <div className="modal-logo-mark">F</div>
          <div className="modal-logo-name">Folio</div>
        </div>
        <div className="modal-title">{mode === 'login' ? 'Welcome back' : 'Create account'}</div>
        <div className="modal-sub">{mode === 'login' ? 'sign in to save your history' : 'join to unlock persistence'}</div>

        {err && <div className="err-box">⚠ {err}</div>}

        <form onSubmit={submit}>
          {mode === 'register' && <>
            <div className="field-group">
              <label className="field-label">Username</label>
              <input className="field-input" value={form.username} onChange={upd('username')} placeholder="cooluser42" required />
            </div>
            <div className="field-group">
              <label className="field-label">Display Name</label>
              <input className="field-input" value={form.display_name} onChange={upd('display_name')} placeholder="Your Name" />
            </div>
          </>}
          <div className="field-group">
            <label className="field-label">Email</label>
            <input className="field-input" type="email" value={form.email} onChange={upd('email')} placeholder="you@example.com" required />
          </div>
          <div className="field-group">
            <label className="field-label">Password</label>
            <input className="field-input" type="password" value={form.password} onChange={upd('password')} placeholder="••••••••" required />
          </div>
          <button className="btn-full" disabled={loading}>
            {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <div className="modal-switch">
          {mode === 'login' ? 'No account? ' : 'Have one? '}
          <button onClick={() => { setMode(m => m === 'login' ? 'register' : 'login'); setErr(''); }}>
            {mode === 'login' ? 'Register' : 'Login'}
          </button>
        </div>
      </div>
    </div>
  );
}
