# AI Analytics Platform V2

## Backend
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000

## Frontend (new terminal)
cd frontend
npm install
npm run dev

Open http://localhost:5173

Upload a real Excel/CSV dataset. The V2 dashboard automatically profiles columns and generates KPIs, trends, category charts, analyst signals and data profile metrics.
