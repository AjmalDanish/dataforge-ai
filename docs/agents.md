# DataForge AI - Agents and Graph Workflow

**Version**: 1.0 (Post-Architecture Review)
**Status**: Finalized

---

## Overview

DataForge AI uses **7 specialized AI agents** orchestrated through a **true branching graph** workflow. Unlike a linear pipeline, agents are dynamically selected by a central Planner Agent based on data characteristics and validation results.

---

## The 7 Agents

### Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                     PLANNER AGENT                            │
│              (Central Decision Maker)                        │
│         Analyzes state, decides next action                 │
└─────────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Ingestion   │  │  Profiling   │  │  Statistics  │
│   Agent      │  │   Agent      │  │   Agent      │
└──────────────┘  └──────────────┘  └──────────────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│Visualization │  │  Evaluator   │  │  Reporting   │
│   Agent      │  │   Agent      │  │   Agent      │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 1. Planner Agent

### Purpose
Central decision maker that orchestrates the entire workflow by analyzing the current GraphState and determining which agent to execute next.

### Responsibilities
1. Analyze current GraphState and execution history
2. Determine which agent to run next
3. Skip irrelevant agents based on data characteristics
4. Detect when analysis is complete
5. Handle errors by re-planning with fallback strategies

### Decision Matrix

| Current State | Decision | Reason |
|---------------|----------|--------|
| `current_step == "start"` | Run Ingestion Agent | Must load data first |
| Ingestion completed, data loaded | Run Profiling Agent | Need to understand data |
| Ingestion completed, no data | ERROR | Cannot proceed |
| Profiling completed, has numeric columns | Run Statistics Agent | Numeric analysis needed |
| Profiling completed, no numeric columns | Skip to Visualization | No stats possible |
| Statistics completed | Run Visualization Agent | Generate charts |
| Visualization completed | Run Evaluator Agent | Validate quality |
| Evaluator passed | Run Reporting Agent | Generate final report |
| Evaluator failed | RE-PLAN | More analysis needed |
| Reporting completed | COMPLETE | Analysis finished |

### Implementation

```python
from dataforge.core.state import GraphState
from dataforge.agents.base import Agent, AgentResult, AgentDecision

class PlannerAgent(Agent):
    """Central planning agent that determines execution flow."""

    async def execute(self, state: GraphState) -> AgentResult:
        """Decide next action based on current state and history."""

        # Step 1: Initial state - start with ingestion
        if state.current_step == "start":
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="Starting analysis with data ingestion",
                next_agent_suggestion="DataIngestionAgent",
                metadata={"reason": "initial_state"}
            )

        # Step 2: After ingestion - validate and decide next
        if "DataIngestionAgent" in state.steps_completed:
            raw_data = state.get("raw_data")
            if raw_data is None:
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="No data loaded, cannot continue",
                    metadata={"reason": "no_data_loaded"}
                )

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Data loaded ({len(raw_data)} rows), proceeding to profiling",
                next_agent_suggestion="DataProfilingAgent",
                metadata={
                    "reason": "data_loaded_successfully",
                    "rows": len(raw_data),
                    "columns": len(raw_data.columns)
                }
            )

        # Step 3: After profiling - check for numeric columns
        if "DataProfilingAgent" in state.steps_completed:
            has_numeric = state.get("has_numeric_columns", False)
            has_categorical = state.get("has_categorical_columns", False)

            if not has_numeric and not has_categorical:
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message="No analyzable columns found",
                    metadata={"reason": "no_analyzable_columns"}
                )

            if not has_numeric:
                self.logger.info(
                    "No numeric columns, skipping statistical analysis",
                    agent=self.name
                )
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="No numeric data, skipping statistics, proceeding to visualization",
                    next_agent_suggestion="VisualizationAgent",
                    metadata={"reason": "no_numeric_columns"}
                )

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="Numeric data found, running statistical analysis",
                next_agent_suggestion="StatisticalAnalysisAgent",
                metadata={
                    "reason": "numeric_data_available",
                    "numeric_column_count": state.get("numeric_column_count", 0)
                }
            )

        # Step 4: After statistics - proceed to visualization
        if "StatisticalAnalysisAgent" in state.steps_completed:
            stats = state.get("statistics")
            if stats:
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message=f"Statistical analysis complete ({stats.get('correlations_count', 0)} correlations found), generating visualizations",
                    next_agent_suggestion="VisualizationAgent",
                    metadata={"reason": "statistics_complete"}
                )
            else:
                # Stats ran but produced no results (edge case)
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="Proceeding to visualization",
                    next_agent_suggestion="VisualizationAgent",
                    metadata={"reason": "statistics_produced_no_results"}
                )

        # Step 5: After visualization - evaluate quality
        if "VisualizationAgent" in state.steps_completed:
            viz_count = len(state.get("visualizations", []))
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Generated {viz_count} visualizations, validating results",
                next_agent_suggestion="EvaluatorAgent",
                metadata={
                    "reason": "visualization_complete",
                    "visualization_count": viz_count
                }
            )

        # Step 6: After evaluator - decide to continue or complete
        if "EvaluatorAgent" in state.steps_completed:
            if state.validation_status == "failed":
                failed_checks = state.get("failed_checks", [])

                # Limit replan attempts
                if state.retry_count >= state.max_retries:
                    self.logger.warning(
                        "Max retries reached, proceeding to report anyway",
                        agent=self.name,
                        retry_count=state.retry_count
                    )
                    return AgentResult(
                        decision=AgentDecision.CONTINUE,
                        message="Max validation retries reached, generating report with available results",
                        next_agent_suggestion="ReportingAgent",
                        metadata={"reason": "max_retries_exceeded"}
                    )

                # Suggest remediation
                suggestion = self._suggest_remediation(failed_checks, state)
                return AgentResult(
                    decision=AgentDecision.REPLAN,
                    message=f"Validation failed: {', '.join(failed_checks)}. Re-planning.",
                    next_agent_suggestion=suggestion,
                    metadata={
                        "reason": "validation_failed",
                        "failed_checks": failed_checks
                    }
                )
            else:
                return AgentResult(
                    decision=AgentDecision.CONTINUE,
                    message="Validation passed, generating final report",
                    next_agent_suggestion="ReportingAgent",
                    metadata={"reason": "validation_passed"}
                )

        # Step 7: After reporting - complete
        if "ReportingAgent" in state.steps_completed:
            return AgentResult(
                decision=AgentDecision.COMPLETE,
                message="Analysis complete, report generated",
                metadata={"reason": "report_generated"}
            )

        # Fallback: shouldn't reach here
        self.logger.warning(
            "Planner reached unexpected state",
            agent=self.name,
            current_step=state.current_step,
            completed_steps=state.steps_completed
        )
        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message="Proceeding with next agent (fallback)",
            metadata={"reason": "fallback"}
        )

    def _suggest_remediation(self, failed_checks: List[str], state: GraphState) -> str:
        """Suggest which agent to run for remediation."""

        suggestions = {
            "has_data": "DataIngestionAgent",
            "has_insights": "StatisticalAnalysisAgent",
            "data_quality": "DataProfilingAgent",
            "sufficient_depth": "StatisticalAnalysisAgent",
        }

        for check in failed_checks:
            if check in suggestions:
                return suggestions[check]

        # Default: try profiling again
        return "DataProfilingAgent"
```

