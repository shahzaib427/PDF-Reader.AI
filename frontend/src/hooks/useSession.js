import { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';

export function useSession() {
  const [sessionId] = useState(() => {
    const s = localStorage.getItem('sessionId');
    if (s) return s;
    const n = uuidv4();
    localStorage.setItem('sessionId', n);
    return n;
  });
  return sessionId;
}
