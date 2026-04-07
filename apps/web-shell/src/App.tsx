import { useEffect, useState } from 'react';

export function App() {
  const [health, setHealth] = useState<string>('checking...');
  useEffect(() => {
    fetch('/api/health')
      .then(r => r.json())
      .then(d => setHealth(d.status))
      .catch(e => setHealth(`error: ${e}`));
  }, []);
  return (
    <div style={{ fontFamily: 'sans-serif', padding: 32 }}>
      <h1>分路链式工业互联网系统 V5.0</h1>
      <p>API health: <strong>{health}</strong></p>
      <p style={{ color: '#888' }}>
        This is the foundation web shell. Each lane will mount its own routes here as
        they get built out.
      </p>
    </div>
  );
}
