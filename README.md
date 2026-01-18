# Data Simulator

A visual tool for generating synthetic datasets from probabilistic DAG (Directed Acyclic Graph) models. Build your data model visually with React Flow, configure probability distributions, and generate datasets via forward sampling.

## Features

- **Visual DAG Editor**: Build probabilistic models using an intuitive drag-and-drop interface
- **14+ Built-in Distributions**: Normal, Uniform, Categorical, Bernoulli, Poisson, Exponential, Beta, Gamma, Log-Normal, Binomial, Triangular, Weibull, Chi-Square, Student's t
- **100+ SciPy Distributions**: Search and use any scipy.stats distribution
- **Dynamic Parameters**: Distribution parameters can be literals, formulas referencing other nodes, or lookups from context tables
- **Scopes**: Support for global, group, and row-level variable generation
- **Project Management**: Save projects with version history
- **Multiple Export Formats**: CSV, Parquet, JSON
- **Real-time Validation**: DAG validation with cycle detection and dependency checking

## Tech Stack

### Backend
- Python 3.11+
- FastAPI
- Pydantic v2
- NumPy / SciPy
- Pandas / PyArrow
- SQLAlchemy + Alembic

### Frontend
- React 19 + TypeScript
- React Flow (DAG visualization)
- Zustand (state management)
- TailwindCSS v4
- Vite

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 20+** (npm or pnpm)
- **uv** (Recommended Python package manager) - `pip install uv`
- **PostgreSQL** (or Supabase instance)

### Backend Setup

1. **Environment Configuration**:
   Create a `backend/.env` file from the template:
   ```bash
   cd backend
   cp .env.example .env
   ```
   Modify `DS_DATABASE_URL` with your Supabase or local Postgres connection string.

2. **Dependency Installation**:
   ```bash
   uv sync
   ```

3. **Database Migrations**:
   ```bash
   uv run alembic upgrade head
   ```

4. **Run Server**:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`.

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Environment Configuration**:
   Create `frontend/.env`:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```

3. **Run development server**:
   ```bash
   npm run dev
   ```

The app will be available at `http://localhost:5173`.

## Project Structure

```
data-simulator/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # API endpoints
│   │   ├── core/             # Config and exceptions
│   │   ├── models/           # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   └── db/               # Database models
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── stores/           # Zustand stores
│   │   ├── services/         # API client
│   │   └── types/            # TypeScript types
│   └── ...
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/distributions` | List common distributions |
| GET | `/api/distributions/search?q=...` | Search scipy distributions |
| POST | `/api/dag/validate` | Validate DAG definition |
| POST | `/api/dag/preview` | Generate preview (500 rows) |
| POST | `/api/dag/generate` | Generate full dataset |
| GET | `/api/projects` | List projects |
| POST | `/api/projects` | Create project |
| GET | `/api/projects/{id}` | Get project with DAG |
| PUT | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project |

## Development

### Backend

```bash
cd backend

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint code
uv run ruff check . --fix

# Type check
uv run mypy app
```

### Frontend

```bash
cd frontend

# Run tests
npm test

# Lint code
npm run lint

# Format code
npm run format

# Build for production
npm run build
```

## Example DAG Definition

```yaml
nodes:
  - id: region
    name: Region
    kind: stochastic
    dtype: category
    scope: row
    distribution:
      type: categorical
      params:
        categories: ["north", "south", "east", "west"]
        probs: [0.25, 0.25, 0.25, 0.25]

  - id: income
    name: Income
    kind: stochastic
    dtype: float
    scope: row
    distribution:
      type: lognormal
      params:
        mean: 10.5
        sigma: 0.8

  - id: tax
    name: Tax
    kind: deterministic
    dtype: float
    scope: row
    formula: "income * 0.22"

edges:
  - source: income
    target: tax

context:
  tax_rate: 0.22

metadata:
  sample_size: 10000
  seed: 42
```

## License

MIT
