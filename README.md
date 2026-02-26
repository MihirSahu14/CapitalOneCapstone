# Fraud Detection System - Capital One Capstone

This repo is a production-style starter for your capstone requirements:
- Fraud score per transaction in `[0, 1]`
- User-configurable alert threshold
- SMS notification with Twilio
- Reply-to-confirm fraud updates in DB
- REST API for account + transaction creation
- AWS-native event-driven architecture

## 1) Architecture (high level)

1. `POST /accounts` creates user profile with phone number + fraud alert threshold.
2. `POST /transactions` creates transaction and emits an event.
3. Event triggers fraud scoring Lambda:
   - Loads trained model artifact.
   - Predicts fraud probability.
   - Converts probability to uniform percentile score (`0-1`).
4. If score >= user threshold, Twilio SMS is sent.
5. User replies `YES` or `NO`; Twilio webhook updates transaction fraud flag.

Detailed diagram: [docs/architecture.md](/c:/Users/mihir/Desktop/UW%20Madison/Spring%202026/CapitalOneProject/CapitalOneCapstone/docs/architecture.md)

## 2) Project structure

- `src/api/app.py`: FastAPI endpoints for account + transaction simulation.
- `src/model/train.py`: model training script on historical dataset.
- `src/model/scorer.py`: scoring + uniform percentile transform.
- `src/lambdas/process_transaction.py`: event-driven scoring + alert send.
- `src/lambdas/twilio_webhook.py`: process customer SMS response.
- `src/shared/db.py`: DynamoDB data access helpers.
- `infra/template.yaml`: AWS SAM infrastructure template.
- `tests/test_scorer.py`: unit test for uniform score transform.

## 3) Quick start (local)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.api.app:app --reload
```

API docs:
- `http://127.0.0.1:8000/docs`

## 4) Environment variables

Copy `.env.example` to `.env` and set:
- AWS: DynamoDB table names and region
- Twilio: account SID, auth token, from number

## 5) Train the fraud model

Expected CSV columns:
- Features: `amount, merchant, location, timestamp`
- Label: `is_fraud` (`0` or `1`)

Run:

```powershell
python -m src.model.train --data data\raw\transactions.csv --out data\processed\model.joblib
```

The saved artifact includes:
- Preprocessing + classifier pipeline
- Calibration scores used for percentile ranking

## 6) Deploy to AWS (SAM)

```powershell
sam build -t infra\template.yaml
sam deploy --guided
```

After deploy:
1. Configure Twilio webhook URL to API Gateway `/twilio/webhook`.
2. Store model artifact where Lambda can load it (S3 or bundled artifact).
3. Set Lambda environment variables in SAM parameters.

## 7) Suggested next implementation milestones

1. Connect `POST /transactions` to EventBridge/SQS for async processing.
2. Add model performance reporting (AUC, precision/recall, confusion matrix).
3. Add dead-letter queue + retries for SMS sends.
4. Add periodic retraining pipeline (weekly/monthly).
