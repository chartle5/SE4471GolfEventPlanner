# SE4471 Golf Event Planner

A full-stack web application for planning and managing golf tournaments. The application features an AI-powered chat assistant for tournament planning and a responsive React frontend for visualization and management.

## Features

- **AI-Powered Planning**: Chat-based tournament planning using Azure OpenAI
- **RAG Proof of Concept**: Local document chunking with in-memory embeddings for lightweight retrieval
- **Local MCP Weather Server**: Streamable HTTP MCP sidecar for live weather plus sunrise and sunset lookup worldwide
- **Tournament Management**: Create and manage golf tournament details
- **Knowledge Base**: Access tournament planning resources and best practices
- **Workflow Visualization**: View planning workflows and artifacts
- **Responsive Design**: Modern React interface with clean UI

## Tech Stack

- **Backend**: Python FastAPI with Azure OpenAI integration
- **Frontend**: React with Vite, React Router
- **AI**: Azure OpenAI GPT chat models plus a lightweight in-memory RAG layer with local embeddings
- **MCP**: Local Python MCP server for external API access during development

## Prerequisites

Before setting up the project, ensure you have the following installed:

- **Node.js** (version 16 or higher) - for the frontend
- **Python** (version 3.10 or higher) - for the backend and local MCP server
- **Azure OpenAI Account** - for AI chat functionality

