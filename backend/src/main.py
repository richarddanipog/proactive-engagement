from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from .settings import settings
from .schemas import Event, DecisionRequest, DecisionResponse


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

    should = (
        session.current_page == "product"
        and session.time_on_site >= 90
        and session.cart_items == 0
    )

    if should:
        return DecisionResponse(
            should_show=True,
            message="Still thinking? Here's a quick tip: check reviews below 👇",
            ttl_seconds=120,
        )

    return DecisionResponse(should_show=False, message=None, ttl_seconds=0)
