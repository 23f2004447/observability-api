import json
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

EMAIL = "23f2004447@ds.study.iitm.ac.in"        # <-- put YOUR logged-in email here

START_TIME = time.monotonic()           # the moment the server started

# The clicker. Exposed as "http_requests_total" in /metrics.
REQUESTS = Counter("http_requests_total", "Total HTTP requests")

# The diary: remembers the last 1000 entries, forgets older ones.
LOGS = deque(maxlen=1000)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# This function runs for EVERY request, whatever the endpoint is.
@app.middleware("http")
async def observe(request: Request, call_next):
    REQUESTS.inc()                                  # click the counter
    request_id = str(uuid.uuid4())
    start = time.perf_counter()

    response = await call_next(request)

    entry = {
        "level": "INFO",
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
        "request_id": request_id,
        "method": request.method,
        "status": response.status_code,
        "duration_s": round(time.perf_counter() - start, 6),
    }
    LOGS.append(entry)                              # write in the diary
    print(json.dumps(entry), flush=True)            # also print it (shows in Render's log page)

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/work")
def work(n: int = Query(1, ge=0)):
    # Do some real (small) work, then report how much was requested.
    sum(range(min(n, 1_000_000)))
    return {"email": EMAIL, "done": n}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": time.monotonic() - START_TIME}


@app.get("/logs/tail")
def logs_tail(limit: int = Query(10, ge=0, le=1000)):
    if limit == 0:
        return []
    return list(LOGS)[-limit:]