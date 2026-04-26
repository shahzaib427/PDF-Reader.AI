import axios from 'axios';


const BASE_URL = "https://pdf-reader-ai-nofr.onrender.com";

const API = axios.create({
  baseURL: BASE_URL,
  timeout: 60000
});

API.interceptors.request.use(cfg => {
  const t = localStorage.getItem('token');
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

export const uploadPDF = (file, sessionId, onProgress) => {
  const fd = new FormData();
  fd.append('pdf', file);
  fd.append('session_id', sessionId);
  return API.post('/upload-pdf', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: e => onProgress && onProgress(Math.round((e.loaded * 100) / e.total)),
  });
};

export const sendChat = (sessionId, message, pdfId) =>
  API.post('/chat', { session_id: sessionId, message, pdf_id: pdfId || null });

export const getHistory = sessionId =>
  API.get('/chat/history', { params: { session_id: sessionId } });

export const clearChat = sessionId =>
  API.delete('/chat/clear', { data: { session_id: sessionId } });

export const getSessionInfo = sessionId =>
  API.get('/chat/session-info', { params: { session_id: sessionId } });

export const setName = (sessionId, name) =>
  API.post('/chat/set-name', { session_id: sessionId, name });

export const getSummary = pdfId =>
  API.get(`/upload-pdf/${pdfId}/summary`);

export const getSessionPDFs = sessionId =>
  API.get(`/upload-pdf/session/${sessionId}`);

export const login = data => API.post('/auth/login', data);
export const register = data => API.post('/auth/register', data);
export const getMe = () => API.get('/auth/me');
