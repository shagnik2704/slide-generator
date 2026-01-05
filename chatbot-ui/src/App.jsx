import React from 'react';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';

function App() {
  return (
    <AuthProvider>
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    </AuthProvider>
  );
}

export default App;