### Logging Examples

```python
# Successful planning
[INFO] ✓ [PlannerAgent] Starting analysis with data ingestion
[INFO] ✓ [PlannerAgent] Data loaded (1000 rows), proceeding to profiling
[INFO] ✓ [PlannerAgent] Numeric data found, running statistical analysis
[INFO] ✓ [PlannerAgent] Generated 4 visualizations, validating results
[INFO] ✓ [PlannerAgent] Validation passed, generating final report
[INFO] ✓ [PlannerAgent] Analysis complete, report generated

# With re-planning
[INFO] ✓ [PlannerAgent] Generated 2 visualizations, validating results
[WARNING] ⚠ [PlannerAgent] Validation failed: has_insights, sufficient_depth. Re-planning.
[INFO] ✓ [PlannerAgent] Running StatisticalAnalysisAgent for remediation
```

---

## 2. Evaluator Agent

### Purpose
Validates analysis quality and requests additional work if results are insufficient.

### Responsibilities
1. Check if data was successfully loaded
2. Verify insights were generated
3. Assess data quality
4. Evaluate analysis depth
5. Request additional analysis if checks fail

### Validation Checks

| Check | Criteria | Pass Condition |
|-------|----------|----------------|
| `has_data` | Data loaded | `state.get("raw_data") is not None` |
| `has_insights` | Insights generated | `len(state.get("insights", [])) >= 3` |
| `data_quality` | Acceptable quality | Missing values < 50% overall |
| `sufficient_depth` | Enough analysis | At least 3 agents completed |

### Implementation

