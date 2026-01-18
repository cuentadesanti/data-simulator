 Data Simulator - Plan de Implementación                                                                                                                             
                                                                                                                                                                     
 Resumen                                                                                                                                                             
                                                                                                                                                                     
 App para generar datos sintéticos desde un DAG probabilístico visual. El usuario construye el modelo con React Flow, lo exporta a JSON, y el backend genera         
 datasets via forward sampling.                                                                                                                                      
                                                                                                                                                                     
 ---                                                                                                                                                                 
 Tech Stack                                                                                                                                                          
                                                                                                                                                                     
 - Frontend: React 18 + TypeScript + React Flow + Zustand + TailwindCSS                                                                                              
 - Backend: Python 3.11+ + FastAPI + Pydantic + NumPy/SciPy + Pandas + PyArrow                                                                                       
 - Database: SQLite (dev) / PostgreSQL (prod) + SQLAlchemy                                                                                                           
                                                                                                                                                                     
 ---                                                                                                                                                                 
 Estructura del Proyecto                                                                                                                                             
                                                                                                                                                                     
 data-simulator/                                                                                                                                                     
 ├── backend/                                                                                                                                                        
 │   ├── app/                                                                                                                                                        
 │   │   ├── main.py                 # FastAPI app entry                                                                                                             
 │   │   ├── api/                                                                                                                                                    
 │   │   │   ├── routes/                                                                                                                                             
 │   │   │   │   ├── dag.py          # POST /validate, POST /generate                                                                                                
 │   │   │   │   └── distributions.py # GET /distributions                                                                                                           
 │   │   │   └── deps.py                                                                                                                                             
 │   │   ├── core/                                                                                                                                                   
 │   │   │   ├── config.py                                                                                                                                           
 │   │   │   └── exceptions.py                                                                                                                                       
 │   │   ├── models/                                                                                                                                                 
 │   │   │   ├── dag.py              # DAG, Node, Edge schemas                                                                                                       
 │   │   │   ├── distribution.py     # Distribution configs                                                                                                          
 │   │   │   └── generation.py       # Request/Response models                                                                                                       
 │   │   ├── services/                                                                                                                                               
 │   │   │   ├── validator.py        # DAG validation, cycle detection                                                                                               
 │   │   │   ├── sampler.py          # Forward sampling engine                                                                                                       
 │   │   │   ├── formula_parser.py   # Safe expression evaluator                                                                                                     
 │   │   │   ├── scope_manager.py    # Hierarchy/scope handling                                                                                                      
 │   │   │   └── distribution_registry.py                                                                                                                            
 │   │   ├── db/                                                                                                                                                     
 │   │   │   ├── database.py         # SQLAlchemy engine/session                                                                                                     
 │   │   │   ├── models.py           # ORM models (Project, DAGVersion)                                                                                              
 │   │   │   └── crud.py             # CRUD operations                                                                                                               
 │   │   └── utils/                                                                                                                                                  
 │   │       └── topological_sort.py                                                                                                                                 
 │   ├── tests/                                                                                                                                                      
 │   ├── requirements.txt                                                                                                                                            
 │   └── pyproject.toml                                                                                                                                              
 ├── frontend/                                                                                                                                                       
 │   ├── src/                                                                                                                                                        
 │   │   ├── components/                                                                                                                                             
 │   │   │   ├── Canvas/                                                                                                                                             
 │   │   │   │   ├── DAGCanvas.tsx       # React Flow container                                                                                                      
 │   │   │   │   ├── CustomNode.tsx      # Variable node component                                                                                                   
 │   │   │   │   └── CustomEdge.tsx                                                                                                                                  
 │   │   │   ├── Panel/                                                                                                                                              
 │   │   │   │   ├── NodeEditor.tsx      # Side panel for node config                                                                                                
 │   │   │   │   ├── DistributionForm.tsx                                                                                                                            
 │   │   │   │   ├── FormulaEditor.tsx                                                                                                                               
 │   │   │   │   └── ScopeSelector.tsx                                                                                                                               
 │   │   │   ├── Toolbar/                                                                                                                                            
 │   │   │   │   ├── Toolbar.tsx                                                                                                                                     
 │   │   │   │   └── ExportButton.tsx                                                                                                                                
 │   │   │   ├── Preview/                                                                                                                                            
 │   │   │   │   ├── DataPreview.tsx     # Sample table                                                                                                              
 │   │   │   │   └── ValidationPanel.tsx # Checks & stats                                                                                                            
 │   │   │   └── common/                                                                                                                                             
 │   │   ├── stores/                                                                                                                                                 
 │   │   │   ├── dagStore.ts         # Zustand store for DAG state                                                                                                   
 │   │   │   └── uiStore.ts                                                                                                                                          
 │   │   ├── hooks/                                                                                                                                                  
 │   │   │   ├── useValidation.ts                                                                                                                                    
 │   │   │   └── useGeneration.ts                                                                                                                                    
 │   │   ├── types/                                                                                                                                                  
 │   │   │   ├── dag.ts              # Node, Edge, DAG types                                                                                                         
 │   │   │   └── distribution.ts                                                                                                                                     
 │   │   ├── services/                                                                                                                                               
 │   │   │   └── api.ts              # Backend API client                                                                                                            
 │   │   ├── utils/                                                                                                                                                  
 │   │   │   └── validation.ts       # Client-side validation                                                                                                        
 │   │   ├── App.tsx                                                                                                                                                 
 │   │   └── main.tsx                                                                                                                                                
 │   ├── package.json                                                                                                                                                
 │   └── vite.config.ts                                                                                                                                              
 └── README.md                                                                                                                                                       
                                                                                                                                                                     
 ---                                                                                                                                                                 
 Modelos de Datos                                                                                                                                                    
                                                                                                                                                                     
 Backend (Pydantic)                                                                                                                                                  
                                                                                                                                                                     
 # models/dag.py                                                                                                                                                     
                                                                                                                                                                     
 # ═══════════════════════════════════════════════════════════════                                                                                                   
 # ParamValue: tipos explícitos para evitar heurísticas                                                                                                              
 # ═══════════════════════════════════════════════════════════════                                                                                                   
                                                                                                                                                                     
 class LookupValue(BaseModel):                                                                                                                                       
     """Busca valor en context[lookup][row[key]]"""                                                                                                                  
     lookup: str      # nombre de la tabla en context                                                                                                                
     key: str         # nodo del cual tomar la categoría                                                                                                             
     default: float = 0                                                                                                                                              
                                                                                                                                                                     
 class MappingValue(BaseModel):                                                                                                                                      
     """Mapping inline (pequeño, no necesita context)"""                                                                                                             
     mapping: dict[str, float]                                                                                                                                       
     key: str         # nodo del cual tomar la categoría                                                                                                             
     default: float = 0                                                                                                                                              
                                                                                                                                                                     
 # ParamValue estricto - sin ambigüedades                                                                                                                            
 ParamValue = Union[                                                                                                                                                 
     float,           # literal numérico: 2000                                                                                                                       
     int,             # literal entero: 100                                                                                                                          
     str,             # expresión: "0.15 * salario_padres + base[zona]"                                                                                              
     LookupValue,     # lookup en context                                                                                                                            
     MappingValue     # mapping inline                                                                                                                               
 ]                                                                                                                                                                   
                                                                                                                                                                     
 # ═══════════════════════════════════════════════════════════════                                                                                                   
 # Distribuciones y Nodos                                                                                                                                            
 # ═══════════════════════════════════════════════════════════════                                                                                                   
                                                                                                                                                                     
 class DistributionConfig(BaseModel):                                                                                                                                
     type: str  # "normal", "categorical", "scipy", "mixture"                                                                                                        
     params: dict[str, ParamValue]                                                                                                                                   
                                                                                                                                                                     
 class NodeConfig(BaseModel):                                                                                                                                        
     id: str                                                                                                                                                         
     name: str                                                                                                                                                       
     kind: Literal["stochastic", "deterministic"]                                                                                                                    
     dtype: Optional[Literal["float", "int", "category", "bool", "string"]] = None                                                                                   
     scope: Literal["global", "group", "row"]                                                                                                                        
     group_by: Optional[str]  # solo para scope="group"                                                                                                              
                                                                                                                                                                     
     # MECE: solo uno según kind                                                                                                                                     
     distribution: Optional[DistributionConfig]  # si kind="stochastic"                                                                                              
     formula: Optional[str]  # si kind="deterministic"                                                                                                               
                                                                                                                                                                     
 class DAGEdge(BaseModel):                                                                                                                                           
     source: str                                                                                                                                                     
     target: str                                                                                                                                                     
                                                                                                                                                                     
 # ═══════════════════════════════════════════════════════════════                                                                                                   
 # Context flexible                                                                                                                                                  
 # ═══════════════════════════════════════════════════════════════                                                                                                   
                                                                                                                                                                     
 # context: dict[str, Any] - permite:                                                                                                                                
 # - Mappings categóricos: {"base": {"norte": 8000, "sur": 12000}}                                                                                                   
 # - Constantes: {"PI": 3.14159, "TAX_RATE": 0.16}                                                                                                                   
 # - Mini-tablas: {"percentiles": {"p10": 1000, "p50": 5000, "p90": 15000}}                                                                                          
                                                                                                                                                                     
 class DAGDefinition(BaseModel):                                                                                                                                     
     nodes: list[NodeConfig]                                                                                                                                         
     edges: list[DAGEdge]                                                                                                                                            
     context: dict[str, Any] = {}  # flexible, validado por "allowed shapes"                                                                                         
     metadata: GenerationMetadata                                                                                                                                    
                                                                                                                                                                     
 # ═══════════════════════════════════════════════════════════════                                                                                                   
 # Metadata de generación                                                                                                                                            
 # ═══════════════════════════════════════════════════════════════                                                                                                   
                                                                                                                                                                     
 class GenerationMetadata(BaseModel):                                                                                                                                
     sample_size: int                                                                                                                                                
     seed: Optional[int] = None                                                                                                                                      
     preview_rows: int = 500                                                                                                                                         
                                                                                                                                                                     
 class GenerationResult(BaseModel):                                                                                                                                  
     """Resultado de /generate - incluir desde día 1 aunque MVP sea sync"""                                                                                          
     job_id: Optional[str] = None  # None si sync                                                                                                                    
     status: Literal["completed", "pending", "running", "failed"]                                                                                                    
     # Metadata del resultado                                                                                                                                        
     rows: int                                                                                                                                                       
     columns: list[str]                                                                                                                                              
     seed: int                                                                                                                                                       
     format: Literal["csv", "parquet", "json"]                                                                                                                       
     size_bytes: Optional[int] = None                                                                                                                                
     schema_version: str = "1.0"                                                                                                                                     
     warnings: list[str] = []                                                                                                                                        
     download_url: Optional[str] = None                                                                                                                              
                                                                                                                                                                     
 Ejemplo de nodo con params dinámicos                                                                                                                                
                                                                                                                                                                     
 nodes:                                                                                                                                                              
   # Zona categórica (root node)                                                                                                                                     
   - id: zona                                                                                                                                                        
     name: Zona                                                                                                                                                      
     kind: stochastic                                                                                                                                                
     dtype: category                                                                                                                                                 
     scope: row                                                                                                                                                      
     distribution:                                                                                                                                                   
       type: categorical                                                                                                                                             
       params:                                                                                                                                                       
         categories: ["norte", "sur", "centro"]                                                                                                                      
         probs: [0.3, 0.4, 0.3]                                                                                                                                      
                                                                                                                                                                     
   # Ingreso: mu depende de zona via lookup                                                                                                                          
   - id: ingreso                                                                                                                                                     
     name: Ingreso                                                                                                                                                   
     kind: stochastic                                                                                                                                                
     dtype: float                                                                                                                                                    
     scope: row                                                                                                                                                      
     distribution:                                                                                                                                                   
       type: normal                                                                                                                                                  
       params:                                                                                                                                                       
         mu:                                                                                                                                                         
           lookup: "base_salario"   # busca en context                                                                                                               
           key: "zona"              # usa valor de nodo zona                                                                                                         
           default: 10000                                                                                                                                            
         sigma: 2000  # literal                                                                                                                                      
                                                                                                                                                                     
   # Ingreso neto: fórmula determinista                                                                                                                              
   - id: ingreso_neto                                                                                                                                                
     name: Ingreso Neto                                                                                                                                              
     kind: deterministic                                                                                                                                             
     dtype: float                                                                                                                                                    
     scope: row                                                                                                                                                      
     formula: "ingreso * (1 - TAX_RATE)"  # usa constante de context                                                                                                 
                                                                                                                                                                     
 context:                                                                                                                                                            
   base_salario:           # mapping categórico                                                                                                                      
     norte: 8000                                                                                                                                                     
     sur: 12000                                                                                                                                                      
     centro: 10000                                                                                                                                                   
   TAX_RATE: 0.16          # constante                                                                                                                               
   PI: 3.14159             # otra constante                                                                                                                          
                                                                                                                                                                     
 Frontend (TypeScript)                                                                                                                                               
                                                                                                                                                                     
 // types/dag.ts                                                                                                                                                     
                                                                                                                                                                     
 // ParamValue explícito                                                                                                                                             
 interface LookupValue {                                                                                                                                             
   lookup: string;                                                                                                                                                   
   key: string;                                                                                                                                                      
   default?: number;                                                                                                                                                 
 }                                                                                                                                                                   
                                                                                                                                                                     
 interface MappingValue {                                                                                                                                            
   mapping: Record<string, number>;                                                                                                                                  
   key: string;                                                                                                                                                      
   default?: number;                                                                                                                                                 
 }                                                                                                                                                                   
                                                                                                                                                                     
 type ParamValue = number | string | LookupValue | MappingValue;                                                                                                     
                                                                                                                                                                     
 interface DistributionConfig {                                                                                                                                      
   type: string;                                                                                                                                                     
   params: Record<string, ParamValue>;                                                                                                                               
 }                                                                                                                                                                   
                                                                                                                                                                     
 type NodeDtype = 'float' | 'int' | 'category' | 'bool' | 'string';                                                                                                  
                                                                                                                                                                     
 interface DAGNode {                                                                                                                                                 
   id: string;                                                                                                                                                       
   name: string;                                                                                                                                                     
   kind: 'stochastic' | 'deterministic';                                                                                                                             
   dtype?: NodeDtype;                                                                                                                                                
   scope: 'global' | 'group' | 'row';                                                                                                                                
   groupBy?: string;                                                                                                                                                 
   distribution?: DistributionConfig;                                                                                                                                
   formula?: string;                                                                                                                                                 
   position: { x: number; y: number };                                                                                                                               
 }                                                                                                                                                                   
                                                                                                                                                                     
 interface DAGEdge {                                                                                                                                                 
   id: string;                                                                                                                                                       
   source: string;                                                                                                                                                   
   target: string;                                                                                                                                                   
 }                                                                                                                                                                   
                                                                                                                                                                     
 // Context flexible: mappings, constantes, mini-tablas                                                                                                              
 type DAGContext = Record<string, unknown>;                                                                                                                          
                                                                                                                                                                     
 interface GenerationResult {                                                                                                                                        
   jobId?: string;                                                                                                                                                   
   status: 'completed' | 'pending' | 'running' | 'failed';                                                                                                           
   rows: number;                                                                                                                                                     
   columns: string[];                                                                                                                                                
   seed: number;                                                                                                                                                     
   format: 'csv' | 'parquet' | 'json';                                                                                                                               
   sizeBytes?: number;                                                                                                                                               
   schemaVersion: string;                                                                                                                                            
   warnings: string[];                                                                                                                                               
   downloadUrl?: string;                                                                                                                                             
 }                                                                                                                                                                   
                                                                                                                                                                     
 ---                                                                                                                                                                 
 API Endpoints                                                                                                                                                       
                                                                                                                                                                     
 | Method | Endpoint           | Descripción                                                         |                                                               
 |--------|--------------------|---------------------------------------------------------------------|                                                               
 | GET    | /api/distributions | Lista distribuciones disponibles con sus params                     |                                                               
 | POST   | /api/dag/validate  | Valida DAG (ciclos, params, dependencias, kind MECE)                |                                                               
 | POST   | /api/dag/preview   | Genera preview_rows muestras (sync, siempre ~500 rows)              |                                                               
 | POST   | /api/dag/generate  | Genera dataset. Si rows > threshold: retorna {job_id} (async-ready) |                                                               
 | GET    | /api/jobs/{job_id} | Estado del job (pending/running/done/failed) + download URL         |                                                               
 | GET    | /api/projects      | Lista proyectos guardados                                           |                                                               
 | POST   | /api/projects      | Crea nuevo proyecto con DAG                                         |                                                               
 | GET    | /api/projects/{id} | Obtiene proyecto con su DAG                                         |                                                               
 | PUT    | /api/projects/{id} | Actualiza proyecto/DAG                                              |                                                               
 | DELETE | /api/projects/{id} | Elimina proyecto                                                    |                                                               
                                                                                                                                                                     
 Nota: El contrato de /generate con job_id queda listo aunque MVP sea sync.                                                                                          
                                                                                                                                                                     
 ---                                                                                                                                                                 
 Semántica de Scopes                                                                                                                                                 
                                                                                                                                                                     
 | Scope  | Tamaño generado | Comportamiento                                    |                                                                                    
 |--------|-----------------|---------------------------------------------------|                                                                                    
 | global | 1               | Se samplea 1 valor, broadcast a todas las N filas |                                                                                    
 | row    | N               | Se samplea 1 valor por fila (default)             |                                                                                    
 | group  | #grupos únicos  | Se samplea 1 valor por grupo, luego map a filas   |                                                                                    
                                                                                                                                                                     
 Reglas de group_by:                                                                                                                                                 
 - Solo aplica cuando scope="group"                                                                                                                                  
 - Debe referenciar un solo nodo categórico (simplifica implementación)                                                                                              
 - El nodo referenciado debe ser un ancestro en el DAG                                                                                                               
                                                                                                                                                                     
 Semántica según scope del nodo group_by:                                                                                                                            
 - Si group_by es un nodo row (categórico): los grupos dependen de las N filas generadas                                                                             
   - Ejemplo: zona con scope=row → puede haber 300 "norte", 400 "sur", 300 "centro"                                                                                  
   - El nodo con group_by: "zona" genera 3 valores (uno por categoría única)                                                                                         
 - Si group_by es un nodo global: solo hay 1 grupo (todos comparten el mismo valor)                                                                                  
   - Raro pero válido — equivale funcionalmente a scope=global                                                                                                       
                                                                                                                                                                     
 Ejemplo:                                                                                                                                                            
 zona (row, categorical) → genera ["norte", "sur", "norte", "sur", "centro", ...]                                                                                    
 efecto_zona (group, group_by: zona) → genera {norte: 0.5, sur: 0.3, centro: 0.7}                                                                                    
 → cada fila hereda el valor según su zona                                                                                                                           
                                                                                                                                                                     
 Orden de resolución:                                                                                                                                                
 1. Validar DAG (acíclico)                                                                                                                                           
 2. Topological sort                                                                                                                                                 
 3. Para cada nodo en orden:                                                                                                                                         
   - Si global: generar 1, broadcast                                                                                                                                 
   - Si group: agrupar por group_by, generar por grupo, map                                                                                                          
   - Si row: generar N valores                                                                                                                                       
                                                                                                                                                                     
 ---                                                                                                                                                                 
 Fases de Implementación                                                                                                                                             
                                                                                                                                                                     
 Fase 1: Foundation (Backend Core) - MVP CRÍTICO                                                                                                                     
                                                                                                                                                                     
 1. Setup proyecto Python + FastAPI + estructura de carpetas                                                                                                         
 2. Modelos Pydantic con nuevo esquema (kind MECE, ParamValue dinámico)                                                                                              
 3. Validador de DAG:                                                                                                                                                
   - Detección de ciclos (DFS)                                                                                                                                       
   - Validación MECE: stochastic tiene distribution, deterministic tiene formula                                                                                     
   - Validación de group_by → debe ser ancestro categórico                                                                                                           
 4. Topological sort                                                                                                                                                 
 5. Distribution Registry con factory pattern (Normal, Uniform, Categorical, Bernoulli)                                                                              
 6. Endpoint /validate + /preview (sync, 500 rows)                                                                                                                   
 7. Tests unitarios para validación                                                                                                                                  
                                                                                                                                                                     
 Fase 2: Params Dinámicos - MVP CRÍTICO                                                                                                                              
                                                                                                                                                                     
 1. Param Resolver: motor que evalúa cada ParamValue                                                                                                                 
   - Literal → usa directo                                                                                                                                           
   - String (expresión) → parsea con simpleeval, inyecta padres + context                                                                                            
   - Dict (mapping) → lookup por valor del nodo referenciado                                                                                                         
 2. Integración con sampler: resolver.resolve(params, row_data, context) → dict[str, float]                                                                          
 3. Tests: expresiones simples, lookups, referencias a padres                                                                                                        
 4. El sampler siempre hace: resolver params → samplear distribución                                                                                                 
                                                                                                                                                                     
 Fase 3: Foundation (Frontend Core)                                                                                                                                  
                                                                                                                                                                     
 1. Setup React + Vite + TypeScript + TailwindCSS                                                                                                                    
 2. Integrar React Flow con canvas básico                                                                                                                            
 3. Custom node component para variables (mostrar kind + scope)                                                                                                      
 4. Conexiones (edges) entre nodos                                                                                                                                   
 5. Zustand store para estado del DAG                                                                                                                                
 6. Panel lateral: selector kind, scope, distribution/formula según kind                                                                                             
 7. Export DAG a JSON con context                                                                                                                                    
                                                                                                                                                                     
 Fase 4: Scopes (global/row primero) - MVP                                                                                                                           
                                                                                                                                                                     
 1. Scope manager en backend                                                                                                                                         
 2. global: generar 1 valor, broadcast a N filas                                                                                                                     
 3. row: generar N valores (default, ya funciona)                                                                                                                    
 4. UI: Selector de scope en panel lateral                                                                                                                           
 5. Tests de broadcast correcto                                                                                                                                      
                                                                                                                                                                     
 Fase 5: Scope Group + Persistencia                                                                                                                                  
                                                                                                                                                                     
 1. group: implementar agrupación por nodo categórico                                                                                                                
 2. Validación: group_by debe ser ancestro categórico                                                                                                                
 3. Setup SQLAlchemy + Alembic (migraciones)                                                                                                                         
 4. Modelos ORM: Project, DAGVersion                                                                                                                                 
 5. CRUD endpoints + Frontend lista de proyectos                                                                                                                     
                                                                                                                                                                     
 Fase 6: Distribuciones Flexibles                                                                                                                                    
                                                                                                                                                                     
 1. Integración scipy.stats (cualquier distribución por nombre)                                                                                                      
 2. Distribuciones intermedias (Poisson, Exponential, Beta, Gamma)                                                                                                   
 3. Validación de parámetros por tipo de distribución    