You can download Node.js from [nodejs.org](https://nodejs.org/) and Python from [python.org](https://python.org/).

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd SE4471GolfEventPlanner
```

### 2. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a Python virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the `backend` directory with your credentials:
   ```env
   AZURE_OPENAI_API_KEY=your_api_key_here
   AZURE_OPENAI_API_VERSION=2023-12-01-preview
   AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT=your-deployment-name
   MCP_WEATHER_SERVER_URL=http://127.0.0.1:8001/mcp
   MONGODB_SERVER_SELECTION_TIMEOUT_MS=5000
   MONGODB_STARTUP_REQUIRED=false
   RAG_LOCAL_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   LOG_LLM_PROMPTS=false

   # JWT (authentication)
   JWT_SECRET=replace_with_a_long_random_string
   JWT_ALGORITHM=HS256
   JWT_EXPIRE_MINUTES=10080

   # SMTP email (replaces SendGrid)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_gmail_address@gmail.com
   SMTP_PASSWORD=your_16_char_app_password
   SMTP_FROM_EMAIL=your_gmail_address@gmail.com
   SMTP_FROM_NAME=Golf Event Planner
   ```

   **SMTP / Gmail setup:** enable 2-Step Verification on your Google account, then go to
   **myaccount.google.com → Security → App Passwords** and generate a 16-character app
   password. Use that value for `SMTP_PASSWORD`. Any other SMTP provider (Outlook, etc.)
   works by changing `SMTP_HOST` and `SMTP_PORT`.

   Replace the placeholder values with your actual Azure OpenAI resource details.
   `MCP_WEATHER_SERVER_URL` is optional and defaults to `http://127.0.0.1:8001/mcp`.
   `MONGODB_SERVER_SELECTION_TIMEOUT_MS` controls how long the backend waits for MongoDB
   during startup. `MONGODB_STARTUP_REQUIRED=false` lets chat and other non-database routes
   start even when MongoDB is unavailable.
   `RAG_LOCAL_EMBEDDING_MODEL` is optional and defaults to
   `sentence-transformers/all-MiniLM-L6-v2`, which runs locally in Python for the
   RAG proof of concept. Set `LOG_LLM_PROMPTS=true` when you want the backend console
   to print the retrieval query, the retrieved chunks forwarded into the prompt, any
   retrieval error, and the exact `messages` payload sent to the chat model.

6. Start the backend server:
   ```bash
   uvicorn app.main:app --reload
   ```

   The backend will run on `http://localhost:8000`.

7. Start the local MCP weather server in a second backend terminal:
   ```bash
   uvicorn mcp_weather_server:app --reload --port 8001
   ```

   The MCP server will run on `http://localhost:8001`, and the Streamable HTTP
   MCP endpoint will be `http://localhost:8001/mcp`.

### 3. Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

   The frontend will run on `http://localhost:5173`.

### 4. Access the Application

Open your browser and navigate to `http://localhost:5173` to access the Golf Event Planner application.

## Local MCP Weather Server

The repository includes a local MCP sidecar at `backend/mcp_weather_server.py`.
It uses Open-Meteo for global geocoding plus forecast data, including daily
`sunrise` and `sunset` values.

Available tools:

- `search_weather_locations` - resolve ambiguous place names into candidate locations
- `get_weather_forecast` - current weather plus daily sunrise and sunset for a named location
- `get_weather_forecast_by_coordinates` - the same data for exact latitude and longitude

Quick local verification:

1. Start the MCP server:
   ```bash
   cd backend
   uvicorn mcp_weather_server:app --reload --port 8001
   ```
2. Visit `http://localhost:8001/` for server metadata or `http://localhost:8001/healthz` for a health check.
3. Point an MCP client or inspector at `http://localhost:8001/mcp`.

When the MCP server is running, the chatbot can answer live weather questions such
as "What is the current temperature in Toronto?" or "When is sunrise in St Andrews?".

## Project Structure

```
SE4471GolfEventPlanner/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── data/
│   │   │   └── knowledge_documents.py  # Local RAG source documents
│   │   ├── main.py          # FastAPI application
│   │   ├── models.py        # Pydantic models
│   │   ├── routes/
│   │   │   └── chat.py      # Chat API endpoints
│   │   └── services/
│   │       ├── agent.py     # Chat orchestration and prompt handling
│   │       ├── openai_client.py  # Shared Azure OpenAI client configuration
│   │       ├── rag.py       # Local chunking and in-memory retrieval
│   │       └── weather_service.py  # Open-Meteo geocoding and forecast integration
│   ├── mcp_weather_server.py # Local Streamable HTTP MCP sidecar
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── data/           # Mock data
│   │   ├── pages/          # Application pages
│   │   └── App.jsx         # Main React app
│   ├── package.json        # Node dependencies
│   └── vite.config.js      # Vite configuration
└── README.md
```

## API Endpoints

- `GET /` - Health check
- `POST /chat` - AI-powered tournament planning chat

## RAG Proof of Concept

The chatbot now includes a lightweight retrieval-augmented generation pipeline designed
for a small local knowledge base:

- Source documents live in `backend/app/data/knowledge_documents.py`
- Documents are chunked locally in `backend/app/services/rag.py`
- Chunk embeddings are generated locally with `sentence-transformers` and cached in an in-memory array
- Each chat request embeds the user query, ranks chunks with cosine similarity, and
  injects the top snippets into the planning prompt
- No database is used; restarting the backend rebuilds the in-memory index on demand

On first use, the local embedding model may need to be downloaded, so the machine
running the backend needs internet access once for the model fetch unless it is already cached.

This setup is intended for a small proof of concept with roughly ten short documents.
If the corpus grows, the next step would be moving chunk storage and metadata into a
vector database or a persistent file-backed index.

## Populating a Tournament with Test Players

The script `register_test_players.sh` at the project root lets you quickly fill a
tournament with dummy players for testing — no manual form filling required.

### Prerequisites

- Both the **backend** (`http://localhost:8000`) and **frontend** (`http://localhost:5173`) must be running.
- A tournament must already be **created and saved** through the UI (Plan Tournament → Save Tournament).
- `curl` and `python3` must be available (standard on macOS/Linux).

### Step 1 — Create and save a tournament

1. Open `http://localhost:5173` and log in.
2. Go to **Plan Tournament** and use the AI chat to build a tournament:
   - Set a **player count** (e.g. 20).
   - Set **event type** to `team` and choose a **team size** (1, 2, or 4) if you want grouped teams.
   - Include catering if you want to test the F&B Summary document.
3. Once the AI finishes, click **Save Tournament** on the Schedule Draft page.

### Step 2 — Find the registration token

The registration token is a UUID string that the backend assigns when you save a tournament. You need it to tell the script which tournament to register players into.

**Option A — DevTools (always works)**

1. With the app open at `http://localhost:5173`, press **F12** (or right-click anywhere on the page → **Inspect**) to open DevTools.
2. Click the **Application** tab at the top of DevTools.
   - If you don't see it, click the **»** overflow arrow — it may be hidden.
3. In the left sidebar, expand **Local Storage** and click **`http://localhost:5173`**.
4. In the key list on the right, click the row named **`savedReservations`**.
5. The value panel will show a JSON array. Each item is a saved tournament. Find the one you just saved (check the `name` or `savedAt` fields).
6. Look for the field **`registration_token`** inside that item. It looks like:
   ```
   "registration_token": "9a667837-f3ff-4933-8f85-323948ceb547"
   ```
7. Copy that UUID value — that is what you paste into the script prompt.

> **Tip:** The most recently saved tournament is usually the last item in the array. If the JSON appears collapsed, click the triangle/arrow next to the array to expand it, then expand the individual tournament object to see all its fields.

### Step 3 — Run the script

From the project root:

```bash
./register_test_players.sh
```

If the backend is running on a different port, prefix your URL:

```bash
BACKEND_URL=http://localhost:8001 ./register_test_players.sh
```

The script will:

1. Ask for the **registration token** — paste the UUID from Step 2.
2. Fetch and display the tournament details so you can confirm it's the right one.
3. Ask for the **team size** to use when grouping players (enter `1`, `2`, or `4`).
   - Use the same value as the tournament's saved team size to avoid warnings.
4. Ask **how many players** to register (capped at the remaining slot count).
5. Register each player (`Player 1`, `Player 2`, …) with sequential team names
   (`Team 1`, `Team 2`, …) and print a ✓ or ✗ for each.

### Step 4 — Verify

- Go to **Reservations** → select your tournament → **View Registrants**.
- All registered players should appear, grouped by team.
- **Cart Placards** will now render with real player names.
- The **Schedule** will show players assigned to tee times.

### Notes

- Players are named `Player 1`, `Player 2`, etc. — fine for testing, not for demos to clients.
- If you run the script multiple times, player numbering continues from the current
  registration count so names will not overlap.
- The script warns you if your chosen team size differs from the tournament's saved
  setting — the backend will reject registrations that exceed the per-team cap.
- To reset players, delete the tournament from Reservations and re-save it, then
  re-run the script.

---

## Troubleshooting

### Backend Issues

- **Module not found errors**: Ensure you're in the virtual environment and all dependencies are installed with `pip install -r requirements.txt`
- **Azure OpenAI errors**: Verify your `.env` file has correct Azure OpenAI credentials
- **Port already in use**: The backend runs on port 8000 by default. If it's occupied, you can specify a different port: `uvicorn app.main:app --reload --port 8001`
- **MCP server port already in use**: Start the MCP server on another port, for example `uvicorn mcp_weather_server:app --reload --port 8002`
- **Email not sending**: Confirm `SMTP_HOST`, `SMTP_USERNAME`, and `SMTP_PASSWORD` are set in `backend/.env`. For Gmail, use an App Password (not your normal account password).

### JWT Token Verification

Use these commands from the `backend/` directory to inspect and test your JWT configuration without starting the server:

**Decode a token (no signature check — inspect payload only):**
```bash
python3 -c "
import sys, base64, json
token = sys.argv[1]
part = token.split('.')[1]
part += '=' * (-len(part) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(part)), indent=2))
" YOUR_TOKEN_HERE
```

**Verify a token against your current JWT_SECRET (checks signature + expiry):**
```bash
python3 -c "
import os; from dotenv import load_dotenv; load_dotenv()
from jose import jwt, JWTError
token = input('Paste token: ')
try:
    payload = jwt.decode(token, os.getenv('JWT_SECRET','change_me'), algorithms=[os.getenv('JWT_ALGORITHM','HS256')])
    print('VALID:', payload)
except JWTError as e:
    print('INVALID:', e)
"
```

**Generate a fresh test token:**
```bash
python3 -c "
import os; from dotenv import load_dotenv; load_dotenv()
from app.services.auth_service import create_access_token
token = create_access_token('test-user-id', 'testuser')
print(token)
"
```

> **Key lifetime:** tokens currently expire after `JWT_EXPIRE_MINUTES` (default 10 080 min = 7 days).
> If a token is expired, simply log in again through the UI to receive a fresh one.
> To invalidate **all** existing tokens at once, change `JWT_SECRET` in `backend/.env` and restart the backend.

### Frontend Issues

- **npm install fails**: Ensure Node.js is installed and try clearing npm cache: `npm cache clean --force`
- **Port already in use**: Vite runs on port 5173 by default. If needed, you can specify a different port in `vite.config.js`
- **CORS errors**: The backend is configured to allow requests from `http://localhost:5173`. If you change the frontend port, update the CORS origins in `backend/app/main.py`

### Common Setup Problems

1. **Python virtual environment not activating**: On Windows, ensure you're using PowerShell or Command Prompt with execution policy allowing scripts
2. **Azure OpenAI access denied**: Check that your Azure subscription has access to OpenAI services and the deployment name matches
3. **Dependencies installation fails**: Try updating pip (`pip install --upgrade pip`) or use a different Python version

## Development

- Backend API documentation available at `http://localhost:8000/docs` (FastAPI auto-generated)
- MCP weather server endpoint available at `http://localhost:8001/mcp`
- Frontend hot-reload enabled during development
- The backend, frontend, and MCP server all support automatic restart on file changes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test both backend and frontend
5. Submit a pull request

## License

This project is for educational purposes as part of SE4471 coursework.