```python
class EvaluatorAgent(Agent):
    """Validates analysis results and quality."""

    async def execute(self, state: GraphState) -> AgentResult:
        """Validate current analysis results against quality gates."""

        checks = {
            "has_data": self._check_has_data(state),
            "has_insights": self._check_has_insights(state),
            "data_quality": self._check_data_quality(state),
            "sufficient_depth": self._check_analysis_depth(state),
        }

        all_passed = all(checks.values())

        self.logger.info(
            "Validation checks performed",
            agent=self.name,
            checks=checks,
            all_passed=all_passed
        )

        if all_passed:
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="All validation checks passed",
                data_updates={"validation_status": "passed"},
                metadata={
                    "validation_results": checks,
                    "all_checks_passed": True
                }
            )
        else:
            failed_checks = [k for k, v in checks.items() if not v]

            # Increment retry count
            new_retry_count = state.retry_count + 1

            return AgentResult(
                decision=AgentDecision.REPLAN,
                message=f"Validation failed: {', '.join(failed_checks)}",
                data_updates={
                    "validation_status": "failed",
                    "failed_checks": failed_checks,
                    "retry_count": new_retry_count
                },
                metadata={
                    "validation_results": checks,
                    "failed_checks": failed_checks,
                    "retry_count": new_retry_count
                }
            )

    def _check_has_data(self, state: GraphState) -> bool:
        """Check if data was loaded."""
        raw_data = state.get("raw_data")
        if raw_data is None:
            return False
        return len(raw_data) > 0

    def _check_has_insights(self, state: GraphState) -> bool:
        """Check if insights were generated."""
        insights = state.get("insights", [])
        return len(insights) >= 3

    def _check_data_quality(self, state: GraphState) -> bool:
        """Check data quality (missing values, etc.)."""
        profile = state.get("profile")
        if not profile:
            return True  # Skip check if no profile

        # Check overall missing value percentage
        missing_ratio = profile.get("overall_missing_ratio", 0)
        return missing_ratio < 0.5  # Less than 50% missing

    def _check_analysis_depth(self, state: GraphState) -> bool:
        """Check if sufficient analysis was performed."""
        # Require at least: ingestion + profiling + (stats OR viz)
        required = {"DataIngestionAgent", "DataProfilingAgent"}
        optional = {"StatisticalAnalysisAgent", "VisualizationAgent"}

        completed = set(state.steps_completed)
        has_required = required.issubset(completed)
        has_optional = len(completed.intersection(optional)) > 0

        return has_required and has_optional
```

### Validation Loop Behavior

```
Evaluator checks
    ↓
All passed?
    ↓ Yes                    ↓ No
Proceed to Reporting    Increment retry count
                            ↓
                        Max retries (3)?
                            ↓ Yes                    ↓ No
Proceed anyway          Suggest remediation
                                                    ↓
                                                Planner re-runs agents
```

---

## 3. Data Ingestion Agent

### Purpose
Read and parse structured data files into a DataFrame.

### Supported Formats
- CSV (with encoding detection)
- Parquet

### Error Handling

| Error | Action |
|-------|--------|
| File not found | Fatal - halt workflow |
| Permission denied | Fatal - halt workflow |
| Empty file | Fatal - halt workflow |
| Encoding error | Retry with alternate encodings (UTF-8 → Latin-1 → CP1252) |

### Implementation

```python
import pandas as pd
from pathlib import Path

class DataIngestionAgent(Agent):
    """Agent for ingesting structured data files."""

    ENCODINGS = ["utf-8", "latin-1", "cp1252"]

    async def execute(self, state: GraphState) -> AgentResult:
        """Ingest the dataset file."""

        file_path = state.input_dataset_path
        path = Path(file_path)

        # Validate path
        if not path.exists():
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"File not found: {file_path}",
                metadata={"error_type": "FileNotFoundError"}
            )

        if not path.is_file():
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"Path is not a file: {file_path}",
                metadata={"error_type": "NotAFileError"}
            )

        # Detect format
        file_format = self._detect_format(path)

        try:
            # Read file with encoding fallback for CSV
            if file_format == "csv":
                df = await self._read_csv_with_retry(path)
            else:  # parquet
                df = pd.read_parquet(path)

            # Validate DataFrame
            if df.empty:
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message=f"File is empty: {file_path}",
                    metadata={"error_type": "EmptyDataError"}
                )

            if len(df.columns) == 0:
                return AgentResult(
                    decision=AgentDecision.ERROR,
                    message=f"No columns found in file: {file_path}",
                    metadata={"error_type": "NoColumnsError"}
                )

            self.logger.info(
                "Data loaded successfully",
                agent=self.name,
                rows=len(df),
                columns=len(df.columns),
                file_size_bytes=path.stat().st_size,
                format=file_format
            )

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Loaded {len(df)} rows, {len(df.columns)} columns",
                data_updates={
                    "raw_data": df,
                    "file_format": file_format,
                    "original_file_size": path.stat().st_size,
                    "load_timestamp": datetime.utcnow().isoformat()
                },
                metadata={
                    "rows": len(df),
                    "columns": len(df.columns),
                    "file_format": file_format,
                    "file_size_bytes": path.stat().st_size
                }
            )

        except Exception as e:
            self.logger.error(
                "Data ingestion failed",
                agent=self.name,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"Failed to read file: {str(e)}",
                metadata={
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )

    def _detect_format(self, path: Path) -> str:
        """Detect file format from extension."""
        ext = path.suffix.lower()
        if ext == ".csv":
            return "csv"
        elif ext in [".parquet", ".pq"]:
            return "parquet"
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    async def _read_csv_with_retry(self, path: Path) -> pd.DataFrame:
        """Read CSV file with encoding fallback."""

        for encoding in self.ENCODINGS:
            try:
                df = pd.read_csv(path, encoding=encoding)
                self.logger.debug(
                    f"Successfully read with encoding: {encoding}",
                    agent=self.name
                )
                return df
            except UnicodeDecodeError:
                self.logger.debug(
                    f"Failed with encoding {encoding}, trying next",
                    agent=self.name
                )
                continue

        raise ValueError(f"Could not decode file with any encoding: {self.ENCODINGS}")
```

