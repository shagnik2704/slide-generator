import React, { useMemo, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import ComplianceReviewWorkspace from '../components/ComplianceReviewWorkspace';

const STORAGE_KEY = 'adminComplianceReviewPayload';

const readStoredPayload = () => {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    console.error('Failed to read admin compliance review payload:', error);
    return null;
  }
};

export default function AdminComplianceReviewPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [activeIssueId, setActiveIssueId] = useState(null);

  const payload = useMemo(
    () => location.state || readStoredPayload(),
    [location.state]
  );

  const report = payload?.report || payload?.complianceReport;
  const jsonScript = payload?.jsonScript;

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate('/create');
    }
  };

  return (
    <div style={pageStyle}>
      <nav style={navStyle}>
        <button onClick={handleBack} style={backButtonStyle}>
          <ArrowLeft size={17} aria-hidden="true" />
          Back
        </button>
      </nav>
      <main style={mainStyle}>
        {report ? (
          <ComplianceReviewWorkspace
            report={report}
            jsonScript={jsonScript}
            isOpen={true}
            variant="page"
            activeIssueId={activeIssueId}
            onIssueSelect={setActiveIssueId}
          />
        ) : (
          <div style={emptyStateStyle}>
            <h2 style={emptyTitleStyle}>No compliance review loaded</h2>
            <p style={emptyTextStyle}>
              Run an admin compliance check from the create workflow, then open the review workspace from the result.
            </p>
            <Link to="/create" style={primaryLinkStyle}>Go to Create</Link>
          </div>
        )}
      </main>
    </div>
  );
}

const pageStyle = {
  background: 'var(--bg-primary)',
  color: 'var(--text-primary)',
  display: 'flex',
  flexDirection: 'column',
  fontFamily: 'var(--font-sans)',
  height: '100vh',
  minWidth: 0,
  overflowY: 'auto',
};

const navStyle = {
  alignItems: 'center',
  background: 'var(--bg-primary)',
  display: 'flex',
  flexShrink: 0,
  minHeight: '58px',
  padding: '0.65rem 1rem',
};

const backButtonStyle = {
  alignItems: 'center',
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-color)',
  borderRadius: '8px',
  color: 'var(--text-primary)',
  cursor: 'pointer',
  display: 'inline-flex',
  fontSize: '0.9rem',
  fontWeight: 700,
  gap: '0.4rem',
  height: '38px',
  padding: '0 0.8rem',
};

const mainStyle = {
  flex: '0 0 auto',
  minHeight: 0,
  overflow: 'visible',
};

const emptyStateStyle = {
  alignItems: 'center',
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  justifyContent: 'center',
  padding: '2rem',
  textAlign: 'center',
};

const emptyTitleStyle = {
  color: 'var(--text-primary)',
  fontSize: '1.35rem',
  marginBottom: '0.5rem',
};

const emptyTextStyle = {
  color: 'var(--text-secondary)',
  maxWidth: '520px',
  marginBottom: '1rem',
};

const primaryLinkStyle = {
  background: 'var(--accent-primary)',
  borderRadius: '8px',
  color: 'white',
  fontWeight: 700,
  padding: '0.65rem 1rem',
  textDecoration: 'none',
};
