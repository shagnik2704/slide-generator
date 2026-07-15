import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, X, Download, AlertTriangle } from 'lucide-react';
import { API_URL } from '../services/api';

/**
 * RedesignForm - Form component for submitting tutorial redesign requests
 */
export default function RedesignForm({ onSubmit, onCancel }) {
    const navigate = useNavigate();
    const [step, setStep] = useState('generate'); // 'generate' | 'progress' | 'preview'
    const [generatedUrl, setGeneratedUrl] = useState('');
    const [hasShared, setHasShared] = useState(false);
    const [fossName, setFossName] = useState('');
    const [language, setLanguage] = useState('English');
    const [recipients, setRecipients] = useState([{ email: '', role: 'writer' }]);
    const [errors, setErrors] = useState({});
    
    // Progress States
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [progressStage, setProgressStage] = useState('');
    
    // Failure State
    const [failureReason, setFailureReason] = useState('');

    const stagesOrder = ['init', 'fetch_links', 'extraction', 'tech_intelligence', 'duration_split', 'tabulation', 'completed'];
    
    const isStageCompleted = (stageKey, currentStage) => {
        const currentIdx = stagesOrder.indexOf(currentStage);
        const keyIdx = stagesOrder.indexOf(stageKey);
        if (currentStage === 'failed') return false;
        if (currentStage === 'completed') return true;
        return keyIdx < currentIdx;
    };

    const handleAddRecipient = () => {
        setRecipients([...recipients, { email: '', role: 'writer' }]);
    };

    const handleRemoveRecipient = (index) => {
        if (recipients.length > 1) {
            setRecipients(recipients.filter((_, i) => i !== index));
        }
    };

    const handleRecipientChange = (index, field, value) => {
        const newRecipients = [...recipients];
        newRecipients[index][field] = value;
        setRecipients(newRecipients);
    };

    const validateEmail = (email) => {
        if (!email) return true; // Empty emails are allowed (will be filtered out)
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    const handleGenerate = async (e) => {
        e.preventDefault();
        
        // Validation
        const newErrors = {};
        if (!fossName.trim()) {
            newErrors.fossName = 'FOSS Name is required';
        }

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        // Change step to progress indicator
        setStep('progress');
        setProgress(0);
        setProgressMessage('Queuing task...');
        setProgressStage('init');

        try {
            setFailureReason('');
            // Submit generate request
            const result = await onSubmit({
                type: 'generate',
                foss_name: fossName.trim(),
                language: language.trim() || 'English',
                onProgress: (progressInfo) => {
                    setProgress(progressInfo.progress || 0);
                    setProgressMessage(progressInfo.message || '');
                    setProgressStage(progressInfo.stage || '');
                }
            });

            if (result && result.url) {
                setGeneratedUrl(result.url);
                setStep('preview');
            } else {
                setStep('generate');
            }
        } catch (err) {
            console.error(err);
            setFailureReason(err.message || 'An unknown error occurred during tutorial redesign.');
            setStep('failed');
        }
    };

    const handleShare = async (e) => {
        e.preventDefault();
        
        // Validation
        const newErrors = {};
        const invalidRecipients = recipients.filter(recipient => recipient.email && !validateEmail(recipient.email));
        if (invalidRecipients.length > 0) {
            newErrors.emails = 'Please enter valid email addresses';
        }

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        // Filter out empty emails
        const validRecipients = recipients.filter(recipient => recipient.email.trim() !== '');

        // Submit share request
        await onSubmit({
            type: 'share',
            url: generatedUrl,
            recipients: validRecipients
        });

        setHasShared(true);

        // Keep the form open for further actions
    };

    const inputStyle = {
        width: '100%',
        padding: '0.75rem 1rem',
        borderRadius: '0.5rem',
        border: '1px solid var(--border-color)',
        background: 'var(--bg-secondary)',
        color: 'var(--text-primary)',
        fontSize: '0.95rem',
        fontFamily: 'inherit',
        outline: 'none',
        transition: 'border-color 0.2s ease'
    };

    const labelStyle = {
        display: 'block',
        marginBottom: '0.5rem',
        fontSize: '0.9rem',
        fontWeight: 500,
        color: 'var(--text-primary)'
    };

    const errorStyle = {
        color: '#ef4444',
        fontSize: '0.85rem',
        marginTop: '0.25rem'
    };

    return (
        <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '1rem',
            padding: '1.5rem',
            marginBottom: '1rem',
            boxShadow: 'var(--shadow-md)',
            maxWidth: '800px',
            margin: '0 auto 1rem auto'
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1.5rem'
            }}>
                <h2 style={{
                    fontSize: '1.25rem',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    margin: 0
                }}>
                    {step === 'generate' ? 'Generate Tutorial' : step === 'progress' ? 'Redesign Progress' : step === 'failed' ? 'Redesign Failed' : 'Preview & Share'}
                </h2>
                {onCancel && (
                    <button
                        onClick={() => {
                            if (onCancel) onCancel();
                            navigate('/create');
                        }}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            padding: '0.25rem',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            borderRadius: '0.25rem',
                            transition: 'all 0.2s ease'
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'var(--bg-tertiary)';
                            e.currentTarget.style.color = 'var(--text-primary)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'transparent';
                            e.currentTarget.style.color = 'var(--text-secondary)';
                        }}
                    >
                        <X size={20} />
                    </button>
                )}
            </div>

            {step === 'generate' && (
                <form onSubmit={handleGenerate}>
                    {/* FOSS Name */}
                    <div style={{ marginBottom: '1.25rem' }}>
                        <label style={labelStyle}>
                            FOSS Name <span style={{ color: '#ef4444' }}>*</span>
                        </label>
                        <select
                            value={fossName}
                            onChange={(e) => {
                                setFossName(e.target.value);
                                if (errors.fossName) setErrors({ ...errors, fossName: null });
                            }}
                            style={{
                                ...inputStyle,
                                borderColor: errors.fossName ? '#ef4444' : 'var(--border-color)'
                            }}
                            required
                        >
                            <option value="">-- All Courses --</option>
                            <option value="Advance C">Advance C</option>
                            <option value="Advanced Cpp">Advanced Cpp</option>
                            <option value="Android app using Kotlin">Android app using Kotlin</option>
                            <option value="Applications of GeoGebra">Applications of GeoGebra</option>
                            <option value="Apps On Physics">Apps On Physics</option>
                            <option value="Arduino">Arduino</option>
                            <option value="ASCEND">ASCEND</option>
                            <option value="Audacity">Audacity</option>
                            <option value="AutoDock4">AutoDock4</option>
                            <option value="Avogadro">Avogadro</option>
                            <option value="BASH">BASH</option>
                            <option value="Basics of Artificial Intelligence">Basics of Artificial Intelligence</option>
                            <option value="Biogas Plant">Biogas Plant</option>
                            <option value="Biopython">Biopython</option>
                            <option value="Blender">Blender</option>
                            <option value="Blender 4.1">Blender 4.1</option>
                            <option value="Bootstrap">Bootstrap</option>
                            <option value="BOSS Linux">BOSS Linux</option>
                            <option value="C and Cpp">C and Cpp</option>
                            <option value="CellDesigner">CellDesigner</option>
                            <option value="ChemCollective Virtual Labs">ChemCollective Virtual Labs</option>
                            <option value="CircuitJS">CircuitJS</option>
                            <option value="Communication Series">Communication Series</option>
                            <option value="Construction of Low Cost Houses">Construction of Low Cost Houses</option>
                            <option value="CSS">CSS</option>
                            <option value="Developing Empathy">Developing Empathy</option>
                            <option value="Digital Divide">Digital Divide</option>
                            <option value="Digital India">Digital India</option>
                            <option value="Docker">Docker</option>
                            <option value="Drupal">Drupal</option>
                            <option value="DSpace">DSpace</option>
                            <option value="DWSIM">DWSIM</option>
                            <option value="eSim">eSim</option>
                            <option value="ExpEYES">ExpEYES</option>
                            <option value="Filezilla">Filezilla</option>
                            <option value="Firefox">Firefox</option>
                            <option value="FreeCAD">FreeCAD</option>
                            <option value="Freeplane">Freeplane</option>
                            <option value="FrontAccounting-2.4.7">FrontAccounting-2.4.7</option>
                            <option value="GChemPaint">GChemPaint</option>
                            <option value="GCompris">GCompris</option>
                            <option value="gedit Text Editor">gedit Text Editor</option>
                            <option value="GeoGebra 5.04">GeoGebra 5.04</option>
                            <option value="GIMP">GIMP</option>
                            <option value="Git">Git</option>
                            <option value="Gnuplot">Gnuplot</option>
                            <option value="Grace">Grace</option>
                            <option value="Gromacs">Gromacs</option>
                            <option value="GUI in Scilab">GUI in Scilab</option>
                            <option value="HTML">HTML</option>
                            <option value="Inkscape">Inkscape</option>
                            <option value="Introduction to Computers">Introduction to Computers</option>
                            <option value="Java">Java</option>
                            <option value="Java Business Application">Java Business Application</option>
                            <option value="JavaScript">JavaScript</option>
                            <option value="Jmol Application">Jmol Application</option>
                            <option value="Joomla">Joomla</option>
                            <option value="K3b">K3b</option>
                            <option value="KiCad">KiCad</option>
                            <option value="Koha Library Management System">Koha Library Management System</option>
                            <option value="Koha Library Software">Koha Library Software</option>
                            <option value="KTouch">KTouch</option>
                            <option value="KTurtle">KTurtle</option>
                            <option value="LaTeX">LaTeX</option>
                            <option value="LibreOffice Installation">LibreOffice Installation</option>
                            <option value="LibreOffice Suite Base">LibreOffice Suite Base</option>
                            <option value="LibreOffice Suite Calc 6.3">LibreOffice Suite Calc 6.3</option>
                            <option value="LibreOffice Suite Draw 6.3">LibreOffice Suite Draw 6.3</option>
                            <option value="LibreOffice Suite Impress 6.3">LibreOffice Suite Impress 6.3</option>
                            <option value="LibreOffice Suite Math 6.3">LibreOffice Suite Math 6.3</option>
                            <option value="LibreOffice Suite Writer 6.3">LibreOffice Suite Writer 6.3</option>
                            <option value="Linux">Linux</option>
                            <option value="Linux AWK">Linux AWK</option>
                            <option value="Linux for Sys-Ads">Linux for Sys-Ads</option>
                            <option value="Linux Ubuntu">Linux Ubuntu</option>
                            <option value="Marble">Marble</option>
                            <option value="Moodle Learning Management System">Moodle Learning Management System</option>
                            <option value="Netbeans">Netbeans</option>
                            <option value="Ngspice">Ngspice</option>
                            <option value="ns-3 Network Simulator">ns-3 Network Simulator</option>
                            <option value="OpenFOAM version 7">OpenFOAM version 7</option>
                            <option value="OpenModelica">OpenModelica</option>
                            <option value="OpenModelica OpenIPSL">OpenModelica OpenIPSL</option>
                            <option value="OpenPLC with LDmicro">OpenPLC with LDmicro</option>
                            <option value="Osdag">Osdag</option>
                            <option value="PERL">PERL</option>
                            <option value="PhET Simulations for Biology">PhET Simulations for Biology</option>
                            <option value="PhET Simulations for Chemistry">PhET Simulations for Chemistry</option>
                            <option value="PhET Simulations for Mathematics">PhET Simulations for Mathematics</option>
                            <option value="PhET Simulations for Physics">PhET Simulations for Physics</option>
                            <option value="PHP and MySQL">PHP and MySQL</option>
                            <option value="Python 3.4.3">Python 3.4.3</option>
                            <option value="Python Django">Python Django</option>
                            <option value="Python Flask">Python Flask</option>
                            <option value="Python for Automation">Python for Automation</option>
                            <option value="Python for Machine Learning">Python for Machine Learning</option>
                            <option value="QCad">QCad</option>
                            <option value="QGIS">QGIS</option>
                            <option value="R">R</option>
                            <option value="RDBMS PostgreSQL">RDBMS PostgreSQL</option>
                            <option value="Ruby">Ruby</option>
                            <option value="Scilab">Scilab</option>
                            <option value="Sed-Stream Editor">Sed-Stream Editor</option>
                            <option value="Single Board Heater System">Single Board Heater System</option>
                            <option value="Skill Development- Fitter">Skill Development- Fitter</option>
                            <option value="Skill Development- InStore Promoter">Skill Development- InStore Promoter</option>
                            <option value="Spoken Tutorial Technology">Spoken Tutorial Technology</option>
                            <option value="Synfig">Synfig</option>
                            <option value="Thunderbird">Thunderbird</option>
                            <option value="Tux Typing">Tux Typing</option>
                            <option value="Ubuntu Linux on Virtual Box">Ubuntu Linux on Virtual Box</option>
                            <option value="UCSF Chimera">UCSF Chimera</option>
                            <option value="Understanding Emotions">Understanding Emotions</option>
                            <option value="Video Editing using Blender">Video Editing using Blender</option>
                            <option value="Waste Management">Waste Management</option>
                            <option value="Website Information">Website Information</option>
                            <option value="What is Spoken Tutorial">What is Spoken Tutorial</option>
                            <option value="Xfig">Xfig</option>
                        </select>
                        {errors.fossName && <div style={errorStyle}>{errors.fossName}</div>}
                    </div>

                    {/* Language */}
                    <div style={{ marginBottom: '1.25rem' }}>
                        <label style={labelStyle}>Language</label>
                        <select
                            value={language}
                            onChange={(e) => setLanguage(e.target.value)}
                            style={inputStyle}
                        >
                            <option value="English">English</option>
                            <option value="Hindi">Hindi</option>
                            <option value="Tamil">Tamil</option>
                            <option value="Telugu">Telugu</option>
                            <option value="Marathi">Marathi</option>
                            <option value="Bengali">Bengali</option>
                            <option value="Kannada">Kannada</option>
                            <option value="Gujarati">Gujarati</option>
                            <option value="Malayalam">Malayalam</option>
                            <option value="Punjabi">Punjabi</option>
                            <option value="Odia">Odia</option>
                            <option value="Assamese">Assamese</option>
                        </select>
                    </div>

                    {/* Submit Button */}
                    <button
                        type="submit"
                        style={{
                            width: '100%',
                            padding: '0.75rem 1.5rem',
                            background: 'var(--accent-primary)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.5rem',
                            fontSize: '0.95rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.5rem',
                            transition: 'all 0.2s ease',
                            boxShadow: 'var(--shadow-sm)'
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.opacity = '0.9';
                            e.currentTarget.style.transform = 'translateY(-1px)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.opacity = '1';
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                        }}
                    >
                        <Send size={16} />
                        Update and Redesign
                    </button>
                </form>
            )}

            {step === 'progress' && (
                <div style={{ padding: '1rem 0' }}>
                    <style>{`
                        @keyframes pulse {
                            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); }
                            70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(59, 130, 246, 0); }
                            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
                        }
                    `}</style>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '1rem'
                    }}>
                        <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                            Progress Stage: <span style={{ color: 'var(--accent-primary)', textTransform: 'capitalize' }}>{progressStage.replace('_', ' ')}</span>
                        </span>
                        <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
                            {progress}%
                        </span>
                    </div>

                    {/* Progress Bar Container */}
                    <div style={{
                        width: '100%',
                        height: '8px',
                        background: 'var(--border-color)',
                        borderRadius: '4px',
                        overflow: 'hidden',
                        marginBottom: '1.5rem',
                        position: 'relative'
                    }}>
                        <div style={{
                            width: `${progress}%`,
                            height: '100%',
                            background: 'linear-gradient(90deg, var(--accent-primary) 0%, #3b82f6 100%)',
                            borderRadius: '4px',
                            transition: 'width 0.4s ease-out',
                            boxShadow: '0 0 8px var(--accent-primary)'
                        }} />
                    </div>

                    {/* Message Box */}
                    <div style={{
                        background: 'var(--bg-primary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '0.5rem',
                        padding: '1rem',
                        fontSize: '0.9rem',
                        color: 'var(--text-primary)',
                        marginBottom: '2rem',
                        fontFamily: 'monospace',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        boxShadow: 'inset var(--shadow-sm)'
                    }}>
                        <div className="pulse-indicator" style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: 'var(--accent-primary)',
                            boxShadow: '0 0 6px var(--accent-primary)',
                            animation: 'pulse 1.5s infinite'
                        }} />
                        <span style={{ wordBreak: 'break-all' }}>{progressMessage || 'Processing...'}</span>
                    </div>

                    {/* Stepper Checklist */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {[
                            { key: 'init', label: 'Initialize Workspace' },
                            { key: 'fetch_links', label: 'Fetch Tutorial Links' },
                            { key: 'extraction', label: 'Extract Contents' },
                            { key: 'tech_intelligence', label: 'AI Tech Intelligence' },
                            { key: 'duration_split', label: 'Duration Split LangGraph' },
                            { key: 'tabulation', label: 'Tabulate Results' }
                        ].map((s, i) => {
                            const isDone = isStageCompleted(s.key, progressStage);
                            const isActive = progressStage === s.key;
                            
                            return (
                                <div key={s.key} style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.75rem',
                                    color: isDone ? 'var(--text-primary)' : isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                                    fontWeight: isActive ? 600 : 400,
                                    fontSize: '0.9rem',
                                    transition: 'all 0.3s ease'
                                }}>
                                    <div style={{
                                        width: '20px',
                                        height: '20px',
                                        borderRadius: '50%',
                                        border: isDone ? 'none' : '2px solid var(--border-color)',
                                        background: isDone ? '#10b981' : isActive ? 'var(--accent-primary)' : 'transparent',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: isDone || isActive ? 'white' : 'var(--text-secondary)',
                                        fontSize: '0.75rem',
                                        fontWeight: 'bold',
                                        transition: 'all 0.3s ease'
                                    }}>
                                        {isDone ? '✓' : i + 1}
                                    </div>
                                    <span>{s.label}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {step === 'preview' && (
                <div>
                    {/* Download */}
                    <div style={{ marginBottom: '1.5rem', textAlign: 'center', padding: '1rem 0' }}>
                        <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                            Redesign Complete!
                        </h3>
                        <a
                            href={`${API_URL}/download/redesign/${generatedUrl}`}
                            download={generatedUrl}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.75rem 1.5rem',
                                background: 'var(--accent-primary)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '0.5rem',
                                fontSize: '0.95rem',
                                fontWeight: 600,
                                textDecoration: 'none',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                boxShadow: 'var(--shadow-sm)'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.opacity = '0.9';
                                e.currentTarget.style.transform = 'translateY(-1px)';
                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.opacity = '1';
                                e.currentTarget.style.transform = 'translateY(0)';
                                e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                            }}
                        >
                            <Download size={16} />
                            Download XLSX File
                        </a>
                    </div>
                </div>
            )}

            {step === 'failed' && (
                <div style={{ padding: '1rem 0', textAlign: 'center' }}>
                    <AlertTriangle size={48} color="#ef4444" style={{ marginBottom: '1rem' }} />
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                        Redesign Process Failed
                    </h3>
                    <div style={{
                        background: 'rgba(239, 68, 68, 0.1)',
                        border: '1px solid #ef4444',
                        borderRadius: '0.5rem',
                        padding: '1rem',
                        color: '#ef4444',
                        fontSize: '0.95rem',
                        marginBottom: '1.5rem',
                        textAlign: 'left',
                        whiteSpace: 'pre-wrap',
                        fontFamily: 'monospace'
                    }}>
                        <strong>Reason:</strong> {failureReason || 'An unknown error occurred during the redesign process.'}
                    </div>
                    <button
                        onClick={() => {
                            setStep('generate');
                            setFailureReason('');
                        }}
                        style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.75rem 1.5rem',
                            background: 'var(--accent-primary)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.5rem',
                            fontSize: '0.95rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            transition: 'all 0.2s ease',
                            boxShadow: 'var(--shadow-sm)'
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.opacity = '0.9';
                            e.currentTarget.style.transform = 'translateY(-1px)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.opacity = '1';
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                        }}
                    >
                        Try Again
                    </button>
                </div>
            )}
        </div>
    );
}