---

## 4. Data Profiling Agent

### Purpose
Analyze data structure, types, and basic characteristics.

### Outputs
- Column information (types, unique counts, missing values)
- Data type classification (numeric, categorical, temporal, text)
- Key candidate columns
- High-cardinality warnings

### Implementation Outline

```python
class DataProfilingAgent(Agent):
    """Agent for profiling dataset structure."""

    async def execute(self, state: GraphState) -> AgentResult:
        """Profile the dataset."""

        df = state.get("raw_data")
        if df is None:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="No data available for profiling"
            )

        # Analyze columns
        columns_info = {}
        numeric_columns = []
        categorical_columns = []

        for col in df.columns:
            info = self._analyze_column(df[col])
            columns_info[col] = info

            if info["type"] == "numeric":
                numeric_columns.append(col)
            elif info["type"] == "categorical":
                categorical_columns.append(col)

        # Generate basic insights
        insights = await self._generate_basic_insights(df, columns_info)

        profile = {
            "columns": columns_info,
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "has_numeric_columns": len(numeric_columns) > 0,
            "has_categorical_columns": len(categorical_columns) > 0,
            "overall_missing_ratio": df.isna().sum().sum() / (len(df) * len(df.columns)),
        }

        self.logger.info(
            "Profiling complete",
            agent=self.name,
            numeric_columns=len(numeric_columns),
            categorical_columns=len(categorical_columns)
        )

        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message=f"Profiled {len(columns_info)} columns: {len(numeric_columns)} numeric, {len(categorical_columns)} categorical",
            data_updates={
                "profile": profile,
                "insights": state.get("insights", []) + insights
            },
            metadata={
                "column_count": len(columns_info),
                "numeric_column_count": len(numeric_columns),
                "categorical_column_count": len(categorical_columns)
            }
        )

    def _analyze_column(self, series: pd.Series) -> dict:
        """Analyze a single column."""
        dtype = str(series.dtype)
        n_unique = series.nunique()
        n_missing = series.isna().sum()
        missing_ratio = n_missing / len(series)

        # Infer semantic type
        if pd.api.types.is_numeric_dtype(series):
            col_type = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(series):
            col_type = "temporal"
        elif pd.api.types.is_bool_dtype(series):
            col_type = "boolean"
        else:
            # Categorical if low cardinality
            if n_unique / len(series) < 0.1:
                col_type = "categorical"
            else:
                col_type = "text"

        return {
            "name": str(series.name),
            "dtype": dtype,
            "type": col_type,
            "n_unique": n_unique,
            "n_missing": n_missing,
            "missing_ratio": missing_ratio,
            "is_high_cardinality": (col_type == "categorical" and n_unique > 100)
        }

    async def _generate_basic_insights(self, df: pd.DataFrame, columns_info: dict) -> List[dict]:
        """Generate basic insights about the data."""
        insights = []

        # Insight about data quality
        total_missing = sum(c["n_missing"] for c in columns_info.values())
        if total_missing > 0:
            insights.append({
                "type": "data_quality",
                "message": f"Dataset has {total_missing} missing values across {len(df.columns)} columns",
                "severity": "warning" if total_missing / len(df) / len(df.columns) > 0.1 else "info"
            })

        # Insight about column types
        numeric_count = sum(1 for c in columns_info.values() if c["type"] == "numeric")
        if numeric_count == 0:
            insights.append({
                "type": "data_structure",
                "message": "No numeric columns found - statistical analysis will be skipped",
                "severity": "warning"
            })

        return insights
```

---

## 5. Statistical Analysis Agent

### Purpose
Compute descriptive statistics and identify relationships.

### When Skipped
- No numeric columns detected by Profiling Agent

### Outputs
- Descriptive statistics (mean, median, std, quartiles)
- Correlation matrix
- Significant correlations (p < 0.05)
- Outlier information

### Implementation Outline

