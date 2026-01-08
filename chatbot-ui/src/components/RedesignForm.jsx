import React, { useState } from 'react';
import { Send, X, Plus, Share2, Eye } from 'lucide-react';

/**
 * RedesignForm - Form component for submitting tutorial redesign requests
 */
export default function RedesignForm({ onSubmit, onCancel }) {
    const [step, setStep] = useState('generate'); // 'generate' | 'preview'
    const [generatedUrl, setGeneratedUrl] = useState('');
    const [hasShared, setHasShared] = useState(false);
    const [fossName, setFossName] = useState('');
    const [language, setLanguage] = useState('English');
    const [recipients, setRecipients] = useState([{ email: '', role: 'writer' }]);
    const [errors, setErrors] = useState({});

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

        // Submit generate request
        const result = await onSubmit({
            type: 'generate',
            foss_name: fossName.trim(),
            language: language.trim() || 'English'
        });

        if (result && result.url) {
            setGeneratedUrl(result.url);
            setStep('preview');
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
                    {step === 'generate' ? 'Generate Tutorial' : 'Preview & Share'}
                </h2>
                {onCancel && (
                    <button
                        onClick={onCancel}
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

            {step === 'generate' ? (
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
                            <option value="Advance C">Advance C (43)</option>
                            <option value="Advanced Cpp">Advanced Cpp (150)</option>
                            <option value="Android app using Kotlin">Android app using Kotlin (10)</option>
                            <option value="Applications of GeoGebra">Applications of GeoGebra (15)</option>
                            <option value="Apps On Physics">Apps On Physics (13)</option>
                            <option value="Arduino">Arduino (144)</option>
                            <option value="ASCEND">ASCEND (6)</option>
                            <option value="Audacity">Audacity (4)</option>
                            <option value="AutoDock4">AutoDock4 (8)</option>
                            <option value="Avogadro">Avogadro (64)</option>
                            <option value="BASH">BASH (345)</option>
                            <option value="Basics of Artificial Intelligence">Basics of Artificial Intelligence (5)</option>
                            <option value="Biogas Plant">Biogas Plant (22)</option>
                            <option value="Biopython">Biopython (53)</option>
                            <option value="Blender">Blender (225)</option>
                            <option value="Blender 4.1">Blender 4.1 (9)</option>
                            <option value="Bootstrap">Bootstrap (18)</option>
                            <option value="BOSS Linux">BOSS Linux (143)</option>
                            <option value="C and Cpp">C and Cpp (387)</option>
                            <option value="CellDesigner">CellDesigner (43)</option>
                            <option value="ChemCollective Virtual Labs">ChemCollective Virtual Labs (15)</option>
                            <option value="CircuitJS">CircuitJS (17)</option>
                            <option value="Communication Series">Communication Series (4)</option>
                            <option value="Construction of Low Cost Houses">Construction of Low Cost Houses (4)</option>
                            <option value="CSS">CSS (17)</option>
                            <option value="Developing Empathy">Developing Empathy (4)</option>
                            <option value="Digital Divide">Digital Divide (192)</option>
                            <option value="Digital India">Digital India (13)</option>
                            <option value="Docker">Docker (10)</option>
                            <option value="Drupal">Drupal (373)</option>
                            <option value="DSpace">DSpace (21)</option>
                            <option value="DWSIM">DWSIM (45)</option>
                            <option value="eSim">eSim (16)</option>
                            <option value="ExpEYES">ExpEYES (82)</option>
                            <option value="Filezilla">Filezilla (13)</option>
                            <option value="Firefox">Firefox (179)</option>
                            <option value="FreeCAD">FreeCAD (26)</option>
                            <option value="Freeplane">Freeplane (11)</option>
                            <option value="FrontAccounting-2.4.7">FrontAccounting-2.4.7 (100)</option>
                            <option value="GChemPaint">GChemPaint (219)</option>
                            <option value="GCompris">GCompris (8)</option>
                            <option value="gedit Text Editor">gedit Text Editor (61)</option>
                            <option value="GeoGebra 5.04">GeoGebra 5.04 (24)</option>
                            <option value="GIMP">GIMP (329)</option>
                            <option value="Git">Git (129)</option>
                            <option value="Gnuplot">Gnuplot (13)</option>
                            <option value="Grace">Grace (7)</option>
                            <option value="Gromacs">Gromacs (9)</option>
                            <option value="GUI in Scilab">GUI in Scilab (10)</option>
                            <option value="HTML">HTML (14)</option>
                            <option value="Inkscape">Inkscape (319)</option>
                            <option value="Introduction to Computers">Introduction to Computers (88)</option>
                            <option value="Java">Java (675)</option>
                            <option value="Java Business Application">Java Business Application (96)</option>
                            <option value="JavaScript">JavaScript (18)</option>
                            <option value="Jmol Application">Jmol Application (187)</option>
                            <option value="Joomla">Joomla (27)</option>
                            <option value="K3b">K3b (20)</option>
                            <option value="KiCad">KiCad (49)</option>
                            <option value="Koha Library Management System">Koha Library Management System (294)</option>
                            <option value="Koha Library Software">Koha Library Software (41)</option>
                            <option value="KTouch">KTouch (49)</option>
                            <option value="KTurtle">KTurtle (115)</option>
                            <option value="LaTeX">LaTeX (136)</option>
                            <option value="LibreOffice Installation">LibreOffice Installation (20)</option>
                            <option value="LibreOffice Suite Base">LibreOffice Suite Base (357)</option>
                            <option value="LibreOffice Suite Calc 6.3">LibreOffice Suite Calc 6.3 (36)</option>
                            <option value="LibreOffice Suite Draw 6.3">LibreOffice Suite Draw 6.3 (14)</option>
                            <option value="LibreOffice Suite Impress 6.3">LibreOffice Suite Impress 6.3 (21)</option>
                            <option value="LibreOffice Suite Math 6.3">LibreOffice Suite Math 6.3 (6)</option>
                            <option value="LibreOffice Suite Writer 6.3">LibreOffice Suite Writer 6.3 (33)</option>
                            <option value="Linux">Linux (305)</option>
                            <option value="Linux AWK">Linux AWK (176)</option>
                            <option value="Linux for Sys-Ads">Linux for Sys-Ads (7)</option>
                            <option value="Linux Ubuntu">Linux Ubuntu (5)</option>
                            <option value="Marble">Marble (15)</option>
                            <option value="Moodle Learning Management System">Moodle Learning Management System (245)</option>
                            <option value="Netbeans">Netbeans (103)</option>
                            <option value="Ngspice">Ngspice (20)</option>
                            <option value="ns-3 Network Simulator">ns-3 Network Simulator (10)</option>
                            <option value="OpenFOAM version 7">OpenFOAM version 7 (13)</option>
                            <option value="OpenModelica">OpenModelica (108)</option>
                            <option value="OpenModelica OpenIPSL">OpenModelica OpenIPSL (4)</option>
                            <option value="OpenPLC with LDmicro">OpenPLC with LDmicro (27)</option>
                            <option value="Osdag">Osdag (10)</option>
                            <option value="PERL">PERL (355)</option>
                            <option value="PhET Simulations for Biology">PhET Simulations for Biology (5)</option>
                            <option value="PhET Simulations for Chemistry">PhET Simulations for Chemistry (15)</option>
                            <option value="PhET Simulations for Mathematics">PhET Simulations for Mathematics (10)</option>
                            <option value="PhET Simulations for Physics">PhET Simulations for Physics (15)</option>
                            <option value="PHP and MySQL">PHP and MySQL (686)</option>
                            <option value="Python 3.4.3">Python 3.4.3 (188)</option>
                            <option value="Python Django">Python Django (10)</option>
                            <option value="Python Flask">Python Flask (4)</option>
                            <option value="Python for Automation">Python for Automation (10)</option>
                            <option value="Python for Machine Learning">Python for Machine Learning (11)</option>
                            <option value="QCad">QCad (5)</option>
                            <option value="QGIS">QGIS (131)</option>
                            <option value="R">R (23)</option>
                            <option value="RDBMS PostgreSQL">RDBMS PostgreSQL (9)</option>
                            <option value="Ruby">Ruby (133)</option>
                            <option value="Scilab">Scilab (335)</option>
                            <option value="Sed-Stream Editor">Sed-Stream Editor (6)</option>
                            <option value="Single Board Heater System">Single Board Heater System (29)</option>
                            <option value="Skill Development- Fitter">Skill Development- Fitter (10)</option>
                            <option value="Skill Development- InStore Promoter">Skill Development- InStore Promoter (9)</option>
                            <option value="Spoken Tutorial Technology">Spoken Tutorial Technology (90)</option>
                            <option value="Synfig">Synfig (96)</option>
                            <option value="Thunderbird">Thunderbird (57)</option>
                            <option value="Tux Typing">Tux Typing (33)</option>
                            <option value="Ubuntu Linux on Virtual Box">Ubuntu Linux on Virtual Box (36)</option>
                            <option value="UCSF Chimera">UCSF Chimera (47)</option>
                            <option value="Understanding Emotions">Understanding Emotions (5)</option>
                            <option value="Video Editing using Blender">Video Editing using Blender (8)</option>
                            <option value="Waste Management">Waste Management (3)</option>
                            <option value="Website Information">Website Information (2)</option>
                            <option value="What is Spoken Tutorial">What is Spoken Tutorial (21)</option>
                            <option value="Xfig">Xfig (38)</option>
                        </select>
                        {errors.fossName && <div style={errorStyle}>{errors.fossName}</div>}
                    </div>

                    {/* Language */}
                    <div style={{ marginBottom: '1.25rem' }}>
                        <label style={labelStyle}>Language</label>
                        <input
                            type="text"
                            value={language}
                            onChange={(e) => setLanguage(e.target.value)}
                            style={inputStyle}
                            placeholder="English"
                        />
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
            ) : (
                <div>
                    {/* Preview */}
                    <div style={{ marginBottom: '1.5rem' }}>
                        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                            Preview Sheet
                        </h3>
                        <button
                            onClick={() => window.open(generatedUrl, '_blank')}
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
                            <Eye size={16} />
                            Preview in New Tab
                        </button>
                    </div>

                    {/* Share Form */}
                    <form onSubmit={handleShare}>
                        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                            <Share2 size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
                            Share with Users
                        </h3>

                        {/* Receipt Emails and Roles */}
                        <div style={{ marginBottom: '1.25rem' }}>
                            <label style={labelStyle}>Receipt Emails and Roles</label>
                            {recipients.map((recipient, index) => (
                                <div key={index} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center' }}>
                                    <input
                                        type="email"
                                        value={recipient.email}
                                        onChange={(e) => {
                                            handleRecipientChange(index, 'email', e.target.value);
                                            if (errors.emails) setErrors({ ...errors, emails: null });
                                        }}
                                        style={{
                                            ...inputStyle,
                                            borderColor: errors.emails ? '#ef4444' : 'var(--border-color)',
                                            flex: 1
                                        }}
                                        placeholder="user@example.com"
                                    />
                                    <select
                                        value={recipient.role}
                                        onChange={(e) => handleRecipientChange(index, 'role', e.target.value)}
                                        style={{
                                            ...inputStyle,
                                            width: '120px',
                                            padding: '0.75rem 0.5rem'
                                        }}
                                    >
                                        <option value="writer">Writer</option>
                                        <option value="commenter">Commenter</option>
                                        <option value="reader">Reader</option>
                                    </select>
                                    {recipients.length > 1 && (
                                        <button
                                            type="button"
                                            onClick={() => handleRemoveRecipient(index)}
                                            style={{
                                                background: 'transparent',
                                                border: '1px solid var(--border-color)',
                                                borderRadius: '0.5rem',
                                                color: 'var(--text-secondary)',
                                                cursor: 'pointer',
                                                padding: '0.75rem',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                transition: 'all 0.2s ease'
                                            }}
                                            onMouseEnter={(e) => {
                                                e.currentTarget.style.borderColor = '#ef4444';
                                                e.currentTarget.style.color = '#ef4444';
                                            }}
                                            onMouseLeave={(e) => {
                                                e.currentTarget.style.borderColor = 'var(--border-color)';
                                                e.currentTarget.style.color = 'var(--text-secondary)';
                                            }}
                                        >
                                            <X size={16} />
                                        </button>
                                    )}
                                </div>
                            ))}
                            <button
                                type="button"
                                onClick={handleAddRecipient}
                                style={{
                                    background: 'transparent',
                                    border: '1px dashed var(--border-color)',
                                    borderRadius: '0.5rem',
                                    color: 'var(--text-secondary)',
                                    cursor: 'pointer',
                                    padding: '0.5rem 0.75rem',
                                    fontSize: '0.85rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    transition: 'all 0.2s ease'
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.borderColor = 'var(--accent-primary)';
                                    e.currentTarget.style.color = 'var(--accent-primary)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.borderColor = 'var(--border-color)';
                                    e.currentTarget.style.color = 'var(--text-secondary)';
                                }}
                            >
                                <Plus size={14} />
                                Add Recipient
                            </button>
                            {errors.emails && <div style={errorStyle}>{errors.emails}</div>}
                        </div>

                        {/* Share Button */}
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
                            <Share2 size={16} />
                            Share
                        </button>
                    </form>
                </div>
            )}
        </div>
    );
}
