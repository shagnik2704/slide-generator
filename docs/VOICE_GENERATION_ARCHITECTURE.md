# Voice Generation Frontend Architecture Analysis

This document traces how voice generation works across your React frontend, covering props, handlers, refs, and component mounting.

---

## Component Tree

```
App
 └── Layout.jsx
       ├── Sidebar.jsx ─────────────────┐
       │     └── voiceInputRef          │ (1) User clicks button
       │     └── handleVoiceFileSelect  │ (2) File selected
       │                                │
       └── ChatArea.jsx ←───────────────┘ (3) Stages file via prop
             └── useChatArea.js
                   └── useSidebarHandlers.js
                         └── handleSidebarVoiceUpload()
                               └── API call → /generate_voice_combined
             └── VoicePreview.jsx ← Rendered in message list
```

---

## Step-by-Step Flow

### 1️⃣ User Clicks "Voice Generator" Button

**File:** `Sidebar.jsx` (lines 314-333)

```jsx
<button onClick={() => voiceInputRef.current?.click()}>
    <Mic size={20} />
    Voice Generator
</button>
```

**Mechanism:** `onClick` triggers the hidden file input via **ref**.

---

### 2️⃣ File Input Opens, User Selects File

**File:** `Sidebar.jsx` (lines 137-142)

```jsx
<input
    ref={voiceInputRef}           // ← REF: attached to input
    type="file"
    accept=".json,.docx,.odt"
    onChange={handleVoiceFileSelect}  // ← HANDLER
    style={{ display: 'none' }}
/>
```

---

### 3️⃣ File Selected → Stage for Preview

**File:** `Sidebar.jsx` (lines 38-44)

```jsx
const handleVoiceFileSelect = (e) => {
    const file = e.target.files[0];
    if (file && onStageFile) {
        onStageFile({ file, type: 'voice' });  // ← PROP: calls parent
        e.target.value = '';
    }
};
```

**Mechanism:** Calls `onStageFile` prop (passed from Layout).

---

### 4️⃣ Layout Receives & Forwards to ChatArea

**File:** `Layout.jsx` (lines 13-18)

```jsx
const handleStageFile = (stagedData) => {
    if (chatAreaRef.current?.setStagedFile) {
        chatAreaRef.current.setStagedFile(stagedData);  // ← REF: calls ChatArea method
    }
};
```

**Pattern:** Layout acts as a **bridge** between siblings.

---

### 5️⃣ ChatArea Stages the File

**File:** `ChatArea.jsx` (via useChatArea hook)

```jsx
// State
const [stagedFile, setStagedFile] = useState(null);

// Exposed via useImperativeHandle
useImperativeHandle(ref, () => ({
    setStagedFile,  // ← EXPOSED: so Layout can call it
    ...
}));
```

---

### 6️⃣ User Confirms Upload → Dispatch by Type

**File:** `useChatArea.js` (lines 157-200)

```jsx
const handleConfirmStagedFile = useCallback(() => {
    if (!stagedFile) return;
    const { file, type } = stagedFile;
    
    switch (type) {
        case 'voice':
            sidebarHandlers.handleSidebarVoiceUpload(file);  // ← DISPATCH
            break;
        // ... other types
    }
    
    setStagedFile(null);  // Clear staging
}, [stagedFile]);
```

---

### 7️⃣ Voice Handler Executes API Call

**File:** `useSidebarHandlers.js` (lines 146-197)

```jsx
const handleSidebarVoiceUpload = useCallback(async (file) => {
    // Show loading message
    setUploadMessages(prev => [...prev, {
        content: `🎤 Generating voice for: ${file.name}...`
    }]);
    setIsTyping(true);

    try {
        // Step 1: Parse script
        const parseData = await apiFormData('/parse_script', formData);
        
        // Step 2: Generate voice
        const voiceData = await apiJson('/generate_voice_combined', {
            body: JSON.stringify({
                json_script: parseData.json_script,
                project_id: parseData.project_id
            }),
        });

        // Step 3: Add result message with voice data
        setUploadMessages(prev => [...prev, {
            type: 'voice_preview',      // ← TYPE: triggers VoicePreview
            voiceData: voiceData        // ← DATA: passed to component
        }]);

    } catch (error) {
        // Handle error
    } finally {
        setIsTyping(false);
    }
}, [setUploadMessages, setIsTyping]);
```

