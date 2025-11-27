import React from 'react';
import Sidebar from './Sidebar';
import ChatArea from './ChatArea';

const Layout = () => {
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(true);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <div className="flex h-full w-full overflow-hidden" style={{ background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      <div style={{ display: 'flex', height: '100vh', width: '100vw' }}>
        <Sidebar isOpen={isSidebarOpen} />
        <ChatArea toggleSidebar={toggleSidebar} isSidebarOpen={isSidebarOpen} />
      </div>
    </div>
  );
};

export default Layout;
