# ParkSense AI — Local Setup & Run Instructions

This guide will help the judging panel and technical reviewers build and run the ParkSense AI prototype locally on their machines. We have fully dockerized the application for seamless, one-click deployment.

## Option 1: Docker Deployment (Recommended)

The entire architecture (PostgreSQL, FastAPI Backend, React Frontend) has been containerized. This is the fastest way to evaluate the project.

### Prerequisites
* Docker & Docker Compose installed and running.

### Run Instructions
1. Open a terminal in the root directory (where `docker-compose.yml` is located).
2. Run the following command:
   ```bash
   docker compose up -d
   ```
3. Docker will automatically pull our custom, pre-seeded PostgreSQL image (`dyuti01/parksense-db:latest`) containing all ~298,445 processed violations and ML hotspots, and then build the Backend and Frontend.
4. Once the containers are running:
   * **Frontend Dashboard:** Available at [http://localhost:3000](http://localhost:3000)
   * **Backend API Docs:** Available at [http://localhost:8000/docs](http://localhost:8000/docs)
5. *Note: If you encounter port conflicts, ensure ports `3000`, `8000`, and `5433` are free on your host machine.*

---

## Option 2: Manual Local Setup

If you prefer to run the services natively on your machine without Docker.

### Prerequisites
1. **Python 3.10+**: For the FastAPI backend and ML spatial engine.
2. **Node.js 18+**: For the React + Vite frontend dashboard.
3. **PostgreSQL 17**: Running locally. **No PostGIS extension is required.**

### 1. Database Setup
1. Ensure your local PostgreSQL server is running.
2. Create an empty database named `parksense`.
3. You do not need to run any initialization scripts; the FastAPI backend uses SQLAlchemy to automatically generate the required tables on boot.

### 2. Backend Setup
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment (`python -m venv venv`).
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `backend/` directory with your local credentials:
   ```env
   DATABASE_URL=postgresql+asyncpg://<username>:<password>@localhost:5432/parksense
   DATABASE_URL_SYNC=postgresql+psycopg2://<username>:<password>@localhost:5432/parksense
   ```
5. Start the backend:
   ```bash
   uvicorn app.main:app --reload
   ```

### 3. Frontend Setup
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite server:
   ```bash
   npm run dev
   ```
   *(The native dev server usually defaults to `http://localhost:5173`)*

---

## Usage Walkthrough

If you ran the system using **Option 1 (Docker)**, the database is already fully seeded with ~298,455 records and pre-calculated ML hotspots, for demonstration purpose!
> Do not need to upload the given dataset CSV. For demonstration purpose, already the data is present in the `database image`.

1. Open the React Dashboard (`http://localhost:3000`).
2. Navigate straight to the **Geospatial Map** to visually inspect the AI-detected parking hotspots.
3. Check the **Temporal Heatmaps** to analyze peak violation times.
4. View the **Dispatch Priority** tab to see the ranked list of critical choke-points automatically sorted by their Congestion Impact Score (CIS).

*Note: If you ran the system via Option 2 (Manual Setup with an empty database), you will first need to navigate to the Data Ingestion tab and upload the raw Hackathon CSV dataset to trigger the ML pipeline.*
