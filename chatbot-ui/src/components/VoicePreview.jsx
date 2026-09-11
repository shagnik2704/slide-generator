import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
    Play,
    Pause,
    Download,
    Volume2,
    Clock,
    Sparkles,
    Edit3,
    Check,
    X,
    RotateCcw,
    AlertCircle,
    FileAudio,
    ChevronLeft,
    ChevronRight,
} from 'lucide-react';
import AudioPatchModal from './AudioPatchModal';
import { apiJson } from '../services/api';

const API_URL = import.meta.env.VITE_API_URL || '';

/**
 * Strip markdown markers like **Slide 1** or '''Slide 1''' from titles
 */
function cleanTitle(title) {
    if (!title) return '';
    return String(title)
        .replace(/^\*{2,3}(.*?)\*{2,3}$/, '$1')
        .replace(/^'{3}(.*?)'{3}$/, '$1')
        .replace(/\*{2,3}/g, '')
        .replace(/'{3}/g, '')
        .trim();
}

/**
 * Render narration text with bold formatting (**word** or '''word''' or ***word***) and line breaks.
 * Keeps standard DOM text nodes so user selection (highlight-to-patch) continues to work cleanly.
 */
function renderFormattedText(text) {
    if (!text || typeof text !== 'string') return text;

    const regex = /(\*{2,3}[^*]+?\*{2,3}|'{3}[^']+?'{3}|\n)/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
        if (match.index > lastIndex) {
            parts.push(text.slice(lastIndex, match.index));
        }

        const token = match[0];
        if (token === '\n') {
            parts.push(<br key={`br-${match.index}`} />);
        } else if (token.startsWith('***') && token.endsWith('***')) {
            parts.push(
                <strong key={`b-${match.index}`} style={{ fontWeight: 650, color: 'var(--text-primary)' }}>
                    <em>{token.slice(3, -3)}</em>
                </strong>
            );
        } else if (token.startsWith('**') && token.endsWith('**')) {
            parts.push(
                <strong key={`b-${match.index}`} style={{ fontWeight: 650, color: 'var(--text-primary)' }}>
                    {token.slice(2, -2)}
                </strong>
            );
        } else if (token.startsWith("'''") && token.endsWith("'''")) {
            parts.push(
                <strong key={`b-${match.index}`} style={{ fontWeight: 650, color: 'var(--text-primary)' }}>
                    {token.slice(3, -3)}
                </strong>
            );
        }

        lastIndex = regex.lastIndex;
    }

    if (lastIndex < text.length) {
        parts.push(text.slice(lastIndex));
    }

    return parts.length > 0 ? parts : text;
}

/**
 * VoicePreview - Displays script narration text and audio players
 * Supports:
 * - Seeing the actual narration text for every row
 * - Selecting any word/phrase to patch in the AudioPatchModal
 * - In-place row editing & regeneration (re-records single slide & re-stitches)
 * - Single combined audio player & individual row players
 */
