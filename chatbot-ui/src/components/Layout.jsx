import React, { useState, useRef } from 'react';
import Sidebar from './Sidebar';
import ChatArea from './ChatArea';

const Layout = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const chatAreaRef = useRef(null);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  // Handle compliance upload from sidebar
  const handleSidebarComplianceUpload = (file) => {
    if (chatAreaRef.current?.handleSidebarComplianceUpload) {
      chatAreaRef.current.handleSidebarComplianceUpload(file);
    }
  };

  // Handle quality upload from sidebar
  const handleSidebarQualityUpload = (file) => {
    if (chatAreaRef.current?.handleSidebarQualityUpload) {
      chatAreaRef.current.handleSidebarQualityUpload(file);
    }
  };

  // Handle voice upload from sidebar
  const handleSidebarVoiceUpload = (file) => {
    if (chatAreaRef.current?.handleSidebarVoiceUpload) {
      chatAreaRef.current.handleSidebarVoiceUpload(file);
    }
  };

  return (
    <div className="flex h-full w-full overflow-hidden" style={{ background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      <div style={{ display: 'flex', height: '100vh', width: '100vw' }}>
        <Sidebar
          isOpen={isSidebarOpen}
          toggleSidebar={toggleSidebar}
          onComplianceUpload={handleSidebarComplianceUpload}
          onQualityUpload={handleSidebarQualityUpload}
          onVoiceUpload={handleSidebarVoiceUpload}
        />
        <ChatArea
          ref={chatAreaRef}
          toggleSidebar={toggleSidebar}
          isSidebarOpen={isSidebarOpen}
        />
      </div>
    </div>
  );
};

export default Layout;

