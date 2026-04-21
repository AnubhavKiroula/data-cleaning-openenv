# Graph Report - D:\RL-PROJECT\data-cleaning-openenv  (2026-04-21)

## Corpus Check
- 68 files · ~184,306 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 975 nodes · 3290 edges · 44 communities detected
- Extraction: 33% EXTRACTED · 67% INFERRED · 0% AMBIGUOUS · INFERRED: 2211 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]

## God Nodes (most connected - your core abstractions)
1. `DQNAgent` - 159 edges
2. `Agent` - 138 edges
3. `AgentCoordinator` - 127 edges
4. `SyntheticDatasetGenerator` - 119 edges
5. `RewardShaper` - 113 edges
6. `DatasetConfig` - 103 edges
7. `DifficultyLevel` - 102 edges
8. `OutlierHandler` - 101 edges
9. `FillMissingAgent` - 100 edges
10. `DuplicateDetector` - 100 edges

## Surprising Connections (you probably didn't know these)
- `Agent` --uses--> `Deep Q-Network (DQN) model for data cleaning reinforcement learning.  This modul`  [INFERRED]
  D:\RL-PROJECT\data-cleaning-openenv\backend\ml\base_agent.py → D:\RL-PROJECT\data-cleaning-openenv\backend\ml\dqn_model.py
- `Agent` --uses--> `Deep Q-Network for approximating Q-values.          Architecture:     - Input la`  [INFERRED]
  D:\RL-PROJECT\data-cleaning-openenv\backend\ml\base_agent.py → D:\RL-PROJECT\data-cleaning-openenv\backend\ml\dqn_model.py
- `Agent` --uses--> `Initialize Q-network.                  Args:             state_dim: Dimension of`  [INFERRED]
  D:\RL-PROJECT\data-cleaning-openenv\backend\ml\base_agent.py → D:\RL-PROJECT\data-cleaning-openenv\backend\ml\dqn_model.py
- `Agent` --uses--> `Initialize network weights using Xavier initialization.`  [INFERRED]
  D:\RL-PROJECT\data-cleaning-openenv\backend\ml\base_agent.py → D:\RL-PROJECT\data-cleaning-openenv\backend\ml\dqn_model.py
- `Agent` --uses--> `Forward pass through network.                  Args:             state: Input st`  [INFERRED]
  D:\RL-PROJECT\data-cleaning-openenv\backend\ml\base_agent.py → D:\RL-PROJECT\data-cleaning-openenv\backend\ml\dqn_model.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (156): Benchmarking system for comparing DQN, Specialist Agents, and LLM approaches.  T, Initialize benchmark suite.                  Args:             device: Device fo, Load trained DQN model for benchmarking.                  Args:             mode, Benchmark a specific approach.                  Args:             approach: "DQN, Benchmark DQN approach., Benchmark Specialist Agents approach., Benchmark LLM approach (simulated since we don't have API access)., Determine expected correct action for a row.                  This is a simplifi (+148 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (112): ABC, Agent, AgentCoordinator, Agent Coordinator for multi-agent data cleaning system.  This module implement, Update agent performance tracking based on received reward.          Args:, Get performance statistics for all agents.          Returns:             Dict, Get recommendations from all capable agents.          Returns:             Li, Select the best agent from recommendations.          Args:             recomm (+104 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (74): CleaningService, clean_dataset(), Celery task definitions for asynchronous cleaning jobs., Process a queued cleaning job and persist progress/results., DatasetResponse, get_dataset(), get_dataset_metrics(), Dataset route handlers. (+66 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (63): AuditLog, JSONField, JSON field that works with both PostgreSQL and SQLite., Convert dict to JSON string., Convert JSON string back to dict., Stores row-level transformations performed during cleaning., Base, BaseSettings (+55 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (53): main(), Main entry point for running the server., reset(), ResetRequest, state(), step(), StepRequest, websocket_endpoint() (+45 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (16): ApiClient, applyAction(), getJobs(), getMetrics(), skipRow(), startJob(), uploadDataset(), fetchDashboardData() (+8 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (15): Sample based on priorities.                  Args:             batch_size: Numbe, Update priorities based on TD-errors.                  Args:             indices, Sample a batch of transitions from the buffer.                  Args:, Sample a batch and convert to tensors for training.                  Args:, get_job_audit_log(), Generate clean base dataset.                  Args:             num_rows: Number, Generate realistic salary based on department., Inject missing values into dataset.                  Args:             df: Clean (+7 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (13): Calculate confidence in fill value., Select action to handle duplicates., Calculate similarity with previous rows., Calculate similarity between two rows., Select action to handle outliers., Check if value is an outlier using IQR method., Calculate median replacement value., Calculate confidence in outlier detection. (+5 more)

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (7): BenchmarkResult, ComparisonSummary, DataCleaningBenchmark, main(), Create training episodes from synthetic data.                  Args:, Detect issues specific to this row.                  Args:             row: Row, Get predefined configuration for difficulty level.                  Args:

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (19): configure_logging(), health_check(), JsonFormatter, lifespan(), metrics(), _probe_database_engine(), FastAPI application entrypoint., Expose Prometheus metrics in text format. (+11 more)