```python
from scipy import stats

class StatisticalAnalysisAgent(Agent):
    """Agent for statistical analysis."""

    async def execute(self, state: GraphState) -> AgentResult:
        """Perform statistical analysis."""

        df = state.get("raw_data")
        profile = state.get("profile", {})

        numeric_columns = profile.get("numeric_columns", [])

        if not numeric_columns:
            return AgentResult(
                decision=AgentDecision.ERROR,
                message="No numeric columns available for statistical analysis"
            )

        # Descriptive statistics
        descriptive = self._compute_descriptive(df, numeric_columns)

        # Correlations
        correlations = self._compute_correlations(df, numeric_columns)

        # Significant correlations
        significant_correlations = self._find_significant_correlations(
            df, numeric_columns, correlations
        )

        # Outliers
        outliers = self._detect_outliers(df, numeric_columns)

        # Generate insights
        insights = await self._generate_insights(descriptive, significant_correlations, outliers)

        statistics = {
            "descriptive": descriptive,
            "correlations": correlations,
            "significant_correlations": significant_correlations,
            "outliers": outliers,
            "correlations_count": len(significant_correlations)
        }

        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message=f"Analyzed {len(numeric_columns)} numeric columns, found {len(significant_correlations)} significant correlations",
            data_updates={
                "statistics": statistics,
                "insights": state.get("insights", []) + insights
            },
            metadata={
                "numeric_column_count": len(numeric_columns),
                "correlations_found": len(significant_correlations),
                "outliers_detected": sum(len(o["indices"]) for o in outliers.values())
            }
        )

    def _compute_descriptive(self, df: pd.DataFrame, columns: List[str]) -> dict:
        """Compute descriptive statistics."""
        descriptive = {}
        for col in columns:
            series = df[col].dropna()
            descriptive[col] = {
                "count": len(series),
                "mean": float(series.mean()),
                "median": float(series.median()),
                "std": float(series.std()),
                "min": float(series.min()),
                "max": float(series.max()),
                "q25": float(series.quantile(0.25)),
                "q75": float(series.quantile(0.75)),
            }
        return descriptive

    def _compute_correlations(self, df: pd.DataFrame, columns: List[str]) -> dict:
        """Compute correlation matrix."""
        corr_matrix = df[columns].corr(method="pearson")
        correlations = {}

        for i, col1 in enumerate(columns):
            for col2 in columns[i+1:]:
                correlations[(col1, col2)] = float(corr_matrix.loc[col1, col2])

        return correlations

    def _find_significant_correlations(
        self,
        df: pd.DataFrame,
        columns: List[str],
        correlations: dict,
        threshold: float = 0.5,
        alpha: float = 0.05
    ) -> List[dict]:
        """Find statistically significant correlations."""
        significant = []

        for (col1, col2), corr_value in correlations.items():
            if abs(corr_value) < threshold:
                continue

            # Calculate p-value
            series1 = df[col1].dropna()
            series2 = df[col2].dropna()
            common_idx = series1.index.intersection(series2.index)

            if len(common_idx) < 3:
                continue

            _, p_value = stats.pearsonr(series1[common_idx], series2[common_idx])

            if p_value < alpha:
                strength = "strong" if abs(corr_value) >= 0.7 else "moderate"
                direction = "positive" if corr_value > 0 else "negative"

                significant.append({
                    "column1": col1,
                    "column2": col2,
                    "correlation": corr_value,
                    "p_value": p_value,
                    "strength": strength,
                    "direction": direction
                })

        # Sort by absolute correlation
        significant.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        return significant[:10]  # Top 10

    def _detect_outliers(self, df: pd.DataFrame, columns: List[str]) -> dict:
        """Detect outliers using IQR method."""
        outliers = {}

        for col in columns:
            series = df[col].dropna()
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outlier_mask = (series < lower_bound) | (series > upper_bound)
            outlier_indices = series[outlier_mask].index.tolist()

            outliers[col] = {
                "count": len(outlier_indices),
                "percentage": len(outlier_indices) / len(series) * 100,
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
            }

        return outliers

    async def _generate_insights(
        self,
        descriptive: dict,
        correlations: List[dict],
        outliers: dict
    ) -> List[dict]:
        """Generate insights from statistics."""
        insights = []

        # Insight about correlations
        if correlations:
            top_corr = correlations[0]
            insights.append({
                "type": "correlation",
                "message": f"Strongest correlation: {top_corr['column1']} and {top_corr['column2']} ({top_corr['direction']}, r={top_corr['correlation']:.2f})",
                "severity": "info"
            })

        # Insight about outliers
        total_outliers = sum(o["count"] for o in outliers.values())
        if total_outliers > 0:
            insights.append({
                "type": "outliers",
                "message": f"Detected {total_outliers} outlier values across {len(outliers)} columns",
                "severity": "info"
            })

        return insights
```

---

## 6. Visualization Agent

### Purpose
Generate essential, high-value visualizations.

### 4 Essential Chart Types

| Chart Type | Use Case | Generated When |
|------------|----------|----------------|
| Histogram | Numeric distribution | At least 1 numeric column |
| Bar Chart | Categorical distribution | At least 1 categorical column |
| Heatmap | Correlation matrix | At least 2 numeric columns |
| Scatter Plot | Relationship visualization | Significant correlation found |

