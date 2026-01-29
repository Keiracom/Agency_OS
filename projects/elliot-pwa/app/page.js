export default function Home() {
  return (
    <main style={{
      minHeight: '100vh',
      padding: '24px',
      maxWidth: '400px',
      margin: '0 auto'
    }}>
      <h1 style={{
        fontSize: '28px',
        fontWeight: '600',
        marginBottom: '32px',
        textAlign: 'center'
      }}>
        🤖 Elliot Status
      </h1>
      
      <div style={{
        background: '#252542',
        borderRadius: '16px',
        padding: '20px',
        marginBottom: '16px'
      }}>
        <div style={{fontSize: '14px', color: '#888', marginBottom: '8px'}}>Status</div>
        <div style={{fontSize: '24px', fontWeight: '600', color: '#4ade80'}}>● Online</div>
      </div>

      <div style={{
        background: '#252542',
        borderRadius: '16px',
        padding: '20px',
        marginBottom: '16px'
      }}>
        <div style={{fontSize: '14px', color: '#888', marginBottom: '8px'}}>Model</div>
        <div style={{fontSize: '20px', fontWeight: '500'}}>Claude Opus</div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '16px',
        marginBottom: '16px'
      }}>
        <div style={{
          background: '#252542',
          borderRadius: '16px',
          padding: '20px'
        }}>
          <div style={{fontSize: '14px', color: '#888', marginBottom: '8px'}}>Context</div>
          <div style={{fontSize: '28px', fontWeight: '600'}}>12%</div>
        </div>
        <div style={{
          background: '#252542',
          borderRadius: '16px',
          padding: '20px'
        }}>
          <div style={{fontSize: '14px', color: '#888', marginBottom: '8px'}}>Tasks Today</div>
          <div style={{fontSize: '28px', fontWeight: '600'}}>7</div>
        </div>
      </div>

      <div style={{
        textAlign: 'center',
        color: '#666',
        fontSize: '12px',
        marginTop: '32px'
      }}>
        Last updated: {new Date().toLocaleTimeString()}
      </div>
    </main>
  )
}
