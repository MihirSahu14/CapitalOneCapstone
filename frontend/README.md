# Sentinel.AI Frontend

This README covers the `frontend/` portion of the project only. Deployment and production hosting details for the AWS environment are documented separately by the teammate who owns that handoff.

## Repository Link

GitHub repository: [https://github.com/MihirSahu14/CapitalOneCapstone](https://github.com/MihirSahu14/CapitalOneCapstone)

## Frontend Overview

The frontend is a React single-page application for demonstrating the Sentinel.AI fraud detection workflow. It provides three user-facing views:

1. `Past Transactions`
   Loads an account by phone number and displays recent scored transactions returned by the backend.
2. `User Details`
   Loads an existing user, creates a demo user, and updates the fraud score threshold for that account.
3. `New Transaction`
   Submits a new transaction and shows the fraud score and flagged/clear result returned by the API.

The UI is built with:

- React
- React Router
- Axios
- CSS modules for page-specific styling

## Setup Steps

### Prerequisites

- Node.js 18+ recommended
- npm

### Local Setup

1. Open a terminal in the `frontend/` directory.
2. Install dependencies:

```bash
npm install
```

3. Configure the API base URL.

The app reads `REACT_APP_API_BASE_URL` from `frontend/.env`.

- If you want requests to use the deployed backend directly, set:

```env
REACT_APP_API_BASE_URL=https://api.freud.dpdns.org
```

- If `REACT_APP_API_BASE_URL` is left blank, Create React App can still proxy API requests during local development because `package.json` includes:

```json
"proxy": "https://api.freud.dpdns.org"
```

4. Start the development server:

```bash
npm start
```

5. Open `http://localhost:3000`.

### Production Build

To create a production frontend bundle:

```bash
npm run build
```

## How The Frontend Works

### App Structure

- [App.js](/c:/Users/mihir/Desktop/UW%20Madison/Spring%202026/CapitalOneProject/CapitalOne/frontend/src/App.js) sets up the main page shell and the three routes.
- `src/components/Transactions.js` handles account lookup and transaction history display.
- `src/components/User.js` handles user lookup, account creation, and threshold updates.
- `src/components/NewTransaction.js` handles transaction submission and fraud score display.
- `src/api.js` centralizes Axios configuration and normalizes API error messages.
- `src/demoState.js` stores the most recent phone number in `localStorage` so it carries across pages.

### Data Flow

- The user enters a phone number or transaction details in the UI.
- The frontend sends requests to the backend using Axios.
- Responses are rendered into cards, forms, and tables.
- The most recently used phone number is saved in browser `localStorage` and reused across screens.

### Backend Endpoints Used By The Frontend

- `GET /accounts/by-phone/:phone`
- `POST /accounts`
- `PATCH /accounts/by-phone/:phone/threshold`
- `POST /transactions`

## What Works

- Navigation between all three frontend pages
- Loading account details by registered phone number
- Viewing recent transactions for an account
- Creating a demo user from the UI
- Updating an account fraud threshold
- Submitting a transaction for live fraud scoring
- Displaying API success and error states in the UI
- Reusing the last entered phone number across pages

## What Does Not Work / Current Limitations

- This frontend depends on the backend API being available; without the API, the pages cannot demonstrate their main flows
- There is no authentication or role-based access control in the frontend
- Form validation is basic and mostly relies on backend validation for invalid payloads
- Automated frontend tests were not built out beyond the default React tooling setup
- The README does not document AWS deployment because that production handoff is maintained separately

## What We Would Work On Next

- Add stronger client-side validation and clearer inline form guidance
- Add loading skeletons and more polished empty/error states
- Add automated tests for routing, forms, and API response handling
- Improve accessibility coverage for keyboard navigation and screen readers
- Add filtering/sorting for transaction history
- Add authentication if this moved beyond a demo workflow

## Additional Notes For Final Handoff

- Frontend code lives in the `frontend/` directory of the main repository.
- The frontend is designed to work with the deployed backend API used by the team demo.
- Any AWS hosting, production deployment, or infrastructure notes should be taken from the separate deployment/production README maintained by the teammate responsible for that environment.