### Implementation Outline

```python
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

class VisualizationAgent(Agent):
    """Agent for generating visualizations."""

    CHART_TYPES = ["histogram", "bar", "heatmap", "scatter"]

    async def execute(self, state: GraphState) -> AgentResult:
        """Generate visualizations."""

        df = state.get("raw_data")
        profile = state.get("profile", {})
        statistics = state.get("statistics", {})

        if df is None:
            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message="No data available for visualization"
            )

        visualizations = []

        # 1. Histogram for first numeric column
        numeric_columns = profile.get("numeric_columns", [])
        if numeric_columns:
            viz = await self._create_histogram(df, numeric_columns[0], state.output_dir)
            if viz:
                visualizations.append(viz)

        # 2. Bar chart for first categorical column
        categorical_columns = profile.get("categorical_columns", [])
        # Filter out high-cardinality
        cat_columns = [
            c for c in categorical_columns
            if not profile["columns"][c].get("is_high_cardinality", False)
        ]
        if cat_columns:
            viz = await self._create_bar_chart(df, cat_columns[0], state.output_dir)
            if viz:
                visualizations.append(viz)

        # 3. Heatmap if 2+ numeric columns
        if len(numeric_columns) >= 2:
            viz = await self._create_heatmap(df, numeric_columns, state.output_dir)
            if viz:
                visualizations.append(viz)

        # 4. Scatter plot for top correlation
        significant_correlations = statistics.get("significant_correlations", [])
        if significant_correlations and len(numeric_columns) >= 2:
            top_corr = significant_correlations[0]
            viz = await self._create_scatter(
                df,
                top_corr["column1"],
                top_corr["column2"],
                state.output_dir
            )
            if viz:
                visualizations.append(viz)

        return AgentResult(
            decision=AgentDecision.CONTINUE,
            message=f"Generated {len(visualizations)} visualizations",
            data_updates={"visualizations": visualizations},
            metadata={
                "visualization_count": len(visualizations),
                "chart_types": [v["type"] for v in visualizations]
            }
        )

    async def _create_histogram(
        self,
        df: pd.DataFrame,
        column: str,
        output_dir: str
    ) -> Optional[dict]:
        """Create histogram for numeric column."""
        try:
            fig = px.histogram(
                df,
                x=column,
                nbins=30,
                title=f"Distribution of {column}",
                labels={column: column, "count": "Frequency"}
            )

            filename = f"histogram_{self._sanitize_filename(column)}.png"
            filepath = Path(output_dir) / "visualizations" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            fig.write_image(str(filepath), width=1200, height=600, scale=2)

            return {
                "type": "histogram",
                "title": f"Distribution of {column}",
                "filepath": str(filepath),
                "column": column
            }
        except Exception as e:
            self.logger.warning(f"Failed to create histogram: {e}", agent=self.name)
            return None

    async def _create_bar_chart(
        self,
        df: pd.DataFrame,
        column: str,
        output_dir: str
    ) -> Optional[dict]:
        """Create bar chart for categorical column."""
        try:
            # Get top 20 categories
            value_counts = df[column].value_counts().head(20)

            fig = px.bar(
                x=value_counts.index,
                y=value_counts.values,
                title=f"Top 20 Categories: {column}",
                labels={"x": column, "y": "Count"}
            )

            filename = f"bar_{self._sanitize_filename(column)}.png"
            filepath = Path(output_dir) / "visualizations" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            fig.write_image(str(filepath), width=1200, height=600, scale=2)

            return {
                "type": "bar",
                "title": f"Top 20 Categories: {column}",
                "filepath": str(filepath),
                "column": column
            }
        except Exception as e:
            self.logger.warning(f"Failed to create bar chart: {e}", agent=self.name)
            return None

    async def _create_heatmap(
        self,
        df: pd.DataFrame,
        columns: List[str],
        output_dir: str
    ) -> Optional[dict]:
        """Create correlation heatmap."""
        try:
            corr_matrix = df[columns].corr()

            fig = px.imshow(
                corr_matrix,
                title="Correlation Matrix",
                color_continuous_scale="RdBu",
                aspect="auto"
            )

            filename = "heatmap_correlations.png"
            filepath = Path(output_dir) / "visualizations" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            fig.write_image(str(filepath), width=1200, height=1000, scale=2)

            return {
                "type": "heatmap",
                "title": "Correlation Matrix",
                "filepath": str(filepath),
                "columns": columns
            }
        except Exception as e:
            self.logger.warning(f"Failed to create heatmap: {e}", agent=self.name)
            return None

    async def _create_scatter(
        self,
        df: pd.DataFrame,
        x_column: str,
        y_column: str,
        output_dir: str
    ) -> Optional[dict]:
        """Create scatter plot."""
        try:
            fig = px.scatter(
                df,
                x=x_column,
                y=y_column,
                title=f"{x_column} vs {y_column}",
                opacity=0.6
            )

            # Add trend line
            df_clean = df[[x_column, y_column]].dropna()
            if len(df_clean) > 1:
                import numpy as np
                coeffs = np.polyfit(df_clean[x_column], df_clean[y_column], 1)
                trend_x = np.linspace(df_clean[x_column].min(), df_clean[x_column].max(), 100)
                trend_y = np.polyval(coeffs, trend_x)
                fig.add_scatter(x=trend_x, y=trend_y, mode="lines", name="Trend")

            filename = f"scatter_{self._sanitize_filename(x_column)}_vs_{self._sanitize_filename(y_column)}.png"
            filepath = Path(output_dir) / "visualizations" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            fig.write_image(str(filepath), width=1200, height=800, scale=2)

            return {
                "type": "scatter",
                "title": f"{x_column} vs {y_column}",
                "filepath": str(filepath),
                "x_column": x_column,
                "y_column": y_column
            }
        except Exception as e:
            self.logger.warning(f"Failed to create scatter plot: {e}", agent=self.name)
            return None

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize column name for filename."""
        return "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in name)
```

