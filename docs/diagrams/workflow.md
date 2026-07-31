# DataForge AI - Workflow Diagram

```mermaid
graph TB
    START([Start Analysis]) --> INIT[Initialize GraphState]
    INIT --> PLANNER[PlannerAgent<br/>Create Analysis Plan]

    PLANNER --> EVALUATOR[EvaluatorAgent<br/>Validate Plan]
    EVALUATOR --> PLAN_VALID{Plan Valid?}

    PLAN_VALID -->|Yes| INGESTION[DataIngestionAgent<br/>Load CSV Data]
    PLAN_VALID -->|No| PLANNER_RETRY[PlannerAgent<br/>Refine Plan<br/>Retry: {retry_count}]
    PLANNER_RETRY --> EVALUATOR

    INGESTION --> PROFILING[DataProfilingAgent<br/>Analyze Schema & Types]
    PROFILING --> STATISTICS[StatisticalAnalysisAgent<br/>Compute Descriptive Stats]

    STATISTICS --> VISUALIZATION[VisualizationAgent<br/>Generate Charts]
    VISUALIZATION --> REPORTING[ReportingAgent<br/>Create HTML/JSON Reports]

    REPORTING --> OUTPUT_VALID{Outputs Valid?}

    OUTPUT_VALID -->|Yes| COMPLETE[Mark State Complete]
    OUTPUT_VALID -->|No| EVALUATOR_RETRY[EvaluatorAgent<br/>Retry Analysis<br/>Retry: {retry_count}]
    EVALUATOR_RETRY --> INGESTION

    COMPLETE --> END([End Analysis])

    MAX_RETRIES{Max Retries<br/>Reached?}
    PLANNER_RETRY --> MAX_RETRIES
    EVALUATOR_RETRY --> MAX_RETRIES
    MAX_RETRIES -->|Yes| FAIL([Failed - Max Retries])
    MAX_RETRIES -->|No| PLANNER_RETRY

    style START fill:#90EE90
    style END fill:#90EE90
    style FAIL fill:#FFB6C1
    style PLANNER fill:#87CEEB
    style EVALUATOR fill:#87CEEB
    style INGESTION fill:#DDA0DD
    style PROFILING fill:#DDA0DD
    style STATISTICS fill:#DDA0DD
    style VISUALIZATION fill:#DDA0DD
    style REPORTING fill:#DDA0DD
    style PLAN_VALID fill:#FFD700
    style OUTPUT_VALID fill:#FFD700
    style MAX_RETRIES fill:#FFD700
```

## Workflow Execution Flow

### Normal Flow (Happy Path)

1. **Initialization**: GraphState is created with dataset path and configuration
2. **Planning**: PlannerAgent analyzes the dataset and creates an analysis plan
3. **Validation**: EvaluatorAgent validates the plan quality
4. **Ingestion**: DataIngestionAgent loads and validates the CSV data
5. **Profiling**: DataProfilingAgent analyzes schema, types, and data quality
6. **Statistics**: StatisticalAnalysisAgent computes descriptive statistics
7. **Visualization**: VisualizationAgent generates interactive charts
8. **Reporting**: ReportingAgent creates HTML and JSON reports
9. **Completion**: State is marked complete and workflow ends

### Error Handling Flow

- **Plan Invalid**: If EvaluatorAgent rejects the plan, PlannerAgent refines it (max 3 retries)
- **Output Invalid**: If ReportingAgent detects issues, analysis restarts from Ingestion (max 3 retries)
- **Max Retries Exceeded**: Workflow fails gracefully with error message

### Agent Execution Order

```
Planner → Evaluator → Ingestion → Profiling → Statistics → Visualization → Reporting
```

Each agent:
1. Receives the current GraphState
2. Performs its specialized task
3. Returns AgentResult with decision and message
4. Updates GraphState with results and logs
5. Passes updated state to next agent

### State Transitions

| Step | Current Step | Next Step | Condition |
|------|-------------|-----------|-----------|
| 1 | None | PLANNING | Initial state |
| 2 | PLANNING | EVALUATION | Plan created |
| 3 | EVALUATION | INGESTION | Plan valid |
| 4 | EVALUATION | PLANNING | Plan invalid |
| 5 | INGESTION | PROFILING | Data loaded |
| 6 | PROFILING | STATISTICS | Profile complete |
| 7 | STATISTICS | VISUALIZATION | Stats computed |
| 8 | VISUALIZATION | REPORTING | Charts generated |
| 9 | REPORTING | COMPLETE | Reports created |
| 10 | REPORTING | INGESTION | Reports invalid |