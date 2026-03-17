from fastapi import FastAPI
from mangum import Mangum
from src.routers import webhook

app = FastAPI(
    title="Twilio Webhook API",
    version="0.1.0",
    root_path="/prod",
    docs_url="/twilio/docs",
    openapi_url="/twilio/openapi.json"
)
app.include_router(webhook.router)
lambda_handler = Mangum(app, lifespan="off", api_gateway_base_path="/prod")