---

## 7. Reporting Agent

### Purpose
Compile comprehensive Markdown and HTML reports.

### Report Sections

1. **Overview** - Dataset summary, execution info
2. **Data Profile** - Column information, types, missing values
3. **Statistical Findings** - Descriptive stats, correlations, outliers
4. **Key Insights** - All generated insights
5. **Visualizations** - Embedded charts with descriptions
6. **Methodology** - Explanation of methods used
7. **Limitations** - Known limitations

### Implementation Outline

```python
import markdown
from pathlib import Path

class ReportingAgent(Agent):
    """Agent for generating reports."""

    async def execute(self, state: GraphState) -> AgentResult:
        """Generate final reports."""

        # Generate Markdown report
        markdown_content = self._generate_markdown(state)

        # Generate HTML report
        html_content = self._generate_html(markdown_content)

        # Save reports
        output_dir = Path(state.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        markdown_path = output_dir / "report.md"
        html_path = output_dir / "report.html"

        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Export logs
        log_file = state.logs[0].get("file") if state.logs else None

        self.logger.info(
            "Reports generated",
            agent=self.name,
            markdown_path=str(markdown_path),
            html_path=str(html_path)
        )

        return AgentResult(
            decision=AgentDecision.COMPLETE,
            message=f"Reports generated: {markdown_path.name}, {html_path.name}",
            data_updates={
                "report_markdown_path": str(markdown_path),
                "report_html_path": str(html_path)
            },
            metadata={
                "markdown_path": str(markdown_path),
                "html_path": str(html_path)
            }
        )

    def _generate_markdown(self, state: GraphState) -> str:
        """Generate Markdown report."""

        df = state.get("raw_data")
        profile = state.get("profile", {})
        statistics = state.get("statistics", {})
        insights = state.get("insights", [])
        visualizations = state.get("visualizations", [])

        lines = []

        # Title
        lines.append("# DataForge Analysis Report\n")

        # Overview
        lines.append("## Dataset Overview\n")
        if df is not None:
            lines.append(f"- **File**: {state.input_dataset_path}")
            lines.append(f"- **Rows**: {len(df):,}")
            lines.append(f"- **Columns**: {len(df.columns)}")
            lines.append(f"- **Execution ID**: `{state.execution_id}`")
            lines.append(f"- **Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

        # Data Profile
        if profile:
            lines.append("## Data Profile\n")
            numeric = profile.get("numeric_columns", [])
            categorical = profile.get("categorical_columns", [])
            lines.append(f"- **Numeric Columns**: {len(numeric)}")
            lines.append(f"- **Categorical Columns**: {len(categorical)}")
            if profile.get("overall_missing_ratio") is not None:
                missing_pct = profile["overall_missing_ratio"] * 100
                lines.append(f"- **Missing Values**: {missing_pct:.1f}%\n")

        # Statistical Findings
        if statistics:
            lines.append("## Statistical Findings\n")

            descriptive = statistics.get("descriptive", {})
            if descriptive:
                lines.append("### Descriptive Statistics\n")
                lines.append("| Column | Mean | Median | Std Dev | Min | Max |")
                lines.append("|--------|------|--------|---------|-----|-----|")
                for col, stats in descriptive.items():
                    lines.append(
                        f"| {col} | {stats['mean']:.2f} | {stats['median']:.2f} | "
                        f"{stats['std']:.2f} | {stats['min']:.2f} | {stats['max']:.2f} |"
                    )
                lines.append("")

            # Correlations
            sig_corrs = statistics.get("significant_correlations", [])
            if sig_corrs:
                lines.append("### Significant Correlations\n")
                for corr in sig_corrs[:5]:
                    lines.append(
                        f"- **{corr['column1']}** × **{corr['column2']}**: "
                        f"{corr['direction']} ({corr['strength']}), r={corr['correlation']:.2f}, p={corr['p_value']:.4f}"
                    )
                lines.append("")

        # Insights
        if insights:
            lines.append("## Key Insights\n")
            for insight in insights:
                icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}.get(insight.get("severity", "info"), "•")
                lines.append(f"{icon} **{insight.get('type', 'insight')}**: {insight['message']}")
            lines.append("")

        # Visualizations
        if visualizations:
            lines.append("## Visualizations\n")
            for viz in visualizations:
                rel_path = Path(viz["filepath"]).relative_to(state.output_dir)
                lines.append(f"### {viz['title']}\n")
                lines.append(f"![{viz['title']}]({rel_path})\n")
                lines.append(f"*Type: {viz['type']}*\n")

        # Methodology
        lines.append("## Methodology\n")
        lines.append("This analysis was performed by DataForge AI, an autonomous multi-agent system. The following agents were executed:\n")
        for step in state.steps_completed:
            lines.append(f"- {step}")
        lines.append("")

        # Limitations
        lines.append("## Limitations\n")
        lines.append("- Analysis is based on the provided dataset only")
        lines.append("- Correlations do not imply causation")
        lines.append("- Statistical tests assume data meets assumptions")
        lines.append("- Results should be reviewed by domain experts\n")

        return "\n".join(lines)

    def _generate_html(self, markdown_content: str) -> str:
        """Generate HTML report from Markdown."""

        html_body = markdown.markdown(
            markdown_content,
            extensions=["tables", "fenced_code"]
        )

        html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DataForge Analysis Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 40px;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px 15px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        img {{
            max-width: 100%;
            height: auto;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .insight {{
            background-color: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin: 10px 0;
            border-radius: 4px;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "Courier New", monospace;
        }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""

        return html_template
```

