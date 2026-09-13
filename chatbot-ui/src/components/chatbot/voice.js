/**
 * Voice STT / TTS service helpers for the FAQ chatbot.
 */
import { apiJson, apiFormData } from '../../services/api';

export async function fetchVoiceStatus() {
    try {
        const data = await apiJson('/faq/voice/status');
        return { enabled: Boolean(data?.enabled) };
    } catch {
        return { enabled: false };
    }
}

export async function transcribeAudio(blob) {
    const formData = new FormData();
    const webmBlob = blob.type === 'audio/webm' ? blob : new Blob([blob], { type: 'audio/webm' });
    formData.append('file', webmBlob, 'recording.webm');

    const data = await apiFormData('/faq/voice/transcribe', formData);
    return data.transcript;
}

export async function synthesizeSpeech(text) {
    const data = await apiJson('/faq/voice/synthesize', {
        method: 'POST',
        body: JSON.stringify({ text }),
    });
    return `data:${data.content_type};base64,${data.audio_base64}`;
}

export function playAudioDataUrl(dataUrl) {
    const audio = new Audio(dataUrl);
    void audio.play();
    return audio;
}
