import React, { useState, useRef, useCallback } from 'react';
import { X, Upload, FileText, Folder, Check, Trash2, AlertCircle } from 'lucide-react';

const BatchUploadModal = ({ isOpen, onClose, onUpload }) => {
    const [files, setFiles] = useState([]);
    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef(null);
    const folderInputRef = useRef(null);

    // Counter to handle nested drag events (child elements trigger leave/enter)
    const dragCounter = useRef(0);

    if (!isOpen) return null;

    const handleDragEnter = (e) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter.current++;
        if (dragCounter.current === 1) {
            setIsDragging(true);
        }
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter.current--;
        if (dragCounter.current === 0) {
            setIsDragging(false);
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

    // Helper: Convert FileEntry to File object
    const getFileFromEntry = (fileEntry) => {
        return new Promise((resolve) => fileEntry.file(resolve));
    };

    // Helper: Recursively read all files from a directory
    const readDirectory = async (dirEntry) => {
        const files = [];
        const reader = dirEntry.createReader();

        // Read entries (may need multiple calls for large directories)
        const readEntries = () => new Promise((resolve) => {
            reader.readEntries(resolve);
        });

        let entries = await readEntries();
        while (entries.length > 0) {
            for (const entry of entries) {
                if (entry.isFile) {
                    const file = await getFileFromEntry(entry);
                    files.push(file);
                } else if (entry.isDirectory) {
                    // Recurse into subdirectories
                    const subFiles = await readDirectory(entry);
                    files.push(...subFiles);
                }
            }
            entries = await readEntries(); // Get next batch if any
        }
        return files;
    };

    // Helper: Process a single DataTransferItem
    const processItem = async (item) => {
        const entry = item.webkitGetAsEntry?.();
        if (!entry) {
            // Fallback for browsers without webkitGetAsEntry
            const file = item.getAsFile?.();
            return file ? [file] : [];
        }

        if (entry.isFile) {
            const file = await getFileFromEntry(entry);
            return [file];
        } else if (entry.isDirectory) {
            return await readDirectory(entry);
        }
        return [];
    };

    const handleDrop = async (e) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter.current = 0;
        setIsDragging(false);

        const items = e.dataTransfer.items;
        let allFiles = [];

        // Process all dropped items (files and folders)
        if (items && items.length > 0) {
            const itemPromises = Array.from(items).map(processItem);
            const results = await Promise.all(itemPromises);
            allFiles = results.flat();
        } else {
            // Fallback to dataTransfer.files if items not available
            allFiles = Array.from(e.dataTransfer.files);
        }

        // Filter to only valid extensions
        const validFiles = allFiles.filter(file =>
            file.name.match(/\.(json|docx|odt)$/i)
        );

        if (validFiles.length > 0) {
            setFiles(prev => [...prev, ...validFiles]);
        }
    };

    const handleFileSelect = (e) => {
        const selectedFiles = Array.from(e.target.files).filter(file =>
            file.name.match(/\.(json|docx|odt)$/i)
        );
        setFiles(prev => [...prev, ...selectedFiles]);
    };

    const handleRemoveFile = (index) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleUploadClick = () => {
        if (files.length > 0) {
            onUpload(files);
            setFiles([]); // Clear files after handoff
            onClose();
        }
    };

    // Helper to format file size
    const formatSize = (bytes) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            animation: 'fadeIn 0.2s ease-out'
        }} onClick={onClose}>
            <div style={{
                width: '90%',
                maxWidth: '600px',
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: '1rem',
                border: '1px solid var(--border-color)',
                boxShadow: 'var(--shadow-lg)',
                display: 'flex',
                flexDirection: 'column',
                maxHeight: '85vh',
                overflow: 'hidden',
                animation: 'scaleIn 0.2s ease-out'
            }} onClick={e => e.stopPropagation()}>

                {/* Header */}
                <div style={{
                    padding: '1.25rem',
                    borderBottom: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                }}>
                    <div>
                        <h2 style={{
                            fontSize: '1.1rem',
                            fontWeight: 600,
                            color: 'var(--text-primary)',
                            margin: 0,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}>
                            Batch Compliance Check
                        </h2>
                        <p style={{
                            margin: '0.25rem 0 0',
                            fontSize: '0.85rem',
                            color: 'var(--text-secondary)'
                        }}>
                            Upload multiple scripts to check them in parallel.
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-tertiary)',
                            cursor: 'pointer',
                            padding: '0.5rem',
                            borderRadius: '0.5rem',
                            transition: 'all 0.2s'
                        }}
                        onMouseEnter={e => {
                            e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
                            e.currentTarget.style.color = 'var(--text-primary)';
                        }}
                        onMouseLeave={e => {
                            e.currentTarget.style.backgroundColor = 'transparent';
                            e.currentTarget.style.color = 'var(--text-tertiary)';
                        }}
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div style={{
                    padding: '1.25rem',
                    flex: 1,
                    overflowY: 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '1rem'
                }}>

                    {/* inputs */}
                    <input
                        type="file"
                        ref={fileInputRef}
                        multiple
                        accept=".json,.docx,.odt"
                        style={{ display: 'none' }}
                        onChange={handleFileSelect}
                    />
                    <input
                        type="file"
                        ref={folderInputRef}
                        webkitdirectory="true"
                        directory="true"
                        style={{ display: 'none' }}
                        onChange={handleFileSelect}
                    />

                    {/* Drop Zone */}
                    <div
                        onDragEnter={handleDragEnter}
                        onDragLeave={handleDragLeave}
                        onDragOver={handleDragOver}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                        style={{
                            border: `2px dashed ${isDragging ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                            borderRadius: '0.75rem',
                            padding: '2rem',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '1rem',
                            backgroundColor: isDragging ? 'rgba(var(--accent-primary-rgb), 0.05)' : 'var(--bg-tertiary)',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease'
                        }}
                    >
                        <div style={{
                            width: '48px',
                            height: '48px',
                            borderRadius: '12px',
                            backgroundColor: 'var(--bg-secondary)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: isDragging ? 'var(--accent-primary)' : 'var(--text-secondary)',
                            boxShadow: 'var(--shadow-sm)'
                        }}>
                            <Upload size={24} />
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <p style={{
                                margin: '0 0 0.25rem',
                                fontWeight: 500,
                                color: 'var(--text-primary)'
                            }}>
                                Click to upload or drag and drop
                            </p>
                            <p style={{
                                margin: 0,
                                fontSize: '0.85rem',
                                color: 'var(--text-secondary)'
                            }}>
                                JSON, DOCX or ODT files
                            </p>
                        </div>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    fileInputRef.current?.click();
                                }}
                                style={{
                                    padding: '0.4rem 0.8rem',
                                    fontSize: '0.8rem',
                                    borderRadius: '0.5rem',
                                    border: '1px solid var(--border-color)',
                                    background: 'var(--bg-secondary)',
                                    color: 'var(--text-primary)',
                                    cursor: 'pointer'
                                }}
                            >
                                Select Files
                            </button>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    folderInputRef.current?.click();
                                }}
                                style={{
                                    padding: '0.4rem 0.8rem',
                                    fontSize: '0.8rem',
                                    borderRadius: '0.5rem',
                                    border: '1px solid var(--border-color)',
                                    background: 'var(--bg-secondary)',
                                    color: 'var(--text-primary)',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.25rem'
                                }}
                            >
                                <Folder size={14} />
                                Select Folder
                            </button>
                        </div>
                    </div>

                    {/* File List */}
                    {files.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                fontSize: '0.85rem',
                                color: 'var(--text-secondary)',
                                padding: '0 0.25rem'
                            }}>
                                <span>{files.length} scripts selected</span>
                                <button
                                    onClick={() => setFiles([])}
                                    style={{
                                        border: 'none',
                                        background: 'none',
                                        color: 'var(--accent-error)', // Assuming generic error color variable or red
                                        fontSize: '0.8rem',
                                        cursor: 'pointer',
                                        padding: 0
                                    }}
                                >
                                    Clear All
                                </button>
                            </div>
                            <div style={{
                                maxHeight: '200px',
                                overflowY: 'auto',
                                border: '1px solid var(--border-color)',
                                borderRadius: '0.5rem',
                                background: 'var(--bg-tertiary)'
                            }}>
                                {files.map((file, idx) => (
                                    <div key={idx} style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        padding: '0.75rem',
                                        borderBottom: idx === files.length - 1 ? 'none' : '1px solid var(--border-color)',
                                        background: 'var(--bg-secondary)'
                                    }}>
                                        <FileText size={18} style={{ color: 'var(--accent-primary)', marginRight: '0.75rem' }} />
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <div style={{
                                                fontSize: '0.9rem',
                                                fontWeight: 500,
                                                color: 'var(--text-primary)',
                                                whiteSpace: 'nowrap',
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis'
                                            }}>
                                                {file.name}
                                            </div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                                {formatSize(file.size)}
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => handleRemoveFile(idx)}
                                            style={{
                                                background: 'transparent',
                                                border: 'none',
                                                color: 'var(--text-tertiary)',
                                                cursor: 'pointer',
                                                padding: '0.25rem',
                                                display: 'flex'
                                            }}
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div style={{
                    padding: '1.25rem',
                    borderTop: '1px solid var(--border-color)',
                    display: 'flex',
                    justifyContent: 'flex-end',
                    gap: '0.75rem',
                    background: 'var(--bg-secondary)'
                }}>
                    <button
                        onClick={onClose}
                        style={{
                            padding: '0.6rem 1rem',
                            borderRadius: '0.5rem',
                            border: '1px solid var(--border-color)',
                            background: 'var(--bg-tertiary)',
                            color: 'var(--text-secondary)',
                            fontSize: '0.9rem',
                            fontWeight: 500,
                            cursor: 'pointer'
                        }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleUploadClick}
                        disabled={files.length === 0}
                        style={{
                            padding: '0.6rem 1.25rem',
                            borderRadius: '0.5rem',
                            border: 'none',
                            background: files.length === 0 ? 'var(--bg-tertiary)' : 'var(--accent-primary)',
                            color: files.length === 0 ? 'var(--text-tertiary)' : 'white',
                            fontSize: '0.9rem',
                            fontWeight: 600,
                            cursor: files.length === 0 ? 'not-allowed' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            boxShadow: files.length === 0 ? 'none' : 'var(--shadow-sm)'
                        }}
                    >
                        Run Batch Check
                        {files.length > 0 && <span style={{
                            background: 'rgba(255,255,255,0.2)',
                            padding: '0 0.4rem',
                            borderRadius: '1rem',
                            fontSize: '0.8rem'
                        }}>{files.length}</span>}
                    </button>
                </div>
            </div>
            <style>{`
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes scaleIn {
                    from { transform: scale(0.95); opacity: 0; }
                    to { transform: scale(1); opacity: 1; }
                }
            `}</style>
        </div>
    );
};

export default BatchUploadModal;
