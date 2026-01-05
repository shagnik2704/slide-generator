# System Design: Multi-Language Translation Agent

## Overview

This document defines the architecture for a multi-language translation feature that allows users to translate scripts into multiple Indian languages simultaneously.

---

## Requirements Summary

| Requirement | Description |
|-------------|-------------|
| **Multi-language** | Support Hindi, Tamil, Telugu, Marathi, Bengali, Kannada |
| **Batch translation** | Translate to multiple languages in one request |
| **Preserve formatting** | Keep bold markers, technical terms |
| **Transliteration** | Technical terms stay in English (or transliterated) |
| **Output formats** | JSON script + DOCX download |
| **User selection** | Checkbox-based language picker |

---

## Supported Languages

| Code | Language | Native Script |
|------|----------|---------------|
| `hi` | Hindi | हिंदी |
| `ta` | Tamil | தமிழ் |
| `te` | Telugu | తెలుగు |
| `mr` | Marathi | मराठी |
| `bn` | Bengali | বাংলা |
| `kn` | Kannada | ಕನ್ನಡ |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
│                                                                              │
│   Sidebar                                                                   │
│      │                                                                       │
│      └── TranslationModal                                                   │
│              ├── FilePreview (staged script)                                │
│              ├── LanguageSelector (checkboxes)                              │
│              └── Action buttons                                             │
│                                                                              │
│   ChatArea                                                                   │
│      │                                                                       │
│      └── TranslationResults (per-language cards with download)              │
│                                                                              │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                         │
│                                                                              │
│   routers/translation.py                                                    │
│      │                                                                       │
│      ├── POST /translation/translate (single language)                      │
│      ├── POST /translation/batch_translate (multi-language)                 │
│      └── GET  /translation/languages (supported list)                       │
│                                                                              │
│   services/translation_service.py                                           │
│      │                                                                       │
│      ├── translate_script(script, target_lang)                              │
│      ├── batch_translate(script, languages[])                               │
│      └── generate_docx(translated_script, lang)                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## User Flow

```
1. User clicks "Translate Script" in Sidebar
         │
         ▼
2. File picker opens → User selects script.docx
         │
         ▼
3. TranslationModal appears with language checkboxes
         │
         ▼
4. User selects: ☑ Hindi  ☑ Tamil  ☐ Telugu  ☐ Marathi
         │
         ▼
5. Clicks "Translate to 2 languages"
         │
         ▼
6. API: POST /translation/batch_translate
         │
         ▼
7. Backend translates in parallel (asyncio.gather)
         │
         ▼
8. Results display with download buttons per language
```

---

## Component Design

### Frontend Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `TranslationModal` | `components/TranslationModal.jsx` | File preview + language picker |
| `LanguageSelector` | `components/LanguageSelector.jsx` | Checkbox grid for languages |
| `TranslationResults` | `components/TranslationResults.jsx` | Results with download links |

### TranslationModal Structure

```jsx
<TranslationModal isOpen={isOpen} onClose={onClose}>
    <FilePreview file={stagedFile} />
    
    <LanguageSelector
        languages={SUPPORTED_LANGUAGES}
        selected={selectedLanguages}
        onChange={setSelectedLanguages}
    />
    
    <ActionButtons>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleTranslate} disabled={selectedLanguages.length === 0}>
            Translate to {selectedLanguages.length} language(s)
        </Button>
    </ActionButtons>
</TranslationModal>
```

### TranslationResults Structure

```jsx
<TranslationResults results={results}>
    {results.map(result => (
        <ResultCard key={result.language}>
            <LanguageFlag code={result.language} />
            <LanguageName>{result.language_name}</LanguageName>
            <Status>{result.success ? '✅' : '❌'}</Status>
            <DownloadButton href={result.docx_url}>
                Download DOCX
            </DownloadButton>
        </ResultCard>
    ))}
</TranslationResults>
```

---

## Backend Design

### File Structure

```
src/
├── services/
│   └── translation_service.py    # Core translation logic
│
├── routers/
│   └── translation.py            # API endpoints
│
└── models/
    └── translation_models.py     # Pydantic schemas
```

### Pydantic Models

```python
from pydantic import BaseModel
from typing import List, Optional

class TranslateRequest(BaseModel):
    json_script: dict
    target_language: str
    project_id: Optional[str] = None

class BatchTranslateRequest(BaseModel):
    json_script: dict
    languages: List[str]
    project_id: Optional[str] = None

class TranslationResult(BaseModel):
    language: str
    language_name: str
    translated_script: dict
    docx_url: Optional[str] = None
    success: bool
    error: Optional[str] = None

class BatchTranslateResponse(BaseModel):
    results: List[TranslationResult]
    total_requested: int
    total_success: int
```

### Translation Service

