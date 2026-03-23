from fastapi import FastAPI
from mangum import Mangum
from src.routers import accounts

app = FastAPI(
    title="Accounts API",
    version="0.1.0",
    root_path="/prod",
    docs_url="/accounts/docs",
    openapi_url="/accounts/openapi.json"
)
app.include_router(accounts.router)
lambda_handler = Mangum(app, lifespan="off", api_gateway_base_path="/prod")