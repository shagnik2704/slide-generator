import React, { useState, useRef } from 'react';
import Sidebar from './Sidebar';
import ChatArea from './ChatArea';

const Layout = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const chatAreaRef = useRef(null);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  // Handle staging file from sidebar (stages for preview before upload)
  const handleStageFile = (stagedData) => {
    if (chatAreaRef.current?.setStagedFile) {
      chatAreaRef.current.setStagedFile(stagedData);
    }
  };

  return (
    <div className="flex h-full w-full overflow-hidden" style={{ background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      <div style={{ display: 'flex', height: '100vh', width: '100vw' }}>
        <Sidebar
          isOpen={isSidebarOpen}
          toggleSidebar={toggleSidebar}
          onStageFile={handleStageFile}
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

