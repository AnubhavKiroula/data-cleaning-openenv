# Graph Report - D:\RL-PROJECT\data-cleaning-openenv  (2026-04-18)

## Corpus Check
- 45 files · ~71,366 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 843 nodes · 3126 edges · 33 communities detected
- Extraction: 31% EXTRACTED · 69% INFERRED · 0% AMBIGUOUS · INFERRED: 2152 edges (avg confidence: 0.55)
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
- `Deep Q-Network (DQN) model for data cleaning reinforcement learning.  This modul` --uses--> `Agent`  [INFERRED]
  D:\RL-PROJECT\data-cleaning-openenv\backend\ml\dqn_model.py → D:\RL-PROJECT\data-cleaning-openenv\backend\ml\base_agent.py
- `Deep Q-Network for approximating Q-values.          Architecture:     - Input la` --uses--> `Agent`  [INFERRED]
  D:\RL-PROJECT\data-cleaning-openenv\backend\ml\dqn_model.py → D:\RL-PROJECT\data-cleaning-openenv\backend\ml\base_agent.py
- `Initialize Q-network.                  Args:             state_dim: Dimension of` --uses--> `Agent`  [INFERRED]
  D:\RL-PROJECT\data-cleaning-openenv\backend\ml\dqn_model.py → D:\RL-PROJECT\data-cleaning-openenv\backend\ml\base_agent.py
- `Initialize network weights using Xavier initialization.` --uses--> `Agent`  [INFERRED]
  D:\RL-PROJECT\data-cleaning-openenv\backend\ml\dqn_model.py → D:\RL-PROJECT\data-cleaning-openenv\backend\ml\base_agent.py
