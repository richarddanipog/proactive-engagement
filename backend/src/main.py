from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from .settings import settings
from .logger import logger
from .schemas import DecisionRequest, DecisionResponse
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


@app.post("/decide", response_model=DecisionResponse)
def decide(req: DecisionRequest):
    session = req.session
    logger.info("Incoming session:", session.dict())
    # cost gate
    gate = (
        (session.current_page in {"product", "cart"})
        and (session.time_on_site >= 30)
    )
    logger.info("Gate passed?", gate)

    if not gate:
        return DecisionResponse(should_show=False, message=None, ttl_seconds=0)

    should, msg, ttl = analyze_session_with_openai(session)

    logger.info("Finished analyze user session.")
    if should and msg:
        return DecisionResponse(should_show=True, message=msg, ttl_seconds=ttl)

    return DecisionResponse(should_show=False, message=None, ttl_seconds=0)
