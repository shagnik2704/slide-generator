import React, { useState, useRef } from 'react';
import Sidebar from './Sidebar';
import OutlineSidebar from './OutlineSidebar';
import ChatArea from './ChatArea';

const Layout = ({ mode = 'create' }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const chatAreaRef = useRef(null);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  // Handle staging file from sidebar (stages for preview before upload)
  const handleStageFile = (stagedData) => {
    console.log('Layout: handleStageFile called with:', stagedData);
    if (chatAreaRef.current?.setStagedFile) {
      chatAreaRef.current.setStagedFile(stagedData);
      console.log('Layout: setStagedFile called successfully');
    } else {
      console.error('Layout: chatAreaRef.current.setStagedFile is not available');
    }
  };

  // Handle create slides from sidebar
  const handleCreateSlides = () => {
    if (chatAreaRef.current?.handleCreateSlides) {
      chatAreaRef.current.handleCreateSlides();
    }
  };

  // Handle open batch modal
  const handleOpenBatchModal = () => {
    if (chatAreaRef.current?.openBatchModal) {
      chatAreaRef.current.openBatchModal();
    }
  };

  // Handle open batch quality modal
  const handleOpenBatchQualityModal = () => {
    if (chatAreaRef.current?.openBatchQualityModal) {
      chatAreaRef.current.openBatchQualityModal();
    }
  };

  const showSidebar = true;

  return (
    <div className="flex h-full w-full overflow-hidden" style={{ background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      <div style={{ display: 'flex', height: '100vh', width: '100vw' }}>
        {showSidebar && (
          mode === 'outline_chat' ? (
            <OutlineSidebar
              isOpen={isSidebarOpen}
              toggleSidebar={toggleSidebar}
              onStageFile={handleStageFile}
            />
          ) : (
            <Sidebar
              isOpen={isSidebarOpen}
              toggleSidebar={toggleSidebar}
              onStageFile={handleStageFile}
              onCreateSlides={handleCreateSlides}
              onOpenBatchModal={handleOpenBatchModal}
              onOpenBatchQualityModal={handleOpenBatchQualityModal}
            />
          )
        )}
        <ChatArea
          ref={chatAreaRef}
          toggleSidebar={toggleSidebar}
          isSidebarOpen={isSidebarOpen}
          mode={mode}
          showSidebarToggle={showSidebar}
        />
      </div>
    </div>
  );
};

export default Layout;

