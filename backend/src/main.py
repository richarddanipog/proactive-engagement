from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from .settings import settings
from .schemas import Event, DecisionRequest, DecisionResponse
from .llm_client import analyze_session_with_openai


app = FastAPI(title="Proactive Engagement Backend",
              default_response_class=ORJSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/events")
def ingest_event(event: Event):
    return {"status": "accepted"}


@app.post("/decide", response_model=DecisionResponse)
def decide(req: DecisionRequest):
    session = req.session
    print("[DEBUG] Incoming session:", session.dict())
    # cost gate
    gate = (
        (session.current_page in {"product", "cart"})
        and (session.time_on_site >= 30)
    )
    print("[DEBUG] Gate passed?", gate)

    if not gate:
        return DecisionResponse(should_show=False, message=None, ttl_seconds=0)

    should, msg, ttl = analyze_session_with_openai(session)
    if should and msg:
        return DecisionResponse(should_show=True, message=msg, ttl_seconds=ttl)

    return DecisionResponse(should_show=False, message=None, ttl_seconds=0)
