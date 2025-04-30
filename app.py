from fastapi import FastAPI

from router import router

app = FastAPI(
    title="Bitcoinstats API",
    description="This is a simple API for getting Bitcoin network statistics computed from bitcoin-core",
)

app.include_router(router)
