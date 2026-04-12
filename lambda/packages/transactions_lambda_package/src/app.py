from fastapi import FastAPI
from mangum import Mangum
from src.routers import transactions

app = FastAPI(
    title="Transactions API",
    version="0.1.0",
    root_path="/prod",
    docs_url="/transactions/docs",
    openapi_url="/transactions/openapi.json"
)
app.include_router(transactions.router)

@app.get("/health")
def health():
    return {"status": "ok"}

lambda_handler = Mangum(app, lifespan="off", api_gateway_base_path="/prod")