import React, { useState, useEffect, useRef } from 'react';

import './index.css';
import { useSession } from './hooks/useSession';
import { sendChat, getHistory, clearChat, getSessionInfo, setName, getMe } from './utils/api';
import UploadZone from './components/UploadZone';
import SummaryPanel from './components/SummaryPanel';
import { Message, Typing } from './components/MessageBubble';
import AuthModal from './components/AuthModal';

function Welcome() {
  return (
    <div className="welcome">
      <div className="welcome-emblem">◈</div>
      <h1 className="welcome-title">Folio AI</h1>
      <p className="welcome-sub">
        Upload any PDF and have an intelligent conversation about its contents.
        Get summaries, ask questions, extract insights instantly.
      </p>
      <div className="steps">
        {[['1','Upload a PDF'],['2','Tell me your name'],['3','Ask anything']].map(([n,l]) => (
          <div key={n} className="step">
            <span className="step-n">{n}</span>{l}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const sessionId = useSession();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activePdf, setActivePdf] = useState(null);
  const [pdfs, setPdfs] = useState([]);
  const [userName, setUserName] = useState('');
  const [nameInput, setNameInput] = useState('');
  const [showNamePrompt, setShowNamePrompt] = useState(false);
  const [authUser, setAuthUser] = useState(null);
  const [showAuth, setShowAuth] = useState(false);
  const [ready, setReady] = useState(false);
  const bottomRef = useRef();

  // Fixed: scroll functionality directly in useEffect
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    (async () => {
      try {
        const token = localStorage.getItem('token');
        if (token) {
          const r = await getMe().catch(() => null);
          if (r) setAuthUser(r.data);
        }
        const si = await getSessionInfo(sessionId);
        if (si.data.user_name) setUserName(si.data.user_name);
        if (si.data.active_pdf) setActivePdf(si.data.active_pdf);

        const hist = await getHistory(sessionId);
        if (hist.data.messages?.length) {
          setMessages(hist.data.messages);
          if (hist.data.pdf && !si.data.active_pdf) setActivePdf(hist.data.pdf);
        } else {
          setShowNamePrompt(true);
        }
      } catch { setShowNamePrompt(true); }
      finally { setReady(true); }
    })();
  }, [sessionId]);

  const handleUpload = (data) => {
    const pdf = { pdf_id: data.pdf_id, file_name: data.file_name, page_count: data.page_count };
    setPdfs(prev => [pdf, ...prev.filter(p => p.pdf_id !== pdf.pdf_id)]);
    setActivePdf(pdf);
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: `**"${data.file_name}"** uploaded successfully (${data.page_count} pages, ${data.chunk_count} chunks).\n\nSummaries are being generated in the background. You can start asking questions now!`,
      timestamp: new Date().toISOString(),
    }]);
  };

  const handleSetName = async () => {
    const n = nameInput.trim();
    if (!n) return;
    await setName(sessionId, n).catch(() => {});
    const capitalized = n.charAt(0).toUpperCase() + n.slice(1);
    setUserName(capitalized);
    setShowNamePrompt(false);
    const greeting = activePdf
      ? `Hello, **${capitalized}**! 👋 I see you have **"${activePdf.file_name}"** loaded. What would you like to know about it?`
      : `Hello, **${capitalized}**! 👋 I'm Folio, your AI document assistant. Upload a PDF from the sidebar and I'll help you understand it completely.`;
    setMessages(prev => [...prev, { role: 'assistant', content: greeting, timestamp: new Date().toISOString() }]);
  };

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setMessages(prev => [...prev, { role: 'user', content: text, timestamp: new Date().toISOString() }]);
    setInput('');
    setLoading(true);
    try {
      const res = await sendChat(sessionId, text, activePdf?.pdf_id);
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.reply, timestamp: new Date().toISOString() }]);
      if (res.data.user_name && !userName) setUserName(res.data.user_name);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '⚠ Failed to connect to backend. Make sure the FastAPI server is running on port 8000.',
        timestamp: new Date().toISOString(),
      }]);
    } finally { setLoading(false); }
  };

  const handleClear = async () => {
    if (!window.confirm('Clear this conversation?')) return;
    await clearChat(sessionId).catch(() => {});
    setMessages([]);
    setShowNamePrompt(!userName);
  };

  const onKey = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } };

  if (!ready) return (
    <div className="loading-screen">
      <div className="loading-logo">F</div>
      <div className="loading-text">Initializing…</div>
    </div>
  );

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand">
            <div className="brand-mark">F</div>
            <span className="brand-name">Folio</span>
          </div>
          <div className="brand-version">AI Document Intelligence</div>
        </div>

        <UploadZone sessionId={sessionId} onUpload={handleUpload} />

        {pdfs.length > 0 && (
          <div className="doc-list">
            <div className="list-label">Documents</div>
            {pdfs.map(p => (
              <div key={p.pdf_id}
                className={`doc-item${activePdf?.pdf_id === p.pdf_id ? ' active' : ''}`}
                onClick={() => setActivePdf(p)}>
                <div className="doc-icon">📄</div>
                <div>
                  <div className="doc-name">{p.file_name}</div>
                  <div className="doc-meta">{p.page_count} pages</div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div style={{ flex: 1 }} />

        <div className="sidebar-foot">
          {authUser ? (
            <div className="user-card">
              <div className="user-avatar">{(authUser.display_name || authUser.username)[0].toUpperCase()}</div>
              <div>
                <div className="user-name-txt">{authUser.display_name || authUser.username}</div>
                <div className="user-role-txt">Authenticated</div>
              </div>
              <button className="logout-btn" onClick={() => { localStorage.removeItem('token'); setAuthUser(null); }} title="Sign out">✕</button>
            </div>
          ) : (
            <button className="auth-btn" onClick={() => setShowAuth(true)}>Sign in to save history</button>
          )}
        </div>
      </aside>

      {/* Main */}
      <main className="chat-main">
        <div className="chat-header">
          <div>
            <div className="chat-title">{activePdf ? activePdf.file_name : 'Folio AI'}</div>
            <div className="chat-subtitle">
              {activePdf ? `${activePdf.page_count} pages · context-aware Q&A` : userName ? `Session: ${userName}` : 'Upload a PDF to begin'}
            </div>
          </div>
          <div className="header-actions">
            <div className="status-dot">
              <div className="dot-live" />
              Online
            </div>
            {messages.length > 0 && (
              <button className="icon-btn" onClick={handleClear} title="Clear chat">✕</button>
            )}
          </div>
        </div>

        {activePdf?.pdf_id && <SummaryPanel pdfId={activePdf.pdf_id} />}

        {showNamePrompt && !userName && (
          <div className="name-banner">
            <div className="name-banner-icon">👤</div>
            <div className="name-banner-body">
              <h3>What's your name?</h3>
              <p>I'll remember it throughout our session</p>
              <div className="name-row">
                <input className="name-field" value={nameInput}
                  onChange={e => setNameInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSetName()}
                  placeholder="Enter your name…" autoFocus />
                <button className="btn-primary" onClick={handleSetName} disabled={!nameInput.trim()}>
                  Continue →
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="msgs-wrap">
          {messages.length === 0 && !showNamePrompt
            ? <Welcome />
            : messages.map((m, i) => <Message key={i} msg={m} userName={userName} />)}
          {loading && <Typing />}
          <div ref={bottomRef} />
        </div>

        <div className="input-zone">
          <div className="input-row">
            <textarea className="chat-field" value={input}
              onChange={e => setInput(e.target.value)} onKeyDown={onKey}
              placeholder={activePdf ? `Ask anything about "${activePdf.file_name}"…` : 'Upload a PDF first, then ask questions…'}
              rows={1} />
            <button className="send-btn" onClick={send} disabled={!input.trim() || loading}>→</button>
          </div>
          <div className="input-hint">
            Enter to send · Shift+Enter for newline{userName ? ` · ${userName}` : ''}
          </div>
        </div>
      </main>

      {showAuth && <AuthModal onAuth={u => { setAuthUser(u); setShowAuth(false); }} onClose={() => setShowAuth(false)} />}
    </div>
  );
}