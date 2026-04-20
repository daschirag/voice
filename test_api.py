import httpx, json, time, os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

print("=== SPEECH ANALYSIS SYSTEM - API TEST ===")
print()

# Step 1: Health check first
print("Health check...")
h = httpx.get("http://localhost:8000/api/v1/health", timeout=10.0)
health = h.json()
print(f"  Status : {health['status']}")
print(f"  GPU    : {health['gpu_name']}")
print(f"  Whisper: {health['models_loaded']['whisper']}")
print()

# Step 2: Upload with long timeout (pipeline takes ~15-30s)
print("Uploading test_speech.wav...")
with open("uploads/test_speech.wav", "rb") as f:
    r = httpx.post(
        "http://localhost:8000/api/v1/analyze",
        files={"file": ("test_speech.wav", f, "audio/wav")},
        data={"role": "general"},
        timeout=120.0,    # 2 minute timeout - enough for full pipeline
    )

print(f"HTTP Status: {r.status_code}")

if r.status_code != 200:
    print(f"Error: {r.text}")
    exit()

result = r.json()
job_id = result["job_id"]
print(f"Job ID : {job_id}")
print(f"Status : {result['status']}")
print()

# Step 3: Poll for completion
print("Polling...")
final_status = None
for i in range(90):
    time.sleep(2)
    try:
        s = httpx.get(
            f"http://localhost:8000/api/v1/status/{job_id}",
            timeout=10.0
        )
        status = s.json()
        progress = status.get("progress", 0)
        msg = status.get("message", "")
        st = status["status"]
        print(f"  [{i*2:3}s] {st:12} {progress:3}% | {msg}")
        if st in ("completed", "failed"):
            final_status = st
            break
    except Exception as e:
        print(f"  Poll error: {e}")
        continue

print()

# Step 4: Get report
if final_status == "completed":
    print("Fetching report...")
    r2 = httpx.get(
        f"http://localhost:8000/api/v1/report/{job_id}",
        timeout=15.0
    )
    report = r2.json()
    results = report.get("results", {})
    dims = report.get("dimensions", {})

    print("=== FINAL RESULTS ===")
    print(f"Score   : {results['composite_score']}/5.0")
    print(f"Grade   : {results['grade']}")
    print(f"Percent : {results['composite_pct']}%")
    print()
    print("Dimensions:")
    for k, d in dims.items():
        bar = round(d["score"])
        blocks = chr(9608) * bar + chr(9617) * (5 - bar)
        print(f"  {d['name']:22}: {d['score']:.1f}/5  {blocks}")
    print()
    print("Improvement priorities:", results.get("improvement_priorities"))
    print()
    print("Summary:")
    print(" ", results["summary"])
    print()
    print("=== LINKS ===")
    print(f"  HTML : http://localhost:8000/reports/{job_id}_report.html")
    print(f"  PDF  : http://localhost:8000/api/v1/report/{job_id}/pdf")
elif final_status == "failed":
    print(f"Job failed")
else:
    print("Job did not complete in time - check server terminal for errors")
    print(f"Try manually: http://localhost:8000/api/v1/status/{job_id}")