### Community 10 - "Community 10"
Cohesion: 0.25
Nodes (7): Database tests for backend initialization., Engine can produce a SQLAlchemy connection object., ORM metadata contains required tables., At minimum ensure table metadata is bound and creatable., test_crud_operations(), test_database_connection(), test_model_creation()

### Community 11 - "Community 11"
Cohesion: 0.33
Nodes (3): Initialize DQN agent.                  Args:             state_dim: Dimension of, Initialize Q-network.                  Args:             state_dim: Dimension of, Initialize network weights using Xavier initialization.

### Community 12 - "Community 12"
Cohesion: 0.33
Nodes (0): 

### Community 13 - "Community 13"
Cohesion: 0.33
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 0.4
Nodes (0): 

### Community 15 - "Community 15"
Cohesion: 0.4
Nodes (0): 

### Community 16 - "Community 16"
Cohesion: 0.5
Nodes (2): Forward pass through network.                  Args:             state: Input st, Get Q-values as numpy array.                  Args:             state: Input sta

### Community 17 - "Community 17"
Cohesion: 0.5
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 0.5
Nodes (0): 

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Celery worker startup entrypoint.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Celery application configuration.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Get agent's confidence in last action.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Reward Shaper for multi-agent data cleaning system.  This module implements so

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Stores row-level transformations performed during cleaning.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Supported cleaning job execution modes.

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Tracks each data cleaning task lifecycle.

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Lifecycle states of an uploaded dataset.

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Stores uploaded dataset metadata.

## Knowledge Gaps
- **97 isolated node(s):** `Emit [START] line at episode begin.`, `Emit [STEP] line after each env.step() with exact format.`, `Emit [END] line after episode completes. Always called even on exception.`, `Ask the LLM what cleaning action to take.`, `Run one full episode for a task and return score in [0, 1] range.` (+92 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 19`** (2 nodes): `worker.py`, `Celery worker startup entrypoint.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `Celery application configuration.`, `celery_config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (2 nodes): `.get_confidence()`, `Get agent's confidence in last action.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (2 nodes): `reward_shaper.py`, `Reward Shaper for multi-agent data cleaning system.  This module implements so`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (2 nodes): `App.tsx`, `main.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (2 nodes): `DataQualityChart.tsx`, `DataQualityChart()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (2 nodes): `MetricsOverview.tsx`, `formatDataSize()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `verify_frontend.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `vite.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `ActionPanel.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Navigation.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Sidebar.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `index.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Stores row-level transformations performed during cleaning.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Supported cleaning job execution modes.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Tracks each data cleaning task lifecycle.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Lifecycle states of an uploaded dataset.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Stores uploaded dataset metadata.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentCoordinator` connect `Community 1` to `Community 8`, `Community 0`, `Community 2`, `Community 3`?**
  _High betweenness centrality (0.160) - this node is a cross-community bridge._
- **Why does `DQNAgent` connect `Community 0` to `Community 1`, `Community 2`, `Community 8`, `Community 11`, `Community 21`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Why does `Agent` connect `Community 1` to `Community 0`, `Community 2`, `Community 7`, `Community 11`, `Community 16`, `Community 21`?**
  _High betweenness centrality (0.111) - this node is a cross-community bridge._
- **Are the 141 inferred relationships involving `DQNAgent` (e.g. with `Agent` and `AgentFactory`) actually correct?**
  _`DQNAgent` has 141 INFERRED edges - model-reasoned connections that need verification._
- **Are the 130 inferred relationships involving `Agent` (e.g. with `AgentCoordinator` and `Agent Coordinator for multi-agent data cleaning system.  This module implement`) actually correct?**
  _`Agent` has 130 INFERRED edges - model-reasoned connections that need verification._
- **Are the 113 inferred relationships involving `AgentCoordinator` (e.g. with `Agent` and `FillMissingAgent`) actually correct?**
  _`AgentCoordinator` has 113 INFERRED edges - model-reasoned connections that need verification._
- **Are the 102 inferred relationships involving `SyntheticDatasetGenerator` (e.g. with `BenchmarkResult` and `ComparisonSummary`) actually correct?**
  _`SyntheticDatasetGenerator` has 102 INFERRED edges - model-reasoned connections that need verification._