"""Data analysis workflow using LangGraph."""

from typing import Any, Dict, List, Optional, TypedDict, Annotated
import json
import structlog
from datetime import datetime
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field

from ..tools.bigquery import BigQueryClient, QueryBuilder, SchemaManager
from ..tools.looker import LookerClient, VisualizationManager, ChartType


class AnalysisStep(Enum):
    """Analysis workflow steps."""
    INTENT_UNDERSTANDING = "intent_understanding"
    SCHEMA_RETRIEVAL = "schema_retrieval"
    SQL_GENERATION = "sql_generation"
    QUERY_EXECUTION = "query_execution"
    VISUALIZATION_CREATION = "visualization_creation"
    RESPONSE_FORMATTING = "response_formatting"
    ERROR_HANDLING = "error_handling"


class AnalysisIntent(BaseModel):
    """Represents the user's analysis intent."""
    intent_type: str  # "query", "visualization", "dashboard", "exploration"
    entities: List[str] = Field(default_factory=list)  # Tables, fields mentioned
    metrics: List[str] = Field(default_factory=list)  # Requested metrics
    dimensions: List[str] = Field(default_factory=list)  # Grouping dimensions
    filters: Dict[str, Any] = Field(default_factory=dict)  # Filter conditions
    time_range: Optional[Dict[str, str]] = None  # Time range if specified
    visualization_type: Optional[str] = None  # Requested chart type
    confidence: float = 0.0  # Confidence in intent understanding


class AnalysisState(TypedDict):
    """State for the data analysis workflow."""
    # Input
    user_query: str
    user_id: str
    session_id: str
    
    # Intent understanding
    intent: Optional[AnalysisIntent]
    
    # Schema information
    relevant_schemas: List[Dict[str, Any]]
    selected_tables: List[str]
    
    # SQL generation
    generated_sql: Optional[str]
    sql_explanation: Optional[str]
    
    # Query execution
    query_results: Optional[Dict[str, Any]]
    execution_error: Optional[str]
    
    # Visualization
    visualization_config: Optional[Dict[str, Any]]
    chart_url: Optional[str]
    
    # Response
    final_response: Optional[str]
    
    # Workflow state
    current_step: str
    error_count: int
    messages: List[BaseMessage]
    metadata: Dict[str, Any]


