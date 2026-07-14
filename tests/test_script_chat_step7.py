"""Step 7 test: Tests the SSE streaming API routes.
Hits /script-chat/start, /script-chat/stream/{id}, /script-chat/resume/{id}.
Uses httpx with SSE parsing.
"""
import sys
from pathlib import Path
import asyncio
import json

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import httpx

BASE_URL = "http://localhost:8000"

async def consume_sse(response):
    """Parse SSE events from an httpx streaming response."""
    events = []
    buffer = ""
    async for chunk in response.aiter_text():
        buffer += chunk
        while "\n\n" in buffer:
            raw_event, buffer = buffer.split("\n\n", 1)
            lines = raw_event.strip().split("\n")
            event_type = "message"
            data = ""
            for line in lines:
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    data = line[6:]
            if data:
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    parsed = data
                events.append({"type": event_type, "data": parsed})
                print(f"  📡 {event_type}: {json.dumps(parsed)[:120]}", flush=True)
    return events

async def main():
    print("🚀 Step 7: API Routes + SSE Streaming Test", flush=True)
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        # ── 1. Start a session ──
        print("\n--- POST /script-chat/start ---", flush=True)
        resp = await client.post("/script-chat/start", json={
            "outline": "Tutorial: Creating Tensors in Google Colab\nimport tensorflow as tf\nscalar = tf.constant(5)",
            "foss_name": "TensorFlow"
        })
        
        if resp.status_code != 200:
            print(f"❌ Start failed: {resp.status_code} {resp.text}", flush=True)
            return
        
        start_data = resp.json()
        thread_id = start_data["thread_id"]
        print(f"✅ Thread created: {thread_id}", flush=True)
        
        # ── 2. Connect to SSE stream ──
        print("\n--- GET /script-chat/stream/{thread_id} ---", flush=True)
        async with client.stream("GET", f"/script-chat/stream/{thread_id}") as sse_resp:
            events = await consume_sse(sse_resp)
        
        # Check we got an interrupt
        interrupt_events = [e for e in events if e["type"] == "interrupt"]
        progress_events = [e for e in events if e["type"] == "progress"]
        print(f"\n✅ Got {len(progress_events)} progress events, {len(interrupt_events)} interrupt events", flush=True)
        
        if interrupt_events:
            interrupt_type = interrupt_events[0]["data"].get("type", "unknown")
            print(f"   Interrupt type: {interrupt_type}", flush=True)
        
        # ── 3. Get history ──
        print("\n--- GET /script-chat/history/{thread_id} ---", flush=True)
        resp = await client.get(f"/script-chat/history/{thread_id}")
        if resp.status_code == 200:
            history = resp.json()
            print(f"✅ Stage: {history['current_stage']}, Interrupted: {history['is_interrupted']}", flush=True)
        
        # ── 4. Resume (approve grounding) ──
        print("\n--- POST /script-chat/resume/{thread_id} (approve grounding) ---", flush=True)
        async with client.stream("POST", f"/script-chat/resume/{thread_id}", json={
            "action": "approve"
        }) as sse_resp:
            events = await consume_sse(sse_resp)
        
        interrupt_events = [e for e in events if e["type"] == "interrupt"]
        if interrupt_events:
            interrupt_type = interrupt_events[0]["data"].get("type", "unknown")
            print(f"✅ Next interrupt: {interrupt_type}", flush=True)
        
        # ── 5. Resume (approve metadata) ──
        print("\n--- POST /script-chat/resume/{thread_id} (approve metadata) ---", flush=True)
        async with client.stream("POST", f"/script-chat/resume/{thread_id}", json={
            "action": "approve"
        }) as sse_resp:
            events = await consume_sse(sse_resp)
        
        interrupt_events = [e for e in events if e["type"] == "interrupt"]
        if interrupt_events:
            interrupt_type = interrupt_events[0]["data"].get("type", "unknown")
            print(f"✅ Next interrupt: {interrupt_type}", flush=True)
            if interrupt_type == "script_review":
                script_data = interrupt_events[0]["data"].get("script", [])
                print(f"   Generated {len(script_data)} slides!", flush=True)
        
        # ── 6. Test manual edit (zero tokens) ──
        print("\n--- PUT /script-chat/edit/{thread_id} (manual edit) ---", flush=True)
        resp = await client.put(f"/script-chat/edit/{thread_id}", json={
            "slide_number": 1,
            "field": "narration",
            "value": "Welcome to this amazing spoken tutorial on Tensors!"
        })
        if resp.status_code == 200:
            edit_result = resp.json()
            print(f"✅ Manual edit: {edit_result['message']}", flush=True)
        else:
            print(f"⚠️ Manual edit: {resp.status_code} {resp.text}", flush=True)
        
        # ── 7. Resume (approve script) → compliance ──
        print("\n--- POST /script-chat/resume/{thread_id} (approve script) ---", flush=True)
        async with client.stream("POST", f"/script-chat/resume/{thread_id}", json={
            "action": "approve"
        }) as sse_resp:
            events = await consume_sse(sse_resp)
        
        interrupt_events = [e for e in events if e["type"] == "interrupt"]
        if interrupt_events:
            interrupt_type = interrupt_events[0]["data"].get("type", "unknown")
            print(f"✅ Next interrupt: {interrupt_type}", flush=True)
            if interrupt_type == "compliance_review":
                summary = interrupt_events[0]["data"].get("summary", {})
                print(f"   Compliance: {summary.get('ai_passed', 0)}/{summary.get('total', 0)} passed", flush=True)
        
        # ── 8. Final approve ──
        print("\n--- POST /script-chat/resume/{thread_id} (approve compliance) ---", flush=True)
        async with client.stream("POST", f"/script-chat/resume/{thread_id}", json={
            "action": "approve"
        }) as sse_resp:
            events = await consume_sse(sse_resp)
        
        done_events = [e for e in events if e["type"] == "done"]
        if done_events:
            print(f"✅ Graph complete! Stage: {done_events[0]['data'].get('stage')}", flush=True)
        
        print("\n🎉 Full API test complete!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