- `Forward pass through network.                  Args:             state: Input st` --uses--> `Agent`  [INFERRED]
  D:\RL-PROJECT\data-cleaning-openenv\backend\ml\dqn_model.py → D:\RL-PROJECT\data-cleaning-openenv\backend\ml\base_agent.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (112): ABC, Agent, AgentCoordinator, Agent Coordinator for multi-agent data cleaning system.  This module implement, Update agent performance tracking based on received reward.          Args:, Get performance statistics for all agents.          Returns:             Dict, Get recommendations from all capable agents.          Returns:             Li, Select the best agent from recommendations.          Args:             recomm (+104 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (133): Benchmarking system for comparing DQN, Specialist Agents, and LLM approaches.  T, Initialize benchmark suite.                  Args:             device: Device fo, Load trained DQN model for benchmarking.                  Args:             mode, Benchmark a specific approach.                  Args:             approach: "DQN, Benchmark DQN approach., Benchmark Specialist Agents approach., Benchmark LLM approach (simulated since we don't have API access)., Determine expected correct action for a row.                  This is a simplifi (+125 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (121): reset(), ResetRequest, state(), step(), StepRequest, websocket_endpoint(), AuditLog, Stores row-level transformations performed during cleaning. (+113 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (23): Update agent's internal state based on received reward., Check if buffer is at capacity., Get current buffer size., Clear all transitions from buffer., Sample based on priorities.                  Args:             batch_size: Numbe, Update priorities based on TD-errors.                  Args:             indices, Get buffer statistics including priority information., Sample a batch of transitions from the buffer.                  Args: (+15 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (15): main(), Main entry point for running the server., BenchmarkResult, ComparisonSummary, DataCleaningBenchmark, main(), Set training/inference mode., DataCleaningEnvironment (+7 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (26): configure_logging(), health_check(), JsonFormatter, lifespan(), metrics(), _probe_database_engine(), FastAPI application entrypoint., Expose Prometheus metrics in text format. (+18 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (13): Calculate confidence in fill value., Select action to handle duplicates., Calculate similarity with previous rows., Calculate similarity between two rows., Select action to handle outliers., Check if value is an outlier using IQR method., Calculate median replacement value., Calculate confidence in outlier detection. (+5 more)

### Community 7 - "Community 7"
Cohesion: 0.1
Nodes (10): Get base reward for action type., Calculate progress bonus based on episode completion.          Args:, Calculate consistency bonus for successful action patterns.          Args:, Calculate penalty for actions that contradict previous decisions.          Arg, Calculate issue-specific reward adjustments.          Args:             actio, Calculate bonus for skip actions when appropriate.          Args:, Update internal tracking for future reward calculations.          Args:, Get statistics about reward distribution.          Returns:             Rewar (+2 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (9): from_dict(), Delete a model from the registry.                  Args:             version: Mo, Export a model to a specified path.                  Args:             version:, Import a model from a specified path.                  Args:             import_, Convert to dictionary., Clean up old models, keeping only the best N models.                  Args:, Initialize model registry.                  Args:             registry_dir: Dire, Load model metadata from registry file. (+1 more)

### Community 9 - "Community 9"
Cohesion: 0.15
Nodes (12): generate_easy_dataset(), generate_hard_dataset(), generate_medium_dataset(), grade_easy(), grade_hard(), grade_medium(), Score Task 3: all issues fixed., Task 2: Missing values + duplicates + formatting. (+4 more)

### Community 10 - "Community 10"
Cohesion: 0.2
Nodes (5): Reset agent state for new episode., Select action using epsilon-greedy policy.                  Args:             ob, Update mapping between action indices and action dictionaries., Encode observation to state vector.                  Args:             observati, Convert action index to action dictionary.

### Community 11 - "Community 11"
Cohesion: 0.25
Nodes (7): Database tests for backend initialization., Engine can produce a SQLAlchemy connection object., ORM metadata contains required tables., At minimum ensure table metadata is bound and creatable., test_crud_operations(), test_database_connection(), test_model_creation()

### Community 12 - "Community 12"
Cohesion: 0.33
Nodes (3): Deep Q-Network (DQN) model for data cleaning reinforcement learning.  This modul, Experience Replay Buffer for DQN training.  This module implements a replay buff, Reward Shaper for multi-agent data cleaning system.  This module implements so

### Community 13 - "Community 13"
Cohesion: 0.5
Nodes (2): Initialize Q-network.                  Args:             state_dim: Dimension of, Initialize network weights using Xavier initialization.

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (1): Celery worker startup entrypoint.

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): Celery application configuration.

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Get agent's confidence in last action.

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Initialize replay buffer.                  Args:             capacity: Maximum n

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Add a transition to the buffer.                  Args:             state: Curren

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Get buffer statistics.                  Returns:             Dictionary with buf

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Save buffer to file.                  Args:             filepath: Path to save b

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Load buffer from file.                  Args:             filepath: Path to load

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Initialize prioritized replay buffer.                  Args:             capacit

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Add a transition with maximum priority.                  Args:             state

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Save dataset to CSV file.                  Args:             df: DataFrame to sa

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Initialize generator.                  Args:             seed: Random seed for r

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Load dataset from CSV file.                  Args:             filepath: Input f

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

## Knowledge Gaps
- **97 isolated node(s):** `Emit [START] line at episode begin.`, `Emit [STEP] line after each env.step() with exact format.`, `Emit [END] line after episode completes. Always called even on exception.`, `Ask the LLM what cleaning action to take.`, `Run one full episode for a task and return score in [0, 1] range.` (+92 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 14`** (2 nodes): `worker.py`, `Celery worker startup entrypoint.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (2 nodes): `Celery application configuration.`, `celery_config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (2 nodes): `.get_confidence()`, `Get agent's confidence in last action.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (2 nodes): `Initialize replay buffer.                  Args:             capacity: Maximum n`, `.__init__()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (2 nodes): `Add a transition to the buffer.                  Args:             state: Curren`, `.add()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (2 nodes): `Get buffer statistics.                  Returns:             Dictionary with buf`, `.get_statistics()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `Save buffer to file.                  Args:             filepath: Path to save b`, `.save_buffer()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (2 nodes): `Load buffer from file.                  Args:             filepath: Path to load`, `.load_buffer()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (2 nodes): `.__init__()`, `Initialize prioritized replay buffer.                  Args:             capacit`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (2 nodes): `.add()`, `Add a transition with maximum priority.                  Args:             state`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (2 nodes): `Save dataset to CSV file.                  Args:             df: DataFrame to sa`, `.save_dataset()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (2 nodes): `Initialize generator.                  Args:             seed: Random seed for r`, `.__init__()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (2 nodes): `Load dataset from CSV file.                  Args:             filepath: Input f`, `.load_dataset()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentCoordinator` connect `Community 0` to `Community 1`, `Community 2`, `Community 4`?**
  _High betweenness centrality (0.179) - this node is a cross-community bridge._
- **Why does `DQNAgent` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 8`, `Community 10`, `Community 12`, `Community 16`?**
  _High betweenness centrality (0.176) - this node is a cross-community bridge._
- **Why does `Agent` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 10`, `Community 12`, `Community 13`, `Community 16`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Are the 141 inferred relationships involving `DQNAgent` (e.g. with `Agent` and `AgentFactory`) actually correct?**
  _`DQNAgent` has 141 INFERRED edges - model-reasoned connections that need verification._
- **Are the 130 inferred relationships involving `Agent` (e.g. with `AgentCoordinator` and `Agent Coordinator for multi-agent data cleaning system.  This module implement`) actually correct?**
  _`Agent` has 130 INFERRED edges - model-reasoned connections that need verification._
- **Are the 113 inferred relationships involving `AgentCoordinator` (e.g. with `Agent` and `FillMissingAgent`) actually correct?**
  _`AgentCoordinator` has 113 INFERRED edges - model-reasoned connections that need verification._
- **Are the 102 inferred relationships involving `SyntheticDatasetGenerator` (e.g. with `BenchmarkResult` and `ComparisonSummary`) actually correct?**
  _`SyntheticDatasetGenerator` has 102 INFERRED edges - model-reasoned connections that need verification._