class DataAnalysisWorkflow:
    """LangGraph workflow for data analysis tasks."""
    
    def __init__(
        self,
        bigquery_client: BigQueryClient,
        looker_client: LookerClient,
        llm_client: Any,  # LLM client (e.g., Vertex AI)
        project_id: str
    ):
        """Initialize the workflow.
        
        Args:
            bigquery_client: BigQuery client
            looker_client: Looker client
            llm_client: LLM client for text generation
            project_id: Google Cloud project ID
        """
        self.bigquery_client = bigquery_client
        self.looker_client = looker_client
        self.llm_client = llm_client
        self.project_id = project_id
        
        self.schema_manager = SchemaManager(bigquery_client)
        self.viz_manager = VisualizationManager(looker_client)
        self.query_builder = QueryBuilder()
        
        self.logger = structlog.get_logger()
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow.
        
        Returns:
            Configured StateGraph
        """
        workflow = StateGraph(AnalysisState)
        
        # Add nodes
        workflow.add_node("intent_understanding", self._understand_intent)
        workflow.add_node("schema_retrieval", self._retrieve_schemas)
        workflow.add_node("sql_generation", self._generate_sql)
        workflow.add_node("query_execution", self._execute_query)
        workflow.add_node("visualization_creation", self._create_visualization)
        workflow.add_node("response_formatting", self._format_response)
        workflow.add_node("error_handling", self._handle_error)
        
        # Set entry point
        workflow.set_entry_point("intent_understanding")
        
        # Add edges
        workflow.add_edge("intent_understanding", "schema_retrieval")
        workflow.add_edge("schema_retrieval", "sql_generation")
        workflow.add_edge("sql_generation", "query_execution")
        workflow.add_edge("query_execution", "visualization_creation")
        workflow.add_edge("visualization_creation", "response_formatting")
        workflow.add_edge("response_formatting", END)
        
        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "intent_understanding",
            self._should_handle_error,
            {
                "error": "error_handling",
                "continue": "schema_retrieval"
            }
        )
        
        workflow.add_conditional_edges(
            "sql_generation",
            self._should_handle_error,
            {
                "error": "error_handling",
                "continue": "query_execution"
            }
        )
        
        workflow.add_conditional_edges(
            "query_execution",
            self._should_handle_error,
            {
                "error": "error_handling",
                "continue": "visualization_creation"
            }
        )
        
        workflow.add_edge("error_handling", "response_formatting")
        
        return workflow.compile()
    
    async def _understand_intent(self, state: AnalysisState) -> AnalysisState:
        """Understand user intent from the query.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with intent information
        """
        try:
            self.logger.info("Understanding user intent", query=state["user_query"])
            
            # Prepare prompt for LLM
            prompt = f"""
            Analyze the following user query and extract the analysis intent:
            
            Query: "{state['user_query']}"
            
            Extract:
            1. Intent type (query, visualization, dashboard, exploration)
            2. Entities mentioned (table names, field names)
            3. Metrics requested (what to measure)
            4. Dimensions (how to group/break down data)
            5. Filters (any conditions)
            6. Time range (if specified)
            7. Visualization type (if requested)
            
            Return as JSON with the following structure:
            {{
                "intent_type": "query|visualization|dashboard|exploration",
                "entities": ["list of entities"],
                "metrics": ["list of metrics"],
                "dimensions": ["list of dimensions"],
                "filters": {{"field": "value"}},
                "time_range": {{"start": "date", "end": "date"}},
                "visualization_type": "chart_type",
                "confidence": 0.8
            }}
            """
            
            # Call LLM (this would be implemented with actual LLM client)
            # For now, we'll create a basic intent parser
            intent = self._parse_intent_basic(state["user_query"])
            
            state["intent"] = intent
            state["current_step"] = AnalysisStep.INTENT_UNDERSTANDING.value
            state["messages"].append(
                AIMessage(content=f"Understood intent: {intent.intent_type}")
            )
            
            self.logger.info(
                "Intent understood",
                intent_type=intent.intent_type,
                confidence=intent.confidence
            )
            
        except Exception as e:
            self.logger.error("Intent understanding failed", error=str(e))
            state["execution_error"] = f"Intent understanding failed: {str(e)}"
            state["error_count"] += 1
        
        return state
    
    async def _retrieve_schemas(self, state: AnalysisState) -> AnalysisState:
        """Retrieve relevant schemas based on intent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with schema information
        """
        try:
            self.logger.info("Retrieving relevant schemas")
            
            intent = state["intent"]
            if not intent:
                raise ValueError("No intent found")
            
            relevant_schemas = []
            
            # Search for schemas based on entities mentioned
            for entity in intent.entities:
                try:
                    # Search by field name
                    schemas = await self.schema_manager.search_tables_by_field(entity)
                    relevant_schemas.extend([schema.to_dict() for schema in schemas])
                    
                    # Search by description
                    desc_schemas = await self.schema_manager.search_tables_by_description(entity)
                    relevant_schemas.extend([schema.to_dict() for schema in desc_schemas])
                    
                except Exception as e:
                    self.logger.warning(f"Schema search failed for entity {entity}", error=str(e))
            
            # Remove duplicates
            unique_schemas = []
            seen_tables = set()
            for schema in relevant_schemas:
                table_key = f"{schema['dataset_id']}.{schema['table_id']}"
                if table_key not in seen_tables:
                    unique_schemas.append(schema)
                    seen_tables.add(table_key)
            
            state["relevant_schemas"] = unique_schemas
            state["selected_tables"] = list(seen_tables)
            state["current_step"] = AnalysisStep.SCHEMA_RETRIEVAL.value
            
            self.logger.info(
                "Schemas retrieved",
                schema_count=len(unique_schemas),
                tables=list(seen_tables)
            )
            
        except Exception as e:
            self.logger.error("Schema retrieval failed", error=str(e))
            state["execution_error"] = f"Schema retrieval failed: {str(e)}"
            state["error_count"] += 1
        
        return state
    
    async def _generate_sql(self, state: AnalysisState) -> AnalysisState:
        """Generate SQL query based on intent and schemas.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with generated SQL
        """
        try:
            self.logger.info("Generating SQL query")
            
            intent = state["intent"]
            schemas = state["relevant_schemas"]
            
            if not intent or not schemas:
                raise ValueError("Missing intent or schemas")
            
            # For now, use a simple SQL generation approach
            # In production, this would use LLM with schema context
            sql_query = self._generate_sql_basic(intent, schemas)
            
            state["generated_sql"] = sql_query
            state["sql_explanation"] = f"Generated query to analyze {intent.intent_type}"
            state["current_step"] = AnalysisStep.SQL_GENERATION.value
            
            self.logger.info("SQL generated", query_length=len(sql_query))
            
        except Exception as e:
            self.logger.error("SQL generation failed", error=str(e))
            state["execution_error"] = f"SQL generation failed: {str(e)}"
            state["error_count"] += 1
        
        return state
    
    async def _execute_query(self, state: AnalysisState) -> AnalysisState:
        """Execute the generated SQL query.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with query results
        """
        try:
            self.logger.info("Executing SQL query")
            
            sql_query = state["generated_sql"]
            if not sql_query:
                raise ValueError("No SQL query to execute")
            
            # Execute query with BigQuery
            df = await self.bigquery_client.execute_query(
                query=sql_query,
                timeout=60.0,
                max_results=1000
            )
            
            # Convert results to dictionary format
            results = {
                "data": df.to_dict("records"),
                "columns": df.columns.tolist(),
                "row_count": len(df),
                "execution_time": datetime.utcnow().isoformat()
            }
            
            state["query_results"] = results
            state["current_step"] = AnalysisStep.QUERY_EXECUTION.value
            
            self.logger.info(
                "Query executed successfully",
                row_count=len(df),
                columns=len(df.columns)
            )
            
        except Exception as e:
            self.logger.error("Query execution failed", error=str(e))
            state["execution_error"] = f"Query execution failed: {str(e)}"
            state["error_count"] += 1
        
        return state
    
    async def _create_visualization(self, state: AnalysisState) -> AnalysisState:
        """Create visualization if requested.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with visualization information
        """
        try:
            self.logger.info("Creating visualization")
            
            intent = state["intent"]
            results = state["query_results"]
            
            if not intent or not results:
                # Skip visualization if no intent or results
                state["current_step"] = AnalysisStep.VISUALIZATION_CREATION.value
                return state
            
            # Only create visualization if requested
            if intent.intent_type in ["visualization", "dashboard"]:
                # Determine chart type
                chart_type = self._determine_chart_type(intent, results)
                
                # Create visualization config
                viz_config = {
                    "chart_type": chart_type.value,
                    "title": f"Analysis: {state['user_query'][:50]}...",
                    "data": results["data"][:100],  # Limit data for visualization
                    "columns": results["columns"]
                }
                
                state["visualization_config"] = viz_config
                # In production, this would create actual Looker visualization
                state["chart_url"] = f"https://looker.example.com/chart/{datetime.utcnow().timestamp()}"
            
            state["current_step"] = AnalysisStep.VISUALIZATION_CREATION.value
            
            self.logger.info("Visualization created")
            
        except Exception as e:
            self.logger.error("Visualization creation failed", error=str(e))
            # Don't fail the workflow for visualization errors
            state["current_step"] = AnalysisStep.VISUALIZATION_CREATION.value
        
        return state
    
    async def _format_response(self, state: AnalysisState) -> AnalysisState:
        """Format the final response.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with formatted response
        """
        try:
            self.logger.info("Formatting response")
            
            response_parts = []
            
            # Add query results summary
            if state["query_results"]:
                results = state["query_results"]
                response_parts.append(
                    f"Query executed successfully. Found {results['row_count']} rows."
                )
                
                # Add sample data
                if results["data"]:
                    response_parts.append("\nSample results:")
                    sample_data = results["data"][:5]  # First 5 rows
                    for i, row in enumerate(sample_data, 1):
                        response_parts.append(f"{i}. {row}")
            
            # Add visualization info
            if state["chart_url"]:
                response_parts.append(f"\nVisualization created: {state['chart_url']}")
            
            # Add SQL query if requested
            if state["generated_sql"]:
                response_parts.append(f"\nSQL Query:\n```sql\n{state['generated_sql']}\n```")
            
            # Handle errors
            if state["execution_error"]:
                response_parts.append(f"\nError: {state['execution_error']}")
            
            final_response = "\n".join(response_parts)
            state["final_response"] = final_response
            state["current_step"] = AnalysisStep.RESPONSE_FORMATTING.value
            
            self.logger.info("Response formatted", response_length=len(final_response))
            
        except Exception as e:
            self.logger.error("Response formatting failed", error=str(e))
            state["final_response"] = f"Analysis completed with errors: {str(e)}"
        
        return state
    
    async def _handle_error(self, state: AnalysisState) -> AnalysisState:
        """Handle errors in the workflow.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with error handling
        """
        self.logger.info("Handling workflow error", error=state.get("execution_error"))
        
        state["current_step"] = AnalysisStep.ERROR_HANDLING.value
        
        # Add error message to response
        error_msg = state.get("execution_error", "Unknown error occurred")
        state["final_response"] = f"I encountered an error while processing your request: {error_msg}"
        
        return state
    
    def _should_handle_error(self, state: AnalysisState) -> str:
        """Determine if error handling is needed.
        
        Args:
            state: Current workflow state
            
        Returns:
            "error" if error handling needed, "continue" otherwise
        """
        if state.get("execution_error") or state.get("error_count", 0) > 0:
            return "error"
        return "continue"
    
    def _parse_intent_basic(self, query: str) -> AnalysisIntent:
        """Basic intent parsing (placeholder for LLM-based parsing).
        
        Args:
            query: User query
            
        Returns:
            Parsed AnalysisIntent
        """
        query_lower = query.lower()
        
        # Determine intent type
        if any(word in query_lower for word in ["chart", "graph", "plot", "visualize"]):
            intent_type = "visualization"
        elif any(word in query_lower for word in ["dashboard", "report"]):
            intent_type = "dashboard"
        elif any(word in query_lower for word in ["explore", "analyze", "investigate"]):
            intent_type = "exploration"
        else:
            intent_type = "query"
        
        # Extract basic entities (this would be much more sophisticated with LLM)
        entities = []
        common_tables = ["sales", "users", "orders", "products", "customers"]
        for table in common_tables:
            if table in query_lower:
                entities.append(table)
        
        return AnalysisIntent(
            intent_type=intent_type,
            entities=entities,
            confidence=0.7  # Basic confidence score
        )
    
    def _generate_sql_basic(self, intent: AnalysisIntent, schemas: List[Dict[str, Any]]) -> str:
        """Basic SQL generation (placeholder for LLM-based generation).
        
        Args:
            intent: Analysis intent
            schemas: Available schemas
            
        Returns:
            Generated SQL query
        """
        if not schemas:
            return "SELECT 1 as sample_query"
        
        # Use first available schema
        schema = schemas[0]
        table_name = f"{schema['dataset_id']}.{schema['table_id']}"
        
        # Build basic query
        self.query_builder.reset()
        self.query_builder.select_all().from_table(table_name).limit(100)
        
        return self.query_builder.build()
    
    def _determine_chart_type(self, intent: AnalysisIntent, results: Dict[str, Any]) -> ChartType:
        """Determine appropriate chart type.
        
        Args:
            intent: Analysis intent
            results: Query results
            
        Returns:
            Recommended ChartType
        """
        if intent.visualization_type:
            # Map user request to chart type
            type_mapping = {
                "bar": ChartType.BAR,
                "line": ChartType.LINE,
                "pie": ChartType.PIE,
                "table": ChartType.TABLE
            }
            return type_mapping.get(intent.visualization_type.lower(), ChartType.TABLE)
        
        # Default recommendation based on data
        columns = results.get("columns", [])
        if len(columns) <= 2:
            return ChartType.BAR
        else:
            return ChartType.TABLE
    
    async def run_analysis(self, user_query: str, user_id: str, session_id: str) -> Dict[str, Any]:
        """Run the complete data analysis workflow.
        
        Args:
            user_query: User's analysis request
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Analysis results
        """
        # Initialize state
        initial_state = AnalysisState(
            user_query=user_query,
            user_id=user_id,
            session_id=session_id,
            intent=None,
            relevant_schemas=[],
            selected_tables=[],
            generated_sql=None,
            sql_explanation=None,
            query_results=None,
            execution_error=None,
            visualization_config=None,
            chart_url=None,
            final_response=None,
            current_step="",
            error_count=0,
            messages=[HumanMessage(content=user_query)],
            metadata={"start_time": datetime.utcnow().isoformat()}
        )
        
        try:
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Return results
            return {
                "success": final_state.get("execution_error") is None,
                "response": final_state.get("final_response"),
                "sql_query": final_state.get("generated_sql"),
                "results": final_state.get("query_results"),
                "visualization": final_state.get("visualization_config"),
                "chart_url": final_state.get("chart_url"),
                "metadata": {
                    "intent": final_state.get("intent"),
                    "schemas_used": final_state.get("selected_tables"),
                    "steps_completed": final_state.get("current_step"),
                    "error_count": final_state.get("error_count", 0)
                }
            }
            
        except Exception as e:
            self.logger.error("Workflow execution failed", error=str(e))
            return {
                "success": False,
                "response": f"Analysis failed: {str(e)}",
                "error": str(e)
            }