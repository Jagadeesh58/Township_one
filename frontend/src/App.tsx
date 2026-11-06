import React, { useEffect, useState } from 'react';

export default function App() {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    fetch('/api/v1/health')
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch((err) => console.error(err));
  }, []);

  return (
    <div style={{ padding: '2rem', maxWidth: '600px', margin: '0 auto' }}>
      <h1>Township One</h1>
      <p style={{ color: 'var(--text-muted)' }}>
        Gated township resident app for maintenance, complaints and visitors
      </p>
      <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#fff', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
        <strong>Backend Status:</strong> {health ? health.status : 'Connecting...'}
      </div>
    </div>
  );
}
