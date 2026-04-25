import React, { useState, useEffect } from 'react';
import { getSummary } from '../utils/api';

export default function SummaryPanel({ pdfId }) {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(true);
  const [tab, setTab] = useState('short');

  useEffect(() => {
    if (!pdfId) return;
    setData(null);
    const fetch = async () => {
      try { const r = await getSummary(pdfId); setData(r.data); } catch {}
    };
    fetch();
    const id = setInterval(async () => {
      try {
        const r = await getSummary(pdfId);
        setData(r.data);
        if (r.data.summary_generated) clearInterval(id);
      } catch {}
    }, 3000);
    return () => clearInterval(id);
  }, [pdfId]);

  if (!pdfId) return null;

  return (
    <div className="summary-strip">
      <button className="summary-toggle" onClick={() => setOpen(o => !o)}>
        <span className="summary-toggle-left">
          ◈ Document Summary
          {data?.summary_generated
            ? <span className="badge badge-ok">✓ Ready</span>
            : <span className="badge badge-wait">⟳ Generating</span>}
        </span>
        <span className="summary-chevron">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="summary-body">
          <div className="sum-tabs">
            <button className={`sum-tab${tab === 'short' ? ' active' : ''}`} onClick={() => setTab('short')}>Short</button>
            <button className={`sum-tab${tab === 'detailed' ? ' active' : ''}`} onClick={() => setTab('detailed')}>Detailed</button>
          </div>
          <p className="sum-text">
            {!data ? 'Loading…'
              : !data.summary_generated ? '🤖 AI is analyzing your document. Usually takes 10–30 seconds…'
              : tab === 'short' ? data.short_summary : data.detailed_summary}
          </p>
        </div>
      )}
    </div>
  );
}