---

## Graph Workflow Summary

### Execution Flow

```
START
  ↓
Planner Agent
  ↓ (suggests: IngestionAgent)
Data Ingestion Agent
  ↓
Planner Agent
  ↓ (suggests: ProfilingAgent)
Data Profiling Agent
  ↓
Planner Agent
  ├─→ (if numeric) Statistical Analysis Agent
  └─→ (if no numeric) Visualization Agent
      ↓
      Planner Agent
      ↓
      Visualization Agent
      ↓
      Planner Agent
      ↓
      Evaluator Agent
      ├─→ (if passed) Reporting Agent → END
      └─→ (if failed) Planner Agent (retry loop)
```

### Key Characteristics

1. **Planner Runs Multiple Times**: After each agent, Planner re-evaluates
2. **Conditional Branching**: Skip agents based on data
3. **Validation Loops**: Evaluator can trigger re-planning
4. **Error Resilience**: Graceful degradation on failures
5. **Dynamic Adaptation**: Execution path adapts to data

---

## Agent Communication

### Via GraphState

All agents communicate through the shared GraphState:

```python
# Agent writes data
state = state.set("raw_data", df)
state = state.set("profile", profile_data)
state = state.set("insights", new_insights)

# Agent reads data
df = state.get("raw_data")
profile = state.get("profile")
```

### Via Agent Decision

Agents communicate intent through AgentResult:

```python
return AgentResult(
    decision=AgentDecision.REPLAN,  # "I need more analysis"
    message="Insufficient insights generated",
    next_agent_suggestion="StatisticalAnalysisAgent"
)
```

---

## Testing Strategy

### Unit Tests

Test each agent in isolation with mocked dependencies:

```python
@pytest.mark.asyncio
async def test_planner_agent_initial_state():
    state = GraphState(
        input_dataset_path="test.csv",
        current_step="start"
    )

    planner = PlannerAgent(mock_llm, mock_logger)
    result = await planner.execute(state)

    assert result.decision == AgentDecision.CONTINUE
    assert result.next_agent_suggestion == "DataIngestionAgent"
```

### Integration Tests

Test agent interactions:

```python
@pytest.mark.asyncio
async def test_full_workflow():
    workflow = create_graph()
    initial_state = GraphState(input_dataset_path="test.csv")

    final_state = await workflow.ainvoke(initial_state)

    assert "ReportingAgent" in final_state.steps_completed
    assert final_state.get("report_markdown_path") is not None
```

---

## Conclusion

The 7-agent architecture provides:
- **Dynamic Orchestration**: Planner adapts to data
- **Quality Assurance**: Evaluator validates results
- **Resilience**: Retry loops and error handling
- **Observability**: Built-in logging everywhere
- **Flexibility**: Easy to add new agents

This is a **true graph workflow**, not a linear pipeline.

**Document Version**: 1.0 (Post-Architecture Review)
**Status**: Finalized