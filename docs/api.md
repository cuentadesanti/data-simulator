# API Contracts + Error Semantics

The Data Simulator backend provides a RESTful API built with FastAPI.

## Global Conventions

- **Content-Type**: `application/json`
- **Variable Naming**: `snake_case` (matching Backend Pydantic models)
- **Base URL**: `/api`

## Core Endpoints

### 1. DAG Operations (`/api/dag`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/validate` | Validates a DAG for cycles, formula syntax, and distribution params. |
| POST | `/preview` | Generates a small sample (default 500 rows) for real-time feedback. |
| POST | `/generate` | Triggers a full data generation run (returns metadata + file path/URL). |

### 2. Distributions (`/api/distributions`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Returns the list of 14+ primary supported distributions with their metadata. |
| GET | `/search` | Search via `?q=` query parameter through all 100+ SciPy-supported distributions. |

### 3. Projects (`/api/projects`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List all projects. |
| POST | `/` | Create a new project. |
| GET | `/{id}` | Get project details including the full DAG definition. |
| PUT | `/{id}` | Update project metadata or DAG. |
| DELETE | `/{id}` | Delete project. |

## Error Semantics

The API uses standard HTTP status codes combined with a structured JSON error response:

```json
{
  "message": "Human-readable error description",
  "node_id": "optional_node_id_that_caused_error",
  "details": {
    "error_type": "ValidationError | SampleError | DistributionError",
    "specific_info": "..."
  }
}
```

### Status Codes

- **400 Bad Request**:
  - `ValidationError`: DAG is invalid (cycle, missing dependencies, invalid formula).
  - `DistributionError`: Mandatory parameters for a distribution are missing.
- **500 Internal Server Error**:
  - `SampleError`: Something went wrong during the numerical generation process (e.g., overflow).
- **404 Not Found**:
  - Requested project or resource doesn't exist.

---
> [!IMPORTANT]
> - `formula`: (Optional) Python expression for deterministic value generation.
  - Can reference other nodes by **Node ID** OR **snake_cased name**.
  - Example: `base_salary * (1 + inflation)` or `n0 * 2`.
