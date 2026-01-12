import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './components/Login';
import AuthCallback from './components/AuthCallback';
import HomePage from './pages/HomePage';
import UploadPage from './pages/UploadPage';
import OutlineChatPage from './pages/OutlineChatPage';

// Component to handle login route - redirects if already authenticated
function LoginRoute() {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        backgroundColor: 'var(--bg-primary, #f0f0ed)',
      }}>
        <div style={{
          textAlign: 'center',
          color: 'var(--text-primary, #2D3E8E)',
        }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '4px solid var(--border-color, #e0e4ed)',
            borderTop: '4px solid var(--accent-primary, #2D3E8E)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 1rem',
          }}></div>
          <p>Loading...</p>
        </div>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }
  
  if (isAuthenticated) {
    return <Navigate to="/upload" replace />;
  }
  
  return <Login />;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginRoute />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route
            path="/upload"
            element={
              <ProtectedRoute>
                <UploadPage />
              </ProtectedRoute>
            }
          />
          <Route path="/outline-chat" element={<OutlineChatPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;