export default function VoicePreview({ voiceData, jsonScript, projectId, isOpen = true }) {
    const [playingSlide, setPlayingSlide] = useState(null);

    // Audio state that can be updated on in-place regeneration
    const initialSlideAudio = voiceData?.audio_urls || voiceData?.slide_audio_urls || {};
    const [localSlideAudio, setLocalSlideAudio] = useState(initialSlideAudio);
    const [localFullAudio, setLocalFullAudio] = useState(voiceData?.audio_url || null);
    const [localZipUrl, setLocalZipUrl] = useState(voiceData?.zip_url || null);

    // Sync with incoming voiceData
    useEffect(() => {
        if (voiceData) {
            setLocalSlideAudio(voiceData.audio_urls || voiceData.slide_audio_urls || {});
            setLocalFullAudio(voiceData.audio_url || null);
            setLocalZipUrl(voiceData.zip_url || null);
        }
    }, [voiceData]);

    // Map slides from jsonScript, voiceData.slides, or static script_{id}.json fallback
    const [slidesMap, setSlidesMap] = useState({});
    useEffect(() => {
        const map = {};
        const slidesList = (jsonScript && Array.isArray(jsonScript.slides) && jsonScript.slides.length > 0)
            ? jsonScript.slides
            : (voiceData && Array.isArray(voiceData.slides) && voiceData.slides.length > 0 ? voiceData.slides : []);

        if (slidesList.length > 0) {
            slidesList.forEach((s, idx) => {
                const num = String(s.slide_number || idx + 1);
                map[num] = {
                    title: s.title || `Slide ${num}`,
                    narration: s.narration || '',
                };
            });
            setSlidesMap(map);
        } else {
            // Fallback: try loading the parsed script from /output/script_{project_id}.json
            const activeProjectId = projectId || voiceData?.project_id;
            if (activeProjectId) {
                const cleanId = String(activeProjectId).replace('project_', '').trim();
                fetch(resolveUrl(`/output/script_${cleanId}.json`))
                    .then((res) => (res.ok ? res.json() : null))
                    .then((data) => {
                        if (data && Array.isArray(data.slides)) {
                            const fetchedMap = {};
                            data.slides.forEach((s, idx) => {
                                const num = String(s.slide_number || idx + 1);
                                fetchedMap[num] = {
                                    title: s.title || `Slide ${num}`,
                                    narration: s.narration || '',
                                };
                            });
                            setSlidesMap(fetchedMap);
                        }
                    })
                    .catch(() => {});
            }
        }
    }, [jsonScript, voiceData, projectId]);

    // Audio Patch Modal state
    const [isPatchModalOpen, setIsPatchModalOpen] = useState(false);
    const [patchModalText, setPatchModalText] = useState('');

    // In-place Row Editing state
    const [editingSlideNum, setEditingSlideNum] = useState(null);
    const [editingText, setEditingText] = useState('');
    const [regeneratingSlideNum, setRegeneratingSlideNum] = useState(null);
    const [regenError, setRegenError] = useState(null);

    // Floating selection tooltip: { text, slideNum, x, y }
    const [selectionTooltip, setSelectionTooltip] = useState(null);
    const previewContainerRef = useRef(null);

    // Derive all unique slide/row numbers sorted numerically
    const allSlideNumbers = useMemo(() => {
        const numbers = new Set([
            ...Object.keys(slidesMap),
            ...Object.keys(localSlideAudio),
        ]);
        if (numbers.size === 0 && voiceData?.total_slides) {
            for (let i = 1; i <= voiceData.total_slides; i++) {
                numbers.add(String(i));
            }
        }
        return Array.from(numbers).sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
    }, [slidesMap, localSlideAudio, voiceData?.total_slides]);

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(5); // 5, 10, 25, or 'all'
    const [jumpInput, setJumpInput] = useState('');

    const totalRows = allSlideNumbers.length;
    const effectivePageSize = pageSize === 'all' ? totalRows : pageSize;
    const totalPages = Math.max(1, Math.ceil(totalRows / (effectivePageSize || 1)));

    // Ensure active page is within bounds
    const activePage = Math.min(Math.max(1, currentPage), totalPages);

    const paginatedSlideNumbers = useMemo(() => {
        if (pageSize === 'all') return allSlideNumbers;
        const startIdx = (activePage - 1) * effectivePageSize;
        return allSlideNumbers.slice(startIdx, startIdx + effectivePageSize);
    }, [allSlideNumbers, activePage, effectivePageSize, pageSize]);

    const startRowIdx = totalRows === 0 ? 0 : (activePage - 1) * effectivePageSize + 1;
    const endRowIdx = pageSize === 'all' ? totalRows : Math.min(activePage * effectivePageSize, totalRows);

    const handlePageChange = (newPage) => {
        const targetPage = Math.min(Math.max(1, newPage), totalPages);
        setCurrentPage(targetPage);
    };

    const handleJumpToRow = (e) => {
        e.preventDefault();
        const rowNum = parseInt(jumpInput, 10);
        if (isNaN(rowNum) || rowNum < 1 || rowNum > totalRows) return;

        const targetIdx = allSlideNumbers.findIndex((n) => parseInt(n, 10) === rowNum);
        if (targetIdx !== -1 && pageSize !== 'all') {
            const targetPage = Math.floor(targetIdx / effectivePageSize) + 1;
            setCurrentPage(targetPage);
        }
        setJumpInput('');
    };

    if (!voiceData || !isOpen) return null;

    const {
        total_slides,
        generated_slides,
        errors,
        duration_estimate,
    } = voiceData;

    const hasSlideAudio = Object.keys(localSlideAudio).length > 0;
    const hasFullAudio = Boolean(localFullAudio);
    const hasRows = allSlideNumbers.length > 0;

    const handlePlay = (slideNum, audioRef) => {
        if (playingSlide === slideNum) {
            audioRef.pause();
            setPlayingSlide(null);
        } else {
            // Pause any currently playing audio
            document.querySelectorAll('audio').forEach((a) => a.pause());
            audioRef.play();
            setPlayingSlide(slideNum);
        }
    };

    const handleEnded = () => {
        setPlayingSlide(null);
    };

    // Text selection detection inside row narration
    const handleMouseUp = (slideNum) => {
        const selection = window.getSelection();
        const selectedText = selection.toString().trim();
        if (selectedText && selectedText.length > 0 && selectedText.length < 250) {
            try {
                const range = selection.getRangeAt(0);
                const rect = range.getBoundingClientRect();
                setSelectionTooltip({
                    text: selectedText,
                    slideNum,
                    x: rect.left + rect.width / 2,
                    y: rect.top - 10,
                });
            } catch (e) {
                setSelectionTooltip(null);
            }
        } else {
            setSelectionTooltip(null);
        }
    };

    // Open Patch Modal pre-filled
    const handleOpenPatch = (textToPatch) => {
        setPatchModalText(textToPatch || '');
        setIsPatchModalOpen(true);
        setSelectionTooltip(null);
    };

    // Start editing row inline
    const handleStartEdit = (slideNum, currentNarration) => {
        setEditingSlideNum(slideNum);
        setEditingText(currentNarration || '');
        setRegenError(null);
    };

    // Cancel inline editing
    const handleCancelEdit = () => {
        setEditingSlideNum(null);
        setEditingText('');
        setRegenError(null);
    };

    // Save and re-record row (or generate row clip on demand)
    const handleSaveAndRegenerate = async (slideNum, fallbackText = null) => {
        const textToUse = (editingSlideNum === slideNum ? editingText : (fallbackText || editingText || '')).trim();
        if (!textToUse) return;

        setRegeneratingSlideNum(slideNum);
        setRegenError(null);

        const activeProjectId = projectId || voiceData?.project_id;

        try {
            if (activeProjectId) {
                // Call dedicated regenerate endpoint that updates slide & re-stitches full audio
                const res = await apiJson('/regenerate_slide', {
                    method: 'POST',
                    body: JSON.stringify({
                        project_id: activeProjectId,
                        slide_number: parseInt(slideNum, 10),
                        text: textToUse,
                    }),
                });

                if (res.success) {
                    // Update slide audio URL (with cache-busting timestamp)
                    const bustUrl = `${res.slide_audio_url}?t=${Date.now()}`;
                    setLocalSlideAudio((prev) => ({
                        ...prev,
                        [slideNum]: bustUrl,
                    }));

                    if (res.full_audio_url) {
                        setLocalFullAudio(`${res.full_audio_url}?t=${Date.now()}`);
                    }
                    if (res.zip_url) {
                        setLocalZipUrl(`${res.zip_url}?t=${Date.now()}`);
                    }

                    // Update local narration text
                    setSlidesMap((prev) => ({
                        ...prev,
                        [slideNum]: {
                            ...prev[slideNum],
                            narration: textToUse,
                        },
                    }));

                    setEditingSlideNum(null);
                } else {
                    setRegenError(res.error || 'Failed to regenerate row');
                }
            } else {
                // Fallback to standalone patch if no projectId is available
                const res = await apiJson('/generate_voice_patch', {
                    method: 'POST',
                    body: JSON.stringify({
                        text: textToUse,
                    }),
                });

                if (res.success) {
                    setLocalSlideAudio((prev) => ({
                        ...prev,
                        [slideNum]: `${res.audio_url}?t=${Date.now()}`,
                    }));
                    setSlidesMap((prev) => ({
                        ...prev,
                        [slideNum]: {
                            ...prev[slideNum],
                            narration: textToUse,
                        },
                    }));
                    setEditingSlideNum(null);
                }
            }
        } catch (err) {
            console.error('Failed to regenerate slide:', err);
            setRegenError(err.message || 'Error re-recording row');
        } finally {
            setRegeneratingSlideNum(null);
        }
    };

    const resolveUrl = (url) => {
        if (!url) return '';
        if (url.startsWith('http')) return url;
        return `${API_URL}${url}`;
    };

    return (
        <div
            ref={previewContainerRef}
            style={{
                marginTop: '1rem',
                padding: '1.25rem',
                background: 'var(--bg-secondary)',
                borderRadius: '0.85rem',
                border: '1px solid var(--border-color)',
                position: 'relative',
            }}
        >
            {/* Header */}
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '1.25rem',
                    paddingBottom: '0.85rem',
                    borderBottom: '1px solid var(--border-color)',
                    flexWrap: 'wrap',
                    gap: '0.75rem',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                    <Volume2 size={20} style={{ color: 'var(--accent-primary)' }} />
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '1rem' }}>
                        Audio Studio & Review
                    </span>
                    <span
                        style={{
                            fontSize: '0.8rem',
                            color: 'var(--text-secondary)',
                            background: 'var(--bg-tertiary)',
                            padding: '0.2rem 0.55rem',
                            borderRadius: '0.4rem',
                        }}
                    >
                        {generated_slides == null ? `${total_slides || allSlideNumbers.length} Rows` : `${generated_slides}/${total_slides || allSlideNumbers.length} Rows`}
                    </span>
                    {duration_estimate && (
                        <span
                            style={{
                                fontSize: '0.8rem',
                                color: 'var(--accent-primary)',
                                background: 'var(--bg-tertiary)',
                                padding: '0.2rem 0.55rem',
                                borderRadius: '0.4rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                fontWeight: 500,
                            }}
                        >
                            <Clock size={13} />
                            {duration_estimate}
                        </span>
                    )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <button
                        onClick={() => handleOpenPatch('')}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                            padding: '0.45rem 0.85rem',
                            background: 'var(--bg-tertiary)',
                            border: '1px solid var(--border-color)',
                            color: 'var(--text-primary)',
                            borderRadius: '0.5rem',
                            fontSize: '0.82rem',
                            fontWeight: 500,
                            cursor: 'pointer',
                            transition: 'all 0.15s ease',
                        }}
                        title="Open standalone audio patch sandbox"
                    >
                        <Sparkles size={14} style={{ color: 'var(--accent-primary)' }} />
                        Audio Patch Sandbox
                    </button>

                    {(localZipUrl || localFullAudio) && (
                        <a
                            href={resolveUrl(localZipUrl || localFullAudio)}
                            download
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.4rem',
                                padding: '0.45rem 0.95rem',
                                background: 'var(--accent-primary)',
                                color: 'white',
                                borderRadius: '0.5rem',
                                textDecoration: 'none',
                                fontSize: '0.82rem',
                                fontWeight: 500,
                            }}
                        >
                            <Download size={15} />
                            {localZipUrl ? 'Download All (ZIP)' : 'Download Audio'}
                        </a>
                    )}
                </div>
            </div>

            {/* Combined Audio - Single Player Card */}
            {hasFullAudio && (
                <div style={{ marginBottom: '1.25rem' }}>
                    <AudioPlayer
                        slideNum="full"
                        title="Full Continuous Narration"
                        url={resolveUrl(localFullAudio)}
                        isPlaying={playingSlide === 'full'}
                        onPlay={handlePlay}
                        onEnded={handleEnded}
                        isCombined={true}
                    />
                </div>
            )}

            {/* Per-Slide / Script Rows Section */}
            {hasRows && (
                <div>
                    {/* Rows Section Toolbar: Count, Per-page selector & mini-pagination */}
                    <div
                        style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: '0.85rem',
                            padding: '0.6rem 0.85rem',
                            background: 'var(--bg-tertiary)',
                            borderRadius: '0.6rem',
                            border: '1px solid var(--border-color)',
                            flexWrap: 'wrap',
                            gap: '0.75rem',
                        }}
                    >
                        {/* Left: Row Count & Showing Range */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                                Script Rows & Studio ({totalRows})
                            </span>
                            <span
                                style={{
                                    fontSize: '0.76rem',
                                    color: 'var(--text-secondary)',
                                    background: 'var(--bg-secondary)',
                                    padding: '0.18rem 0.55rem',
                                    borderRadius: '0.35rem',
                                    border: '1px solid var(--border-color)',
                                    fontWeight: 500,
                                }}
                            >
                                Showing {startRowIdx}–{endRowIdx} of {totalRows}
                            </span>
                        </div>

                        {/* Right: Page Size Selector & Quick Prev/Next */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                            {/* Page Size Pills */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Per page:</span>
                                {[5, 10, 25, 'all'].map((size) => {
                                    const isActive = pageSize === size;
                                    return (
                                        <button
                                            key={String(size)}
                                            onClick={() => {
                                                setPageSize(size);
                                                setCurrentPage(1);
                                            }}
                                            style={{
                                                padding: '0.2rem 0.55rem',
                                                fontSize: '0.75rem',
                                                fontWeight: isActive ? 600 : 400,
                                                borderRadius: '0.35rem',
                                                border: isActive ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)',
                                                background: isActive ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                                                color: isActive ? 'white' : 'var(--text-secondary)',
                                                cursor: 'pointer',
                                                transition: 'all 0.15s ease',
                                            }}
                                        >
                                            {size === 'all' ? 'All' : size}
                                        </button>
                                    );
                                })}
                            </div>

                            {/* Mini Page Switcher (if multiple pages) */}
                            {pageSize !== 'all' && totalPages > 1 && (
                                <div
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.25rem',
                                        borderLeft: '1px solid var(--border-color)',
                                        paddingLeft: '0.6rem',
                                    }}
                                >
                                    <button
                                        onClick={() => handlePageChange(activePage - 1)}
                                        disabled={activePage <= 1}
                                        aria-label="Previous Page"
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            width: '24px',
                                            height: '24px',
                                            borderRadius: '0.35rem',
                                            border: '1px solid var(--border-color)',
                                            background: 'var(--bg-secondary)',
                                            color: activePage <= 1 ? 'var(--text-tertiary, #888)' : 'var(--text-primary)',
                                            opacity: activePage <= 1 ? 0.4 : 1,
                                            cursor: activePage <= 1 ? 'not-allowed' : 'pointer',
                                        }}
                                    >
                                        <ChevronLeft size={14} />
                                    </button>
                                    <span style={{ fontSize: '0.78rem', color: 'var(--text-primary)', fontWeight: 500, minWidth: '4.5rem', textAlign: 'center' }}>
                                        {activePage} / {totalPages}
                                    </span>
                                    <button
                                        onClick={() => handlePageChange(activePage + 1)}
                                        disabled={activePage >= totalPages}
                                        aria-label="Next Page"
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            width: '24px',
                                            height: '24px',
                                            borderRadius: '0.35rem',
                                            border: '1px solid var(--border-color)',
                                            background: 'var(--bg-secondary)',
                                            color: activePage >= totalPages ? 'var(--text-tertiary, #888)' : 'var(--text-primary)',
                                            opacity: activePage >= totalPages ? 0.4 : 1,
                                            cursor: activePage >= totalPages ? 'not-allowed' : 'pointer',
                                        }}
                                    >
                                        <ChevronRight size={14} />
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Paginated Script Rows */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                        {paginatedSlideNumbers.map((slideNum) => {
                            const url = localSlideAudio[slideNum];
                            const slideInfo = slidesMap[slideNum] || { title: `Slide ${slideNum}`, narration: '' };
                            const isEditing = editingSlideNum === slideNum;
                            const isRegenerating = regeneratingSlideNum === slideNum;

                            return (
                                <div
                                    key={slideNum}
                                    style={{
                                        padding: '1rem',
                                        borderRadius: '0.75rem',
                                        background: 'var(--bg-tertiary)',
                                        border: isEditing ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: '0.75rem',
                                        transition: 'all 0.2s ease',
                                    }}
                                >
                                    {/* Row Header */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                            <span
                                                style={{
                                                    fontSize: '0.78rem',
                                                    fontWeight: 600,
                                                    background: 'var(--accent-primary)',
                                                    color: 'white',
                                                    padding: '0.2rem 0.5rem',
                                                    borderRadius: '0.4rem',
                                                }}
                                            >
                                                Row {slideNum}
                                            </span>
                                            {slideInfo.title && (
                                                <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                                                    {cleanTitle(slideInfo.title)}
                                                </span>
                                            )}
                                        </div>

                                        {/* Row Actions */}
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                            <button
                                                onClick={() => handleOpenPatch(slideInfo.narration || '')}
                                                title="Send this row to Audio Patch sandbox"
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.25rem',
                                                    padding: '0.25rem 0.5rem',
                                                    background: 'transparent',
                                                    border: '1px solid var(--border-color)',
                                                    borderRadius: '0.4rem',
                                                    color: 'var(--text-secondary)',
                                                    fontSize: '0.75rem',
                                                    cursor: 'pointer',
                                                }}
                                            >
                                                <Sparkles size={12} style={{ color: 'var(--accent-primary)' }} />
                                                Patch
                                            </button>

                                            {!isEditing ? (
                                                <button
                                                    onClick={() => handleStartEdit(slideNum, slideInfo.narration || '')}
                                                    title="Edit text and re-record this row"
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.25rem',
                                                        padding: '0.25rem 0.5rem',
                                                        background: 'transparent',
                                                        border: '1px solid var(--border-color)',
                                                        borderRadius: '0.4rem',
                                                        color: 'var(--text-secondary)',
                                                        fontSize: '0.75rem',
                                                        cursor: 'pointer',
                                                    }}
                                                >
                                                    <Edit3 size={12} />
                                                    Edit
                                                </button>
                                            ) : (
                                                <button
                                                    onClick={handleCancelEdit}
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.25rem',
                                                        padding: '0.25rem 0.5rem',
                                                        background: 'transparent',
                                                        border: '1px solid var(--border-color)',
                                                        borderRadius: '0.4rem',
                                                        color: 'var(--text-secondary)',
                                                        fontSize: '0.75rem',
                                                        cursor: 'pointer',
                                                    }}
                                                >
                                                    <X size={12} />
                                                    Cancel
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    {/* Narration Content: Read-only with bold markdown formatting or Editable textarea */}
                                    {!isEditing ? (
                                        <div
                                            onMouseUp={() => handleMouseUp(slideNum)}
                                            style={{
                                                fontSize: '0.92rem',
                                                lineHeight: '1.55',
                                                color: 'var(--text-primary)',
                                                background: 'var(--bg-secondary)',
                                                padding: '0.65rem 0.85rem',
                                                borderRadius: '0.5rem',
                                                border: '1px solid var(--border-color)',
                                                cursor: 'text',
                                                userSelect: 'text',
                                            }}
                                        >
                                            {slideInfo.narration ? (
                                                renderFormattedText(slideInfo.narration)
                                            ) : (
                                                <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                                                    No narration text recorded for this slide
                                                </span>
                                            )}
                                        </div>
                                    ) : (
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                            <textarea
                                                rows={3}
                                                value={editingText}
                                                onChange={(e) => setEditingText(e.target.value)}
                                                style={{
                                                    width: '100%',
                                                    padding: '0.65rem',
                                                    borderRadius: '0.5rem',
                                                    border: '1px solid var(--accent-primary)',
                                                    background: 'var(--bg-secondary)',
                                                    color: 'var(--text-primary)',
                                                    fontSize: '0.92rem',
                                                    lineHeight: '1.5',
                                                    resize: 'vertical',
                                                    boxSizing: 'border-box',
                                                    fontFamily: 'inherit',
                                                }}
                                            />
                                            {regenError && (
                                                <span style={{ fontSize: '0.78rem', color: '#ef4444' }}>
                                                    {regenError}
                                                </span>
                                            )}
                                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                                                <button
                                                    onClick={handleCancelEdit}
                                                    disabled={isRegenerating}
                                                    style={{
                                                        padding: '0.4rem 0.75rem',
                                                        borderRadius: '0.4rem',
                                                        border: '1px solid var(--border-color)',
                                                        background: 'transparent',
                                                        color: 'var(--text-secondary)',
                                                        fontSize: '0.8rem',
                                                        cursor: 'pointer',
                                                    }}
                                                >
                                                    Cancel
                                                </button>
                                                <button
                                                    onClick={() => handleSaveAndRegenerate(slideNum)}
                                                    disabled={isRegenerating || !editingText.trim()}
                                                    style={{
                                                        padding: '0.4rem 0.85rem',
                                                        borderRadius: '0.4rem',
                                                        border: 'none',
                                                        background: 'var(--accent-primary)',
                                                        color: 'white',
                                                        fontSize: '0.8rem',
                                                        fontWeight: 600,
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.35rem',
                                                        cursor: isRegenerating || !editingText.trim() ? 'not-allowed' : 'pointer',
                                                    }}
                                                >
                                                    {isRegenerating ? (
                                                        <>
                                                            <RotateCcw size={13} className="animate-spin" />
                                                            Re-recording row...
                                                        </>
                                                    ) : (
                                                        <>
                                                            <RotateCcw size={13} />
                                                            Save & Re-record Row
                                                        </>
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {/* Audio Player for this row or On-Demand Row Audio Trigger */}
                                    {url ? (
                                        <AudioPlayer
                                            slideNum={slideNum}
                                            url={resolveUrl(url)}
                                            isPlaying={playingSlide === slideNum}
                                            onPlay={handlePlay}
                                            onEnded={handleEnded}
                                            isCombined={false}
                                        />
                                    ) : (
                                        <div
                                            style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'space-between',
                                                padding: '0.55rem 0.85rem',
                                                background: 'var(--bg-secondary)',
                                                borderRadius: '0.5rem',
                                                border: '1px dashed var(--border-color)',
                                                fontSize: '0.8rem',
                                                color: 'var(--text-secondary)',
                                                flexWrap: 'wrap',
                                                gap: '0.5rem',
                                            }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                                <FileAudio size={14} style={{ opacity: 0.7 }} />
                                                <span>Audio included in continuous track above</span>
                                            </div>
                                            <button
                                                onClick={() => handleSaveAndRegenerate(slideNum, slideInfo.narration)}
                                                disabled={isRegenerating || !slideInfo.narration}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.35rem',
                                                    padding: '0.3rem 0.65rem',
                                                    background: 'var(--bg-tertiary)',
                                                    border: '1px solid var(--border-color)',
                                                    borderRadius: '0.4rem',
                                                    color: 'var(--text-primary)',
                                                    fontSize: '0.78rem',
                                                    fontWeight: 500,
                                                    cursor: isRegenerating || !slideInfo.narration ? 'not-allowed' : 'pointer',
                                                }}
                                                title="Synthesize a separate audio player for this row"
                                            >
                                                {isRegenerating ? (
                                                    <>
                                                        <RotateCcw size={12} className="animate-spin" />
                                                        Generating clip...
                                                    </>
                                                ) : (
                                                    <>
                                                        <Volume2 size={12} style={{ color: 'var(--accent-primary)' }} />
                                                        Generate Row Audio
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>

                    {/* Bottom Pagination Bar */}
                    {totalPages > 1 && pageSize !== 'all' && (
                        <div
                            style={{
                                marginTop: '1.25rem',
                                padding: '0.75rem 1rem',
                                background: 'var(--bg-tertiary)',
                                borderRadius: '0.6rem',
                                border: '1px solid var(--border-color)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                flexWrap: 'wrap',
                                gap: '0.75rem',
                            }}
                        >
                            {/* Jump to row form */}
                            <form
                                onSubmit={handleJumpToRow}
                                style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                            >
                                <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                                    Go to row:
                                </span>
                                <input
                                    type="number"
                                    min="1"
                                    max={totalRows}
                                    value={jumpInput}
                                    onChange={(e) => setJumpInput(e.target.value)}
                                    placeholder={`1–${totalRows}`}
                                    style={{
                                        width: '64px',
                                        padding: '0.25rem 0.45rem',
                                        fontSize: '0.78rem',
                                        borderRadius: '0.35rem',
                                        border: '1px solid var(--border-color)',
                                        background: 'var(--bg-secondary)',
                                        color: 'var(--text-primary)',
                                    }}
                                />
                                <button
                                    type="submit"
                                    style={{
                                        padding: '0.25rem 0.55rem',
                                        fontSize: '0.75rem',
                                        borderRadius: '0.35rem',
                                        border: '1px solid var(--border-color)',
                                        background: 'var(--bg-secondary)',
                                        color: 'var(--text-primary)',
                                        cursor: 'pointer',
                                        fontWeight: 500,
                                    }}
                                >
                                    Go
                                </button>
                            </form>

                            {/* Page Buttons (Numbered + Prev/Next) */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
                                <button
                                    onClick={() => handlePageChange(activePage - 1)}
                                    disabled={activePage <= 1}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.2rem',
                                        padding: '0.3rem 0.6rem',
                                        fontSize: '0.78rem',
                                        borderRadius: '0.4rem',
                                        border: '1px solid var(--border-color)',
                                        background: 'var(--bg-secondary)',
                                        color: activePage <= 1 ? 'var(--text-tertiary, #888)' : 'var(--text-primary)',
                                        opacity: activePage <= 1 ? 0.4 : 1,
                                        cursor: activePage <= 1 ? 'not-allowed' : 'pointer',
                                    }}
                                >
                                    <ChevronLeft size={13} />
                                    Prev
                                </button>

                                {/* Page number buttons */}
                                {(() => {
                                    const pages = [];
                                    if (totalPages <= 7) {
                                        for (let p = 1; p <= totalPages; p++) pages.push(p);
                                    } else {
                                        pages.push(1);
                                        if (activePage > 3) pages.push('...');
                                        const start = Math.max(2, activePage - 1);
                                        const end = Math.min(totalPages - 1, activePage + 1);
                                        for (let p = start; p <= end; p++) {
                                            if (!pages.includes(p)) pages.push(p);
                                        }
                                        if (activePage < totalPages - 2) pages.push('...');
                                        if (!pages.includes(totalPages)) pages.push(totalPages);
                                    }

                                    return pages.map((page, idx) => {
                                        if (page === '...') {
                                            return (
                                                <span
                                                    key={`ellipsis-${idx}`}
                                                    style={{
                                                        fontSize: '0.78rem',
                                                        color: 'var(--text-secondary)',
                                                        padding: '0 0.2rem',
                                                    }}
                                                >
                                                    ...
                                                </span>
                                            );
                                        }
                                        const isCurrent = page === activePage;
                                        return (
                                            <button
                                                key={`page-${page}`}
                                                onClick={() => handlePageChange(page)}
                                                style={{
                                                    minWidth: '28px',
                                                    height: '28px',
                                                    padding: '0 0.4rem',
                                                    fontSize: '0.78rem',
                                                    fontWeight: isCurrent ? 600 : 400,
                                                    borderRadius: '0.4rem',
                                                    border: isCurrent ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)',
                                                    background: isCurrent ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                                                    color: isCurrent ? 'white' : 'var(--text-primary)',
                                                    cursor: 'pointer',
                                                    transition: 'all 0.15s ease',
                                                }}
                                            >
                                                {page}
                                            </button>
                                        );
                                    });
                                })()}

                                <button
                                    onClick={() => handlePageChange(activePage + 1)}
                                    disabled={activePage >= totalPages}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.2rem',
                                        padding: '0.3rem 0.6rem',
                                        fontSize: '0.78rem',
                                        borderRadius: '0.4rem',
                                        border: '1px solid var(--border-color)',
                                        background: 'var(--bg-secondary)',
                                        color: activePage >= totalPages ? 'var(--text-tertiary, #888)' : 'var(--text-primary)',
                                        opacity: activePage >= totalPages ? 0.4 : 1,
                                        cursor: activePage >= totalPages ? 'not-allowed' : 'pointer',
                                    }}
                                >
                                    Next
                                    <ChevronRight size={13} />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* All rows view note */}
                    {pageSize === 'all' && totalRows > 10 && (
                        <div
                            style={{
                                marginTop: '1rem',
                                textAlign: 'center',
                                fontSize: '0.78rem',
                                color: 'var(--text-secondary)',
                            }}
                        >
                            Showing all {totalRows} rows.{' '}
                            <button
                                onClick={() => {
                                    setPageSize(5);
                                    setCurrentPage(1);
                                }}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    color: 'var(--accent-primary)',
                                    cursor: 'pointer',
                                    textDecoration: 'underline',
                                    padding: 0,
                                    fontSize: 'inherit',
                                }}
                            >
                                Switch to 5 per page
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Floating Highlight-to-Patch Tooltip */}
            {selectionTooltip && (
                <div
                    style={{
                        position: 'fixed',
                        left: `${selectionTooltip.x}px`,
                        top: `${selectionTooltip.y}px`,
                        transform: 'translate(-50%, -100%)',
                        zIndex: 10000,
                        animation: 'fadeIn 0.15s ease-out',
                    }}
                >
                    <button
                        onClick={() => handleOpenPatch(selectionTooltip.text)}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            padding: '0.4rem 0.75rem',
                            background: 'var(--accent-primary)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '20px',
                            boxShadow: '0 4px 14px rgba(0, 0, 0, 0.3)',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            whiteSpace: 'nowrap',
                        }}
                    >
                        <Sparkles size={13} />
                        Patch "{selectionTooltip.text.length > 18 ? selectionTooltip.text.slice(0, 18) + '...' : selectionTooltip.text}"
                    </button>
                </div>
            )}

            {/* Audio Patch Modal (shares engine with Sidebar) */}
            <AudioPatchModal
                isOpen={isPatchModalOpen}
                onClose={() => setIsPatchModalOpen(false)}
                initialText={patchModalText}
            />

            {/* Errors display */}
            {errors && errors.length > 0 && (
                <div
                    style={{
                        marginTop: '1rem',
                        padding: '0.75rem',
                        background: 'rgba(239, 68, 68, 0.1)',
                        borderRadius: '0.5rem',
                        fontSize: '0.85rem',
                        color: '#ef4444',
                    }}
                >
                    <strong>Failed rows:</strong>
                    <ul style={{ margin: '0.5rem 0 0 1rem', padding: 0 }}>
                        {errors.map((err, i) => (
                            <li key={i}>{err}</li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}

/**
 * Individual audio player component with scrub bar
 */
function AudioPlayer({ slideNum, title, url, isPlaying, onPlay, onEnded, isCombined = false }) {
    const audioRef = useRef(null);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [isSeeking, setIsSeeking] = useState(false);

    const handleTimeUpdate = () => {
        if (audioRef.current && !isSeeking) {
            setCurrentTime(audioRef.current.currentTime);
        }
    };

    const handleLoadedMetadata = () => {
        if (audioRef.current) {
            setDuration(audioRef.current.duration);
        }
    };

    const formatTime = (time) => {
        if (isNaN(time)) return '0:00';
        const mins = Math.floor(time / 60);
        const secs = Math.floor(time % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const handleSeek = (e) => {
        const time = parseFloat(e.target.value);
        if (audioRef.current) {
            audioRef.current.currentTime = time;
            setCurrentTime(time);
        }
    };

    return (
        <div
            className="audio-player-card"
            style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.4rem',
                padding: isCombined ? '1rem' : '0.6rem 0.8rem',
                background: isCombined ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                borderRadius: '0.6rem',
                border: isPlaying ? '1px solid var(--accent-primary)' : '1px solid transparent',
                transition: 'all 0.2s ease',
            }}
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <button
                    onClick={() => onPlay(slideNum, audioRef.current)}
                    style={{
                        width: isCombined ? '42px' : '34px',
                        height: isCombined ? '42px' : '34px',
                        borderRadius: '50%',
                        border: 'none',
                        background: isPlaying ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                        color: isPlaying ? 'white' : 'var(--text-primary)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'all 0.15s ease',
                    }}
                >
                    {isPlaying ? <Pause size={isCombined ? 18 : 15} fill="currentColor" /> : <Play size={isCombined ? 18 : 15} fill="currentColor" style={{ marginLeft: '2px' }} />}
                </button>

                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: isCombined ? '0.92rem' : '0.82rem', fontWeight: 500, color: 'var(--text-primary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>{title || (isCombined ? 'Full Narration' : `Audio Clip (Row ${slideNum})`)}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            {formatTime(currentTime)} / {formatTime(duration)}
                        </span>
                    </div>
                </div>

                <a
                    href={url}
                    download={isCombined ? 'full_narration.wav' : `row_${slideNum}.wav`}
                    style={{
                        color: 'var(--text-secondary)',
                        padding: '0.35rem',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                    }}
                    title="Download WAV"
                >
                    <Download size={15} />
                </a>
            </div>

            {/* Seekbar */}
            <input
                type="range"
                min="0"
                max={duration || 0}
                step="0.01"
                value={currentTime}
                onMouseDown={() => setIsSeeking(true)}
                onMouseUp={() => setIsSeeking(false)}
                onChange={handleSeek}
                style={{
                    width: '100%',
                    height: '4px',
                    accentColor: 'var(--accent-primary)',
                    cursor: 'pointer',
                    marginTop: '0.2rem',
                }}
            />

            <audio
                ref={audioRef}
                src={url}
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onDurationChange={handleLoadedMetadata}
                onEnded={onEnded}
                style={{ display: 'none' }}
            />
        </div>
    );
}