```python
class TranslationService:
    SUPPORTED_LANGUAGES = {
        "hi": {"name": "Hindi", "native": "हिंदी"},
        "ta": {"name": "Tamil", "native": "தமிழ்"},
        "te": {"name": "Telugu", "native": "తెలుగు"},
        "mr": {"name": "Marathi", "native": "मराठी"},
        "bn": {"name": "Bengali", "native": "বাংলা"},
        "kn": {"name": "Kannada", "native": "ಕನ್ನಡ"},
    }
    
    async def translate_script(
        self, 
        json_script: dict, 
        target_language: str
    ) -> dict:
        """Translate script to a single target language."""
        slides = json_script.get("slides", [])
        
        prompt = self._build_translation_prompt(slides, target_language)
        result = await self.llm.ainvoke(prompt)
        
        return self._merge_translations(json_script, result)
    
    async def batch_translate(
        self,
        json_script: dict,
        languages: List[str]
    ) -> List[TranslationResult]:
        """Translate to multiple languages in parallel."""
        tasks = [
            self._translate_with_result(json_script, lang)
            for lang in languages
            if lang in self.SUPPORTED_LANGUAGES
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _translate_with_result(
        self,
        json_script: dict,
        language: str
    ) -> TranslationResult:
        """Wrap translation with error handling."""
        try:
            translated = await self.translate_script(json_script, language)
            docx_path = await self._generate_docx(translated, language)
            
            return TranslationResult(
                language=language,
                language_name=self.SUPPORTED_LANGUAGES[language]["name"],
                translated_script=translated,
                docx_url=docx_path,
                success=True
            )
        except Exception as e:
            return TranslationResult(
                language=language,
                language_name=self.SUPPORTED_LANGUAGES[language]["name"],
                translated_script={},
                success=False,
                error=str(e)
            )
```

### API Endpoints

```python
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/translation", tags=["translation"])
translation_service = TranslationService()

@router.get("/languages")
async def get_languages():
    """Return supported languages."""
    return translation_service.SUPPORTED_LANGUAGES

@router.post("/translate")
async def translate_script(data: TranslateRequest) -> TranslationResult:
    """Translate to a single language."""
    if data.target_language not in translation_service.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported language: {data.target_language}")
    
    result = await translation_service.translate_script(
        data.json_script,
        data.target_language
    )
    return result

@router.post("/batch_translate")
async def batch_translate(data: BatchTranslateRequest) -> BatchTranslateResponse:
    """Translate to multiple languages in parallel."""
    results = await translation_service.batch_translate(
        data.json_script,
        data.languages
    )
    
    return BatchTranslateResponse(
        results=results,
        total_requested=len(data.languages),
        total_success=sum(1 for r in results if r.success)
    )
```

---

## Translation Prompt Template

```python
TRANSLATION_PROMPT = """You are an expert English-to-{language} translator for Spoken Tutorial scripts.

**Rules:**
1. Translate ONLY the narration text
2. Use natural, conversational {language}
3. Keep technical terms in English (e.g., Python, Linux, Terminal)
4. Preserve **bold** markers around technical terms
5. Each sentence should be speakable in one breath (~100 characters max)

**Script to translate:**
{slides_json}

Return translations in the same JSON structure with a new field `narration_{lang_code}` for each slide.
"""
```

---

## Output Files

| File | Location | Description |
|------|----------|-------------|
| Script JSON | In-memory | Translated script with dual-language narrations |
| DOCX | `output/translations/{project_id}/{language}.docx` | Downloadable document |

### DOCX Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  Script: Python Tutorial                                        │
│  Language: Hindi (हिंदी)                                         │
│  Generated: 2026-01-05                                          │
├─────────────────────────────────────────────────────────────────┤
│  Slide 1                                                        │
│  ─────────────────────────                                      │
│  Visual: Show terminal                                          │
│  English: Open the terminal and type python.                    │
│  Hindi: टर्मिनल खोलें और python टाइप करें।                       │
├─────────────────────────────────────────────────────────────────┤
│  Slide 2                                                        │
│  ...                                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend Handlers

### Sidebar Integration

```jsx
// In Sidebar.jsx
const translationInputRef = useRef(null);

const handleTranslationFileSelect = (e) => {
    const file = e.target.files[0];
    if (file && onStageFile) {
        onStageFile({ file, type: 'translation' });
        e.target.value = '';
    }
};

// Button
<TooltipWrapper text="Translate Script">
    <button onClick={() => translationInputRef.current?.click()}>
        <Languages size={20} />
        {isOpen && <span>Translate Script</span>}
    </button>
</TooltipWrapper>
```

### useChatArea Handler

```jsx
// In useChatArea.js
case 'translation':
    setTranslationModalOpen(true);
    setTranslationStagedFile(file);
    break;
```

---

## Error Handling

| Error | User Message |
|-------|--------------|
| Unsupported language | "Language not supported" |
| Script parsing failed | "Could not parse script file" |
| Translation failed | "Translation failed for {language}: {error}" |
| DOCX generation failed | "Could not generate document" |

---

## Implementation Phases

### Phase 1: Backend (2-3 days)
- [ ] Create `translation_service.py`
- [ ] Create `translation.py` router
- [ ] Add Pydantic models
- [ ] Test single-language translation
- [ ] Test batch translation

### Phase 2: Frontend Modal (2 days)
- [ ] Create `TranslationModal.jsx`
- [ ] Create `LanguageSelector.jsx`
- [ ] Add sidebar button
- [ ] Wire up to useChatArea

### Phase 3: Results Display (1-2 days)
- [ ] Create `TranslationResults.jsx`
- [ ] Add download functionality
- [ ] Handle error states

### Phase 4: DOCX Export (1 day)
- [ ] Generate translated DOCX
- [ ] Dual-language format
- [ ] Download endpoint

---

## Future Enhancements

1. **Quality check integration**: Run translation through back-translation quality check
2. **Glossary support**: Custom technical term translations per project
3. **Batch file translation**: Translate multiple scripts at once
4. **Translation memory**: Reuse previous translations for efficiency
5. **Edit before download**: Let user review/edit translations

---

## References

- [Existing Quality Service](/src/services/quality_service.py) - Has translation logic
- [DOCX Exporter](/src/utils/docx_exporter.py) - Document generation
- [Database Design](/docs/SYSTEM_DESIGN_DATABASE.md) - Assets table for translations
