from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import router
from app.database import engine
from app.models import Base

app = FastAPI(title="Chat",
              docs_url="/docs",
              openapi_url="/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router.router)

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)