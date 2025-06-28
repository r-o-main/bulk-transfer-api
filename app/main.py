from fastapi import FastAPI

from app.migrations.simple_runner import run_all_migrations
from app.routers import transfers

app = FastAPI(  # https://fastapi.tiangolo.com/reference/fastapi/
    title="Qonto Bulk Transfer API",
    version="0.1.0"
)

app.include_router(transfers.router, prefix="/transfers", tags=["transfers"])

@app.on_event("startup")
def on_startup():
    run_all_migrations()
