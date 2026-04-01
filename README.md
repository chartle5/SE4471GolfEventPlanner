# SE4471 Golf Event Planner

A full-stack web application for planning and managing golf tournaments. The application features an AI-powered chat assistant for tournament planning and a responsive React frontend for visualization and management.

## Features

- **AI-Powered Planning**: Chat-based tournament planning using Azure OpenAI
- **RAG Proof of Concept**: Local document chunking with in-memory embeddings for lightweight retrieval
- **Tournament Management**: Create and manage golf tournament details
- **Knowledge Base**: Access tournament planning resources and best practices
- **Workflow Visualization**: View planning workflows and artifacts
- **Responsive Design**: Modern React interface with clean UI

## Tech Stack

- **Backend**: Python FastAPI with Azure OpenAI integration
- **Frontend**: React with Vite, React Router
- **AI**: Azure OpenAI GPT chat models plus a lightweight in-memory RAG layer with local embeddings

## Prerequisites

Before setting up the project, ensure you have the following installed:

- **Node.js** (version 16 or higher) - for the frontend
- **Python** (version 3.8 or higher) - for the backend
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

5. Create a `.env` file in the `backend` directory with your Azure OpenAI credentials:
   ```env
   AZURE_OPENAI_API_KEY=your_api_key_here
   AZURE_OPENAI_API_VERSION=2023-12-01-preview
   AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT=your-deployment-name
   RAG_LOCAL_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   LOG_LLM_PROMPTS=false
   ```

   Replace the placeholder values with your actual Azure OpenAI resource details.
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
│   │       └── rag.py       # Local chunking and in-memory retrieval
│   └── requirements.txt     # Python dependencies
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

## Troubleshooting

### Backend Issues

- **Module not found errors**: Ensure you're in the virtual environment and all dependencies are installed with `pip install -r requirements.txt`
- **Azure OpenAI errors**: Verify your `.env` file has correct Azure OpenAI credentials
- **Port already in use**: The backend runs on port 8000 by default. If it's occupied, you can specify a different port: `uvicorn app.main:app --reload --port 8001`

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
- Frontend hot-reload enabled during development
- Both servers support automatic restart on file changes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test both backend and frontend
5. Submit a pull request

## License

This project is for educational purposes as part of SE4471 coursework.
