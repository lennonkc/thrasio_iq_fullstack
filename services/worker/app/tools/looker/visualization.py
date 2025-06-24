"""Visualization configuration and management for Looker."""

from typing import Any, Dict, List, Optional, Union
from enum import Enum
import structlog
from dataclasses import dataclass, field

from .client import LookerClient, LookerAPIError


class ChartType(Enum):
    """Supported chart types in Looker."""
    LINE = "line"
    BAR = "column"
    AREA = "area"
    PIE = "pie"
    SCATTER = "scatter"
    TABLE = "looker_table"
    SINGLE_VALUE = "single_value"
    FUNNEL = "funnel"
    WATERFALL = "waterfall"
    HEATMAP = "looker_grid"
    MAP = "looker_map"
    TIMELINE = "timeline"


class AggregateFunction(Enum):
    """Aggregate functions for measures."""
    SUM = "sum"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    PERCENTILE = "percentile"


@dataclass
class QueryField:
    """Represents a field in a Looker query."""
    name: str
    type: str  # "dimension" or "measure"
    label: Optional[str] = None
    
    def to_api_format(self) -> str:
        """Convert to API format.
        
        Returns:
            Field name in API format
        """
        return self.name


@dataclass
class VisualizationConfig:
    """Configuration for a Looker visualization."""
    chart_type: ChartType
    title: Optional[str] = None
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None
    show_legend: bool = True
    show_grid: bool = True
    color_palette: Optional[List[str]] = None
    custom_config: Dict[str, Any] = field(default_factory=dict)
    
    def to_looker_config(self) -> Dict[str, Any]:
        """Convert to Looker visualization configuration.
        
        Returns:
            Looker visualization config dictionary
        """
        config = {
            "type": self.chart_type.value,
            "show_view_names": False,
            "show_row_numbers": True,
            "transpose": False,
            "truncate_text": True,
            "hide_totals": False,
            "hide_row_totals": False,
            "size_to_fit": True,
            "table_theme": "white",
            "limit_displayed_rows": False,
            "enable_conditional_formatting": False,
            "header_text_alignment": "left",
            "header_font_size": 12,
            "rows_font_size": 12
        }
        
        # Chart-specific configurations
        if self.chart_type in [ChartType.LINE, ChartType.BAR, ChartType.AREA]:
            config.update({
                "x_axis_gridlines": self.show_grid,
                "y_axis_gridlines": self.show_grid,
                "show_y_axis_labels": True,
                "show_y_axis_ticks": True,
                "y_axis_tick_density": "default",
                "y_axis_tick_density_custom": 5,
                "show_x_axis_label": bool(self.x_axis_label),
                "show_x_axis_ticks": True,
                "y_axis_scale_mode": "linear",
                "x_axis_reversed": False,
                "y_axis_reversed": False,
                "plot_size_by_field": False,
                "trellis": "",
                "stacking": "",
                "legend_position": "center" if self.show_legend else "off",
                "point_style": "none",
                "show_value_labels": False,
                "label_density": 25,
                "x_axis_scale": "auto",
                "y_axis_combined": True,
                "ordering": "none",
                "show_null_labels": False,
                "show_totals_labels": False,
                "show_silhouette": False,
                "totals_color": "#808080"
            })
            
            if self.x_axis_label:
                config["x_axis_label"] = self.x_axis_label
            if self.y_axis_label:
                config["y_axis_label"] = self.y_axis_label
        
        elif self.chart_type == ChartType.PIE:
            config.update({
                "pie_inner_radius": 0,
                "legend_position": "center" if self.show_legend else "off",
                "show_value_labels": True,
                "label_type": "labPer",
                "inner_radius": 0
            })
        
        elif self.chart_type == ChartType.SINGLE_VALUE:
            config.update({
                "single_value_title": self.title or "",
                "value_format": "",
                "font_size": "medium",
                "text_color": "#3a4245"
            })
        
        elif self.chart_type == ChartType.TABLE:
            config.update({
                "show_view_names": False,
                "show_row_numbers": True,
                "transpose": False,
                "truncate_text": True,
                "hide_totals": False,
                "hide_row_totals": False,
                "size_to_fit": True,
                "table_theme": "white",
                "limit_displayed_rows": False,
                "enable_conditional_formatting": False
            })
        
        # Apply color palette if provided
        if self.color_palette:
            config["color_application"] = {
                "collection_id": "custom",
                "palette_id": "custom",
                "options": {
                    "steps": len(self.color_palette),
                    "reverse": False
                },
                "custom": {
                    "colors": self.color_palette
                }
            }
        
        # Apply custom configuration overrides
        config.update(self.custom_config)
        
        return config


