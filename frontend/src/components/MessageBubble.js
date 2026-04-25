import React from 'react';

function renderMarkdown(text) {
  return text.split('\n\n').map((para, i) => {
    const html = para
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>');
    return <p key={i} dangerouslySetInnerHTML={{ __html: html }} />;
  });
}

function fmt(ts) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function Message({ msg, userName }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`msg-row${isUser ? ' user' : ''}`}>
      <div className={`msg-av${isUser ? ' u' : ' ai'}`}>
        {isUser ? (userName?.[0]?.toUpperCase() || '?') : '◈'}
      </div>
      <div>
        <div className={`bubble ${isUser ? 'user' : 'ai'}`}>
          {renderMarkdown(msg.content)}
        </div>
        <div className="msg-time">{fmt(msg.timestamp || Date.now())}</div>
      </div>
    </div>
  );
}

export function Typing() {
  return (
    <div className="typing-row">
      <div className="msg-av ai">◈</div>
      <div className="typing-bubble">
        <div className="tdot" /><div className="tdot" /><div className="tdot" />
      </div>
    </div>
  );
}
