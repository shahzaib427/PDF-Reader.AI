import React, { useState, useRef } from 'react';
import { uploadPDF } from '../utils/api';

export default function UploadZone({ sessionId, onUpload }) {
  const [drag, setDrag] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const ref = useRef();

  const handle = async (file) => {
    if (!file || file.type !== 'application/pdf') { setError('PDF files only'); return; }
    if (file.size > 5 * 1024 * 1024) { setError('Max 5 MB'); return; }
    setError(''); setUploading(true); setProgress(0);
    try {
      const res = await uploadPDF(file, sessionId, setProgress);
      onUpload(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed');
    } finally { setUploading(false); setProgress(0); }
  };

  return (
    <div className="upload-area">
      <div
        className={`drop-zone${drag ? ' drag-over' : ''}${uploading ? ' uploading' : ''}`}
        onDragOver={e => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={e => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files[0]); }}
        onClick={() => !uploading && ref.current.click()}
      >
        <span className="drop-icon">{uploading ? '⏳' : drag ? '📂' : '📜'}</span>
        <div className="drop-title">{uploading ? `Uploading ${progress}%` : 'Drop a PDF'}</div>
        <div className="drop-hint">{uploading ? 'Extracting text…' : 'or click to browse · max 5 MB'}</div>
        {uploading && <div className="progress-bar"><div className="progress-fill" style={{ width: `${progress}%` }} /></div>}
      </div>
      {error && <div className="upload-error">⚠ {error}</div>}
      <input ref={ref} type="file" accept=".pdf" style={{ display: 'none' }} onChange={e => handle(e.target.files[0])} />
    </div>
  );
}
