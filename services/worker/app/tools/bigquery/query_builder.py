"""SQL query builder for BigQuery."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
import re
from enum import Enum


class AggregationType(Enum):
    """Supported aggregation types."""
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    COUNT_DISTINCT = "COUNT(DISTINCT {})"


class JoinType(Enum):
    """Supported join types."""
    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"
    FULL = "FULL OUTER JOIN"


class QueryBuilder:
    """SQL query builder for BigQuery with safety features."""
    
    def __init__(self):
        """Initialize query builder."""
        self.reset()
    
    def reset(self) -> 'QueryBuilder':
        """Reset the query builder to initial state.
        
        Returns:
            Self for method chaining
        """
        self._select_fields: List[str] = []
        self._from_table: Optional[str] = None
        self._joins: List[str] = []
        self._where_conditions: List[str] = []
        self._group_by_fields: List[str] = []
        self._having_conditions: List[str] = []
        self._order_by_fields: List[str] = []
        self._limit_value: Optional[int] = None
        self._with_clauses: List[str] = []
        return self
    
    def select(self, *fields: str) -> 'QueryBuilder':
        """Add SELECT fields.
        
        Args:
            *fields: Field names or expressions
            
        Returns:
            Self for method chaining
        """
        for field in fields:
            if self._is_safe_identifier(field):
                self._select_fields.append(field)
            else:
                raise ValueError(f"Unsafe field identifier: {field}")
        return self
    
    def select_all(self) -> 'QueryBuilder':
        """Add SELECT * to query.
        
        Returns:
            Self for method chaining
        """
        self._select_fields.append("*")
        return self
    
    def aggregate(self, field: str, agg_type: AggregationType, alias: Optional[str] = None) -> 'QueryBuilder':
        """Add aggregation field.
        
        Args:
            field: Field name to aggregate
            agg_type: Type of aggregation
            alias: Optional alias for the aggregated field
            
        Returns:
            Self for method chaining
        """
        if not self._is_safe_identifier(field):
            raise ValueError(f"Unsafe field identifier: {field}")
        
        if agg_type == AggregationType.COUNT_DISTINCT:
            agg_expr = agg_type.value.format(field)
        else:
            agg_expr = f"{agg_type.value}({field})"
        
        if alias:
            if not self._is_safe_identifier(alias):
                raise ValueError(f"Unsafe alias: {alias}")
            agg_expr += f" AS {alias}"
        
        self._select_fields.append(agg_expr)
        return self
    
    def from_table(self, table: str) -> 'QueryBuilder':
        """Set FROM table.
        
        Args:
            table: Table name (can include dataset and project)
            
        Returns:
            Self for method chaining
        """
        if not self._is_safe_table_name(table):
            raise ValueError(f"Unsafe table name: {table}")
        
        self._from_table = table
        return self
    
    def join(self, table: str, condition: str, join_type: JoinType = JoinType.INNER) -> 'QueryBuilder':
        """Add JOIN clause.
        
        Args:
            table: Table to join
            condition: JOIN condition
            join_type: Type of join
            
        Returns:
            Self for method chaining
        """
        if not self._is_safe_table_name(table):
            raise ValueError(f"Unsafe table name: {table}")
        
        if not self._is_safe_condition(condition):
            raise ValueError(f"Unsafe join condition: {condition}")
        
        join_clause = f"{join_type.value} {table} ON {condition}"
        self._joins.append(join_clause)
        return self
    
    def where(self, condition: str) -> 'QueryBuilder':
        """Add WHERE condition.
        
        Args:
            condition: WHERE condition
            
        Returns:
            Self for method chaining
        """
        if not self._is_safe_condition(condition):
            raise ValueError(f"Unsafe WHERE condition: {condition}")
        
        self._where_conditions.append(condition)
        return self
    
    def where_in(self, field: str, values: List[Any]) -> 'QueryBuilder':
        """Add WHERE field IN (values) condition.
        
        Args:
            field: Field name
            values: List of values
            
        Returns:
            Self for method chaining
        """
        if not self._is_safe_identifier(field):
            raise ValueError(f"Unsafe field identifier: {field}")
        
        if not values:
            raise ValueError("Values list cannot be empty")
        
        # Format values based on type
        formatted_values = []
        for value in values:
            if isinstance(value, str):
                formatted_values.append(f"'{value.replace("'", "''")}'")  # Escape single quotes
            elif isinstance(value, (int, float)):
                formatted_values.append(str(value))
            elif isinstance(value, bool):
                formatted_values.append(str(value).upper())
            elif value is None:
                formatted_values.append("NULL")
            else:
                formatted_values.append(f"'{str(value).replace("'", "''")}'")  # Escape single quotes
        
        condition = f"{field} IN ({', '.join(formatted_values)})"
        self._where_conditions.append(condition)
        return self
    
    def where_between(self, field: str, start: Any, end: Any) -> 'QueryBuilder':
        """Add WHERE field BETWEEN start AND end condition.
        
        Args:
            field: Field name
            start: Start value
            end: End value
            
        Returns:
            Self for method chaining
        """
        if not self._is_safe_identifier(field):
            raise ValueError(f"Unsafe field identifier: {field}")
        
        start_val = self._format_value(start)
        end_val = self._format_value(end)
        
        condition = f"{field} BETWEEN {start_val} AND {end_val}"
        self._where_conditions.append(condition)
        return self
    
    def group_by(self, *fields: str) -> 'QueryBuilder':
        """Add GROUP BY fields.
        
        Args:
            *fields: Field names
            
        Returns:
            Self for method chaining
        """
        for field in fields:
            if self._is_safe_identifier(field):
                self._group_by_fields.append(field)
            else:
                raise ValueError(f"Unsafe field identifier: {field}")
        return self
    
    def having(self, condition: str) -> 'QueryBuilder':
        """Add HAVING condition.
        
        Args:
            condition: HAVING condition
            
        Returns:
            Self for method chaining
        """
        if not self._is_safe_condition(condition):
            raise ValueError(f"Unsafe HAVING condition: {condition}")
        
        self._having_conditions.append(condition)
        return self
    
    def order_by(self, field: str, desc: bool = False) -> 'QueryBuilder':
        """Add ORDER BY field.
        
        Args:
            field: Field name
            desc: Whether to sort in descending order
            
        Returns:
            Self for method chaining
        """
        if not self._is_safe_identifier(field):
            raise ValueError(f"Unsafe field identifier: {field}")
        
        order_expr = field
        if desc:
            order_expr += " DESC"
        
        self._order_by_fields.append(order_expr)
        return self
    
    def limit(self, count: int) -> 'QueryBuilder':
        """Add LIMIT clause.
        
        Args:
            count: Maximum number of rows to return
            
        Returns:
            Self for method chaining
        """
        if not isinstance(count, int) or count < 0:
            raise ValueError("Limit must be a non-negative integer")
        
        self._limit_value = count
        return self
    
    def with_clause(self, name: str, query: str) -> 'QueryBuilder':
        """Add WITH clause (CTE).
        
        Args:
            name: CTE name
            query: CTE query
            
        Returns:
            Self for method chaining
        """
        if not self._is_safe_identifier(name):
            raise ValueError(f"Unsafe CTE name: {name}")
        
        # Basic validation for the CTE query
        if not query.strip():
            raise ValueError("CTE query cannot be empty")
        
        cte = f"{name} AS ({query})"
        self._with_clauses.append(cte)
        return self
    
    def build(self) -> str:
        """Build the final SQL query.
        
        Returns:
            Complete SQL query string
            
        Raises:
            ValueError: If required components are missing
        """
        if not self._select_fields:
            raise ValueError("SELECT fields are required")
        
        if not self._from_table:
            raise ValueError("FROM table is required")
        
        query_parts = []
        
        # WITH clauses
        if self._with_clauses:
            query_parts.append(f"WITH {', '.join(self._with_clauses)}")
        
        # SELECT
        query_parts.append(f"SELECT {', '.join(self._select_fields)}")
        
        # FROM
        query_parts.append(f"FROM {self._from_table}")
        
        # JOINs
        if self._joins:
            query_parts.extend(self._joins)
        
        # WHERE
        if self._where_conditions:
            query_parts.append(f"WHERE {' AND '.join(self._where_conditions)}")
        
        # GROUP BY
        if self._group_by_fields:
            query_parts.append(f"GROUP BY {', '.join(self._group_by_fields)}")
        
        # HAVING
        if self._having_conditions:
            query_parts.append(f"HAVING {' AND '.join(self._having_conditions)}")
        
        # ORDER BY
        if self._order_by_fields:
            query_parts.append(f"ORDER BY {', '.join(self._order_by_fields)}")
        
        # LIMIT
        if self._limit_value is not None:
            query_parts.append(f"LIMIT {self._limit_value}")
        
        return '\n'.join(query_parts)
    
    def _is_safe_identifier(self, identifier: str) -> bool:
        """Check if identifier is safe (no SQL injection).
        
        Args:
            identifier: Identifier to check
            
        Returns:
            True if safe, False otherwise
        """
        # Allow alphanumeric, underscore, dot, and basic SQL functions
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_\.\(\)\s,]*$'
        return bool(re.match(pattern, identifier))
    
    def _is_safe_table_name(self, table_name: str) -> bool:
        """Check if table name is safe.
        
        Args:
            table_name: Table name to check
            
        Returns:
            True if safe, False otherwise
        """
        # Allow project.dataset.table format
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_\-]*(?:\.[a-zA-Z_][a-zA-Z0-9_\-]*){0,2}$'
        return bool(re.match(pattern, table_name))
    
    def _is_safe_condition(self, condition: str) -> bool:
        """Check if condition is safe.
        
        Args:
            condition: Condition to check
            
        Returns:
            True if safe, False otherwise
        """
        # Basic safety check - no dangerous keywords
        dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER', 
            'TRUNCATE', 'EXEC', 'EXECUTE', 'UNION', 'SCRIPT'
        ]
        
        condition_upper = condition.upper()
        for keyword in dangerous_keywords:
            if keyword in condition_upper:
                return False
        
        return True
    
    def _format_value(self, value: Any) -> str:
        """Format a value for SQL.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted SQL value
        """
        if isinstance(value, str):
            return f"'{value.replace("'", "''")}'"	# Escape single quotes
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, bool):
            return str(value).upper()
        elif isinstance(value, (datetime, date)):
            return f"'{value.isoformat()}'"
        elif value is None:
            return "NULL"
        else:
            return f"'{str(value).replace("'", "''")}'"	  # Escape single quotes


# Alias for backward compatibility
BigQueryQueryBuilder = QueryBuilder