import httpx, json, time, os, sys
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

AUDIO_FILE = sys.argv[1] if len(sys.argv) > 1 else "uploads/test_speech.wav"
ROLE = sys.argv[2] if len(sys.argv) > 2 else "general"

if not os.path.exists(AUDIO_FILE):
    print(f"File not found: {AUDIO_FILE}")
    exit()

file_size = os.path.getsize(AUDIO_FILE) / (1024*1024)
print("=== SPEECH ANALYSIS SYSTEM ===")
print(f"File : {AUDIO_FILE}")
print(f"Size : {file_size:.1f} MB")
print(f"Role : {ROLE}")
print()

print("Uploading...")
filename = os.path.basename(AUDIO_FILE)
ext = os.path.splitext(filename)[1].lower()
mime_map = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}
mime = mime_map.get(ext, "audio/wav")

with open(AUDIO_FILE, "rb") as f:
    r = httpx.post(
        "http://localhost:8000/api/v1/analyze",
        files={"file": (filename, f, mime)},
        data={"role": ROLE},
        timeout=300.0,
    )

if r.status_code != 200:
    print(f"Upload failed: {r.status_code}")
    print(r.text[:500])
    exit()

result = r.json()
job_id = result["job_id"]
print(f"Job ID : {job_id}")
print(f"Status : {result['status']}")
print()

if result["status"] != "completed":
    print("Polling...")
    for i in range(120):
        time.sleep(2)
        s = httpx.get(f"http://localhost:8000/api/v1/status/{job_id}", timeout=10.0)
        status = s.json()
        progress = status.get("progress", 0)
        msg = status.get("message", "")
        print(f"  [{i*2:3}s] {status['status']:12} {progress:3}% | {msg}")
        if status["status"] in ("completed", "failed"):
            break

print()
r2 = httpx.get(f"http://localhost:8000/api/v1/report/{job_id}", timeout=15.0)
report = r2.json()
results = report.get("results", {})
dims = report.get("dimensions", {})
meta = report.get("metadata", {})

print("=== RESULTS ===")
print(f"File     : {meta.get('filename')}")
print(f"Duration : {meta.get('duration_seconds')}s")
print(f"Language : {meta.get('language')}")
print(f"ASR Conf : {meta.get('asr_confidence')}")
print()
print(f"Score    : {results['composite_score']}/5.0")
print(f"Grade    : {results['grade']}")
print(f"Percent  : {results['composite_pct']}%")
print()
print("Dimensions:")
for k, d in dims.items():
    bar = round(d["score"])
    blocks = chr(9608) * bar + chr(9617) * (5 - bar)
    print(f"  {d['name']:22}: {d['score']:.1f}/5  {blocks}")
print()
print("Priorities:", results.get("improvement_priorities"))
print()
print("Transcript (first 300 chars):")
print(" ", report.get("transcript", "")[:300])
print()
print("=== LINKS ===")
print(f"  HTML : http://localhost:8000/reports/{job_id}_report.html")
print(f"  PDF  : http://localhost:8000/api/v1/report/{job_id}/pdf")
print(f"  JSON : http://localhost:8000/api/v1/report/{job_id}")