---

### 8️⃣ ChatArea Renders VoicePreview

**File:** `ChatArea.jsx` (lines 386-387)

```jsx
{msg.type === 'voice_preview' && msg.voiceData && (
    <VoicePreview voiceData={msg.voiceData} isOpen={true} />
)}
```

**Pattern:** Conditional rendering based on message `type`.

---

## Summary Table

| Step | File | Mechanism | Type |
|------|------|-----------|------|
| 1 | Sidebar | `onClick` → `ref.current.click()` | **Ref** |
| 2 | Sidebar | `<input onChange={...}>` | **Handler** |
| 3 | Sidebar | `onStageFile({ file, type })` | **Prop (up)** |
| 4 | Layout | `chatAreaRef.current.setStagedFile()` | **Ref (down)** |
| 5 | ChatArea | `useImperativeHandle(ref, () => ...)` | **Ref exposure** |
| 6 | useChatArea | `switch(type) → handler()` | **Dispatch** |
| 7 | useSidebarHandlers | `await apiJson(...)` | **API call** |
| 8 | ChatArea | `{msg.type === ... && <Component />}` | **Conditional render** |

---

## Mounting & Lifecycle

| Component | When Mounted | Dependencies |
|-----------|--------------|--------------|
| `Sidebar` | Always (with Layout) | `isOpen`, `toggleSidebar`, `onStageFile`, etc. |
| `ChatArea` | Always (with Layout) | Receives `ref` from Layout |
| `VoicePreview` | When `msg.type === 'voice_preview'` | `voiceData` prop |

---

## Key Patterns Used

1. **Ref forwarding**: Layout → ChatArea via `forwardRef` + `useImperativeHandle`
2. **Sibling communication**: Sidebar → Layout → ChatArea (parent as bridge)
3. **Custom hooks**: `useChatArea` → `useSidebarHandlers` (composition)
4. **Conditional rendering**: Message type determines which component shows
5. **Async handlers**: API calls with loading state (`isTyping`)

---

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER ACTION                                     │
│                     Clicks "Voice Generator" button                         │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SIDEBAR                                                                     │
│  voiceInputRef.current.click() ───► <input onChange={handleVoiceFileSelect}>│
│                                              │                               │
│                                              ▼                               │
│                                 onStageFile({ file, type: 'voice' })        │
└─────────────────────────────────────────────┬───────────────────────────────┘
                                              │ (prop call upward)
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYOUT                                                                      │
│  handleStageFile(stagedData)                                                │
│          │                                                                   │
│          ▼                                                                   │
│  chatAreaRef.current.setStagedFile(stagedData)                              │
└─────────────────────────────────────────────┬───────────────────────────────┘
                                              │ (ref call downward)
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  CHATAREA → useChatArea hook                                                 │
│  stagedFile = { file, type: 'voice' }                                       │
│                                                                              │
│  User confirms ──► handleConfirmStagedFile()                                │
│                           │                                                  │
│                           ▼                                                  │
│                    switch(type)                                             │
│                    case 'voice': handleSidebarVoiceUpload(file)             │
└─────────────────────────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  useSidebarHandlers                                                          │
│  handleSidebarVoiceUpload(file)                                             │
│          │                                                                   │
│          ▼                                                                   │
│  API: /parse_script ───► API: /generate_voice_combined                      │
│          │                          │                                        │
│          ▼                          ▼                                        │
│  setUploadMessages([..., { type: 'voice_preview', voiceData }])             │
└─────────────────────────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  CHATAREA RENDER                                                             │
│  uploadMessages.map(msg => ...)                                             │
│          │                                                                   │
│          ▼                                                                   │
│  {msg.type === 'voice_preview' && <VoicePreview voiceData={msg.voiceData}/>}│
└─────────────────────────────────────────────────────────────────────────────┘
```
