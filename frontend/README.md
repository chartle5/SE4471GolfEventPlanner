# Golf Tournament Planner — Frontend

This is the React frontend for the Golf Tournament Planner application. It provides a user interface for tournament planning, knowledge base access, and workflow visualization. The frontend communicates with a FastAPI backend that includes AI-powered chat assistance.

## Features

- Responsive React app with routes for Dashboard, Plan Tournament, Knowledge Base, Workflow, Event Memory, Artifacts, and Architecture
- Mock data under `src/data` for documents, tournament state, workflow steps, and artifacts
- Clean component structure under `src/components`
- Integration with backend API for AI chat functionality

## Setup

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Run dev server:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:5173` and expects the backend to be running on `http://localhost:8000`.

## Notes

- Requires the backend server to be running for full functionality
- API calls are made to the backend for chat and tournament planning
- All data is managed through the backend API