class VisualizationManager:
    """Manages Looker visualizations and queries."""
    
    def __init__(self, looker_client: LookerClient):
        """Initialize visualization manager.
        
        Args:
            looker_client: Looker client instance
        """
        self.client = looker_client
        self.logger = structlog.get_logger()
    
    async def create_query(
        self,
        model: str,
        explore: str,
        dimensions: List[str],
        measures: List[str],
        filters: Optional[Dict[str, str]] = None,
        sorts: Optional[List[str]] = None,
        limit: Optional[int] = None,
        row_total: bool = False
    ) -> Dict[str, Any]:
        """Create a new query in Looker.
        
        Args:
            model: LookML model name
            explore: Explore name
            dimensions: List of dimension field names
            measures: List of measure field names
            filters: Optional filters dictionary
            sorts: Optional list of sort specifications
            limit: Optional row limit
            row_total: Whether to include row totals
            
        Returns:
            Created query object
            
        Raises:
            LookerAPIError: If query creation fails
        """
        try:
            query_data = {
                "model": model,
                "explore": explore,
                "dimensions": dimensions,
                "measures": measures,
                "row_total": row_total
            }
            
            if filters:
                query_data["filters"] = filters
            
            if sorts:
                query_data["sorts"] = sorts
            
            if limit:
                query_data["limit"] = str(limit)
            
            query = await self.client._make_request(
                "POST",
                "/queries",
                data=query_data
            )
            
            self.logger.info(
                "Created query",
                query_id=query.get("id"),
                model=model,
                explore=explore,
                dimensions=len(dimensions),
                measures=len(measures)
            )
            
            return query
            
        except LookerAPIError as e:
            self.logger.error(
                "Failed to create query",
                error=str(e),
                model=model,
                explore=explore
            )
            raise
    
    async def create_visualization(
        self,
        query_id: str,
        config: VisualizationConfig
    ) -> Dict[str, Any]:
        """Create a visualization for a query.
        
        Args:
            query_id: Query ID
            config: Visualization configuration
            
        Returns:
            Visualization object
        """
        try:
            # Get the query to update it with visualization config
            query = await self.client._make_request("GET", f"/queries/{query_id}")
            
            # Update query with visualization configuration
            vis_config = config.to_looker_config()
            query["vis_config"] = vis_config
            
            # Update the query
            updated_query = await self.client._make_request(
                "PUT",
                f"/queries/{query_id}",
                data=query
            )
            
            self.logger.info(
                "Created visualization",
                query_id=query_id,
                chart_type=config.chart_type.value
            )
            
            return updated_query
            
        except LookerAPIError as e:
            self.logger.error(
                "Failed to create visualization",
                error=str(e),
                query_id=query_id
            )
            raise
    
    async def create_chart_from_data(
        self,
        model: str,
        explore: str,
        chart_type: ChartType,
        dimensions: List[str],
        measures: List[str],
        title: Optional[str] = None,
        filters: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
        color_palette: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a complete chart with query and visualization.
        
        Args:
            model: LookML model name
            explore: Explore name
            chart_type: Type of chart to create
            dimensions: List of dimension field names
            measures: List of measure field names
            title: Optional chart title
            filters: Optional filters
            limit: Optional row limit
            color_palette: Optional color palette
            
        Returns:
            Complete query object with visualization
        """
        try:
            # Create the query
            query = await self.create_query(
                model=model,
                explore=explore,
                dimensions=dimensions,
                measures=measures,
                filters=filters,
                limit=limit
            )
            
            # Create visualization configuration
            vis_config = VisualizationConfig(
                chart_type=chart_type,
                title=title,
                color_palette=color_palette
            )
            
            # Apply visualization to query
            chart = await self.create_visualization(query["id"], vis_config)
            
            self.logger.info(
                "Created complete chart",
                query_id=query["id"],
                chart_type=chart_type.value,
                title=title
            )
            
            return chart
            
        except LookerAPIError as e:
            self.logger.error(
                "Failed to create chart",
                error=str(e),
                model=model,
                explore=explore,
                chart_type=chart_type.value
            )
            raise
    
    async def get_chart_data(
        self,
        query_id: str,
        format: str = "json",
        limit: Optional[int] = None
    ) -> Any:
        """Get data for a chart.
        
        Args:
            query_id: Query ID
            format: Data format (json, csv, etc.)
            limit: Optional row limit
            
        Returns:
            Chart data in specified format
        """
        try:
            data = await self.client.run_query(
                query_id=query_id,
                result_format=format,
                limit=limit
            )
            
            self.logger.info(
                "Retrieved chart data",
                query_id=query_id,
                format=format
            )
            
            return data
            
        except LookerAPIError as e:
            self.logger.error(
                "Failed to get chart data",
                error=str(e),
                query_id=query_id
            )
            raise
    
    def get_recommended_chart_type(
        self,
        dimensions: List[str],
        measures: List[str],
        data_sample: Optional[List[Dict[str, Any]]] = None
    ) -> ChartType:
        """Recommend a chart type based on data characteristics.
        
        Args:
            dimensions: List of dimensions
            measures: List of measures
            data_sample: Optional sample of data
            
        Returns:
            Recommended ChartType
        """
        num_dimensions = len(dimensions)
        num_measures = len(measures)
        
        # Single value
        if num_dimensions == 0 and num_measures == 1:
            return ChartType.SINGLE_VALUE
        
        # Table for complex data
        if num_dimensions > 2 or num_measures > 3:
            return ChartType.TABLE
        
        # Pie chart for single dimension with single measure
        if num_dimensions == 1 and num_measures == 1:
            # Check if dimension has limited categories
            return ChartType.PIE
        
        # Line chart for time series
        if num_dimensions == 1:
            # Check if dimension looks like a date
            dim_name = dimensions[0].lower()
            if any(word in dim_name for word in ['date', 'time', 'month', 'year', 'day']):
                return ChartType.LINE
        
        # Bar chart as default for categorical data
        if num_dimensions <= 2 and num_measures <= 2:
            return ChartType.BAR
        
        # Default to table
        return ChartType.TABLE
    
    def get_color_palette(self, palette_name: str = "default") -> List[str]:
        """Get a predefined color palette.
        
        Args:
            palette_name: Name of the palette
            
        Returns:
            List of color hex codes
        """
        palettes = {
            "default": [
                "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
            ],
            "blue": [
                "#08519c", "#3182bd", "#6baed6", "#9ecae1", "#c6dbef"
            ],
            "green": [
                "#00441b", "#238b45", "#66c2a4", "#abdda4", "#e5f5f9"
            ],
            "red": [
                "#67000d", "#a50f15", "#cb181d", "#ef3b2c", "#fb6a4a"
            ],
            "purple": [
                "#3f007d", "#54278f", "#756bb1", "#9e9ac8", "#cbc9e2"
            ]
        }
        
        return palettes.get(palette_name, palettes["default"])