import { useMemo, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const MAX_CLIENT_FILE_MB = 5;

export default function App() {
  const [file, setFile] = useState(null);
  const [email, setEmail] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [summary, setSummary] = useState('');

  const fileMeta = useMemo(() => {
    if (!file) return 'No file selected';
    return `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
  }, [file]);

  const onSubmit = async (event) => {
    event.preventDefault();
    if (!file || !email) {
      setStatus('error');
      setMessage('Please provide both a sales file and recipient email.');
      return;
    }

    const isSupported = file.name.toLowerCase().endsWith('.csv') || file.name.toLowerCase().endsWith('.xlsx');
    if (!isSupported) {
      setStatus('error');
      setMessage('Unsupported file type. Please upload a .csv or .xlsx file.');
      return;
    }

    if (file.size > MAX_CLIENT_FILE_MB * 1024 * 1024) {
      setStatus('error');
      setMessage(`File exceeds ${MAX_CLIENT_FILE_MB}MB client limit.`);
      return;
    }

    setStatus('loading');
    setSummary('');
    setMessage('Uploading and generating summary...');

    const formData = new FormData();
    formData.append('file', file);

    const headers = {};
    if (apiKey.trim()) {
      headers['X-API-Key'] = apiKey.trim();
    }

    try {
      const response = await fetch(`${API_BASE}/api/summarize?recipient_email=${encodeURIComponent(email)}`, {
        method: 'POST',
        headers,
        body: formData,
      });

      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || 'Request failed.');
      }

      setStatus('success');
      setSummary(result.summary);
      setMessage(result.emailed ? 'Summary generated and email queued.' : 'Summary generated. Email service not configured.');
    } catch (error) {
      setStatus('error');
      setMessage(error.message || 'Unexpected error occurred.');
    }
  };

  return (
    <main className="container">
      <h1>Sales Insight Automator</h1>
      <p>Upload a CSV/XLSX file, generate an AI summary, and send it to leadership.</p>

      <form onSubmit={onSubmit} className="card">
        <label>
          Sales file (.csv or .xlsx)
          <input type="file" accept=".csv,.xlsx" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <small>{fileMeta}</small>
        </label>

        <label>
          Recipient email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="vp-sales@company.com"
          />
        </label>

        <label>
          Optional API Key
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="X-API-Key header"
          />
        </label>

        <button type="submit" disabled={status === 'loading'}>
          {status === 'loading' ? 'Generating...' : 'Generate & Send'}
        </button>
      </form>

      {message && <div className={`alert ${status}`}>{message}</div>}
      {summary && (
        <section className="card summary">
          <h2>Generated Summary</h2>
          <pre>{summary}</pre>
        </section>
      )}
    </main>
  );
}
