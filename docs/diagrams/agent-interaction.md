# DataForge AI - Agent Interaction Diagram

```mermaid
sequenceDiagram
    participant CLI as CLI
    participant WF as LangGraph Workflow
    participant P as PlannerAgent
    participant E as EvaluatorAgent
    participant I as DataIngestionAgent
    participant PR as DataProfilingAgent
    participant S as StatisticalAnalysisAgent
    participant V as VisualizationAgent
    participant R as ReportingAgent
    participant State as GraphState
    participant LLM as LLM Provider

    CLI->>WF: analyze(dataset_path)
    WF->>State: Initialize GraphState

    Note over P: Step 1: Planning
    WF->>P: execute(state)
    P->>LLM: Analyze dataset schema
    LLM-->>P: Analysis plan
    P->>State: add_log("INFO", "Planner", "Plan created")
    P->>State: set("analysis_plan", plan)
    P-->>WF: AgentResult(CONTINUE, "Plan ready")

    Note over E: Step 2: Validation
    WF->>E: execute(state)
    E->>State: get("analysis_plan")
    E->>LLM: Validate plan quality
    LLM-->>E: Validation result
    alt Plan Valid
        E->>State: add_log("INFO", "Evaluator", "Plan valid")
        E-->>WF: AgentResult(CONTINUE, "Plan approved")
    else Plan Invalid
        E->>State: increment_retry()
        E->>State: add_log("WARN", "Evaluator", "Plan rejected")
        E-->>WF: AgentResult(RETRY, "Refine plan")
        WF->>P: execute(state)
    end

    Note over I: Step 3: Data Ingestion
    WF->>I: execute(state)
    I->>I: Load CSV file
    I->>I: Validate data
    I->>State: set("df", dataframe)
    I->>State: add_log("INFO", "Ingestion", f"Loaded {rows} rows")
    I-->>WF: AgentResult(CONTINUE, "Data loaded")

    Note over PR: Step 4: Data Profiling
    WF->>PR: execute(state)
    PR->>State: get("df")
    PR->>PR: Analyze schema
    PR->>PR: Detect types
    PR->>PR: Check quality
    PR->>State: set("schema", schema)
    PR->>State: set("types", types)
    PR->>State: add_log("INFO", "Profiling", "Profile complete")
    PR-->>WF: AgentResult(CONTINUE, "Profile ready")

    Note over S: Step 5: Statistics
    WF->>S: execute(state)
    S->>State: get("df")
    S->>S: Compute descriptive stats
    S->>S: Calculate correlations
    S->>State: set("stats", statistics)
    S->>State: add_log("INFO", "Statistics", "Stats computed")
    S-->>WF: AgentResult(CONTINUE, "Statistics ready")

    Note over V: Step 6: Visualization
    WF->>V: execute(state)
    V->>State: get("df")
    V->>State: get("stats")
    V->>V: Generate distributions
    V->>V: Generate scatter plots
    V->>V: Generate box plots
    V->>V: Generate correlation heatmap
    V->>State: set("visualizations", paths)
    V->>State: add_log("INFO", "Visualization", f"Generated {count} charts")
    V-->>WF: AgentResult(CONTINUE, "Visualizations ready")

    Note over R: Step 7: Reporting
    WF->>R: execute(state)
    R->>State: get("df")
    R->>State: get("stats")
    R->>State: get("visualizations")
    R->>R: Generate HTML report
    R->>R: Generate JSON report
    R->>State: set("report_path", html_path)
    R->>State: set("json_path", json_path)
    R->>State: add_log("INFO", "Reporting", "Reports created")
    R-->>WF: AgentResult(COMPLETE, "Analysis complete")

    WF->>State: mark_complete()
    WF-->>CLI: Final State
    CLI->>CLI: Display results
```

## Agent Interaction Patterns

### 1. State Read-Write Pattern

All agents follow the same pattern:

```python
async def execute(self, state: GraphState) -> AgentResult:
    # 1. Read from state
    df = state.get("df")

    # 2. Perform work
    result = self._do_work(df)

    # 3. Write to state
    updated_state = state.set("my_result", result)

    # 4. Log action
    updated_state = updated_state.add_log(
        level="INFO",
        agent=self.name,
        message="Work completed"
    )

    # 5. Return result
    return AgentResult(
        decision=AgentDecision.CONTINUE,
        message="Success"
    )
```

### 2. LLM Interaction Pattern

Agents that use LLMs follow this pattern:

```python
async def execute(self, state: GraphState) -> AgentResult:
    # 1. Prepare prompt
    prompt = self._build_prompt(state)

    # 2. Call LLM
    response = await self.llm.generate(prompt)

    # 3. Parse response
    result = self._parse_response(response)

    # 4. Update state
    return AgentResult(...)
```

### 3. Retry Pattern

When agents need to retry:

```python
async def execute(self, state: GraphState) -> AgentResult:
    try:
        # Attempt work
        result = await self._do_work(state)
        return AgentResult(AgentDecision.CONTINUE, "Success")
    except RecoverableError as e:
        # Increment retry count
        new_state = state.increment_retry()
        if new_state.retry_count < MAX_RETRIES:
            return AgentResult(AgentDecision.RETRY, str(e))
        else:
            return AgentResult(AgentDecision.FAIL, "Max retries exceeded")
```

## Agent Communication Matrix

| From | To | Data Flow | Purpose |
|------|-----|-----------|---------|
| Planner | Evaluator | analysis_plan | Plan validation |
| Evaluator | Planner | validation_result | Plan refinement |
| DataIngestion | DataProfiling | df | Data for profiling |
| DataProfiling | StatisticalAnalysis | schema, types | Context for stats |
| StatisticalAnalysis | Visualization | stats | Stats for charts |
| Visualization | Reporting | visualizations | Charts for report |
| All | GraphState | logs, data | Central state updates |

## Error Propagation

```mermaid
graph TB
    A[Agent Error] --> B{Error Type?}
    B -->|Recoverable| C[Return RETRY decision]
    B -->|Critical| D[Return FAIL decision]

    C --> E[Workflow increments retry_count]
    E --> F{retry_count < 3?}
    F -->|Yes| G[Re-execute agent]
    F -->|No| D

    D --> H[Workflow terminates]
    H --> I[Return error to CLI]

    style C fill:#FFD700
    style D fill:#FFB6C1
    style G fill:#90EE90
    style H fill:#FFB6C1