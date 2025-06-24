"""Dashboard management for Looker."""

from typing import Any, Dict, List, Optional, Union
import structlog
from dataclasses import dataclass
from datetime import datetime

from .client import LookerClient, LookerAPIError


@dataclass
class DashboardElement:
    """Represents a dashboard element (tile)."""
    id: str
    type: str
    title: Optional[str]
    subtitle: Optional[str]
    query_id: Optional[str]
    look_id: Optional[str]
    body_text: Optional[str]
    row: int
    col: int
    width: int
    height: int
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'DashboardElement':
        """Create DashboardElement from API response.
        
        Args:
            data: API response data
            
        Returns:
            DashboardElement instance
        """
        return cls(
            id=data.get("id", ""),
            type=data.get("type", ""),
            title=data.get("title"),
            subtitle=data.get("subtitle"),
            query_id=data.get("query_id"),
            look_id=data.get("look_id"),
            body_text=data.get("body_text"),
            row=data.get("row", 0),
            col=data.get("col", 0),
            width=data.get("width", 1),
            height=data.get("height", 1)
        )
    
    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API dictionary format.
        
        Returns:
            Dictionary for API requests
        """
        data = {
            "type": self.type,
            "row": self.row,
            "col": self.col,
            "width": self.width,
            "height": self.height
        }
        
        if self.title:
            data["title"] = self.title
        if self.subtitle:
            data["subtitle"] = self.subtitle
        if self.query_id:
            data["query_id"] = self.query_id
        if self.look_id:
            data["look_id"] = self.look_id
        if self.body_text:
            data["body_text"] = self.body_text
        
        return data


@dataclass
class Dashboard:
    """Represents a Looker dashboard."""
    id: str
    title: str
    description: Optional[str]
    space_id: str
    user_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    elements: List[DashboardElement]
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'Dashboard':
        """Create Dashboard from API response.
        
        Args:
            data: API response data
            
        Returns:
            Dashboard instance
        """
        elements = []
        if "dashboard_elements" in data:
            elements = [
                DashboardElement.from_api_response(elem)
                for elem in data["dashboard_elements"]
            ]
        
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            except ValueError:
                pass
        
        updated_at = None
        if data.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            except ValueError:
                pass
        
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description"),
            space_id=data.get("space_id", ""),
            user_id=data.get("user_id"),
            created_at=created_at,
            updated_at=updated_at,
            elements=elements
        )


class DashboardManager:
    """Manages Looker dashboards and their elements."""
    
    def __init__(self, looker_client: LookerClient):
        """Initialize dashboard manager.
        
        Args:
            looker_client: Looker client instance
        """
        self.client = looker_client
        self.logger = structlog.get_logger()
    
    async def create_dashboard(
        self, 
        title: str, 
        space_id: str,
        description: Optional[str] = None,
        elements: Optional[List[DashboardElement]] = None
    ) -> Dashboard:
        """Create a new dashboard with optional elements.
        
        Args:
            title: Dashboard title
            space_id: Space ID where dashboard will be created
            description: Optional dashboard description
            elements: Optional list of dashboard elements
            
        Returns:
            Created Dashboard object
            
        Raises:
            LookerAPIError: If dashboard creation fails
        """
        try:
            # Create the dashboard
            dashboard_data = await self.client.create_dashboard(
                title=title,
                space_id=space_id,
                description=description
            )
            
            dashboard = Dashboard.from_api_response(dashboard_data)
            
            # Add elements if provided
            if elements:
                for element in elements:
                    await self.add_element_to_dashboard(dashboard.id, element)
                
                # Refresh dashboard to get updated elements
                dashboard = await self.get_dashboard(dashboard.id)
            
            self.logger.info(
                "Created dashboard",
                dashboard_id=dashboard.id,
                title=title,
                element_count=len(elements) if elements else 0
            )
            
            return dashboard
            
        except LookerAPIError as e:
            self.logger.error(
                "Failed to create dashboard",
                error=str(e),
                title=title
            )
            raise
    
    async def get_dashboard(self, dashboard_id: str) -> Dashboard:
        """Get dashboard with all elements.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            Dashboard object
            
        Raises:
            LookerAPIError: If dashboard retrieval fails
        """
        try:
            dashboard_data = await self.client.get_dashboard(dashboard_id)
            dashboard = Dashboard.from_api_response(dashboard_data)
            
            self.logger.info(
                "Retrieved dashboard",
                dashboard_id=dashboard_id,
                element_count=len(dashboard.elements)
            )
            
            return dashboard
            
        except LookerAPIError as e:
            self.logger.error(
                "Failed to get dashboard",
                error=str(e),
                dashboard_id=dashboard_id
            )
            raise
    
    async def list_dashboards(self, space_id: Optional[str] = None) -> List[Dashboard]:
        """List dashboards, optionally filtered by space.
        
        Args:
            space_id: Optional space ID to filter dashboards
            
        Returns:
            List of Dashboard objects
        """
        try:
            dashboards_data = await self.client.list_dashboards(space_id=space_id)
            dashboards = [
                Dashboard.from_api_response(data) 
                for data in dashboards_data
            ]
            
            self.logger.info(
                "Listed dashboards",
                count=len(dashboards),
                space_id=space_id
            )
            
            return dashboards
            
        except LookerAPIError as e:
            self.logger.error(
                "Failed to list dashboards",
                error=str(e),
                space_id=space_id
            )
            raise
    
    async def update_dashboard(
        self, 
        dashboard_id: str, 
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dashboard:
        """Update dashboard metadata.
        
        Args:
            dashboard_id: Dashboard ID
            title: Optional new title
            description: Optional new description
            
        Returns:
            Updated Dashboard object
        """
        try:
            updates = {}
            if title is not None:
                updates["title"] = title
            if description is not None:
                updates["description"] = description
            
            if not updates:
                # No updates, just return current dashboard
                return await self.get_dashboard(dashboard_id)
            
            dashboard_data = await self.client.update_dashboard(dashboard_id, updates)
            dashboard = Dashboard.from_api_response(dashboard_data)
            
            self.logger.info(
                "Updated dashboard",
                dashboard_id=dashboard_id,
                updates=list(updates.keys())
            )
            
            return dashboard
            
        except LookerAPIError as e:
            self.logger.error(
                "Failed to update dashboard",
                error=str(e),
                dashboard_id=dashboard_id
            )
            raise
    
    async def delete_dashboard(self, dashboard_id: str) -> None:
        """Delete a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
        """
        try:
            await self.client.delete_dashboard(dashboard_id)
            
            self.logger.info("Deleted dashboard", dashboard_id=dashboard_id)
            
        except LookerAPIError as e:
            self.logger.error(
                "Failed to delete dashboard",
                error=str(e),
                dashboard_id=dashboard_id
            )
            raise
    
    async def add_element_to_dashboard(
        self, 
        dashboard_id: str, 
        element: DashboardElement
    ) -> DashboardElement:
        """Add an element to a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            element: Dashboard element to add
            
        Returns:
            Created DashboardElement
        """
        try:
            element_data = await self.client._make_request(
                "POST",
                f"/dashboard_elements",
                data={
                    "dashboard_id": dashboard_id,
                    **element.to_api_dict()
                }
            )
            
            created_element = DashboardElement.from_api_response(element_data)
            
            self.logger.info(
                "Added element to dashboard",
                dashboard_id=dashboard_id,
                element_id=created_element.id,
                element_type=created_element.type
            )
            
            return created_element
            
        except LookerAPIError as e:
            self.logger.error(
                "Failed to add element to dashboard",
                error=str(e),
                dashboard_id=dashboard_id
            )
            raise
    
    async def update_dashboard_element(
        self, 
        element_id: str, 
        updates: Dict[str, Any]
    ) -> DashboardElement:
        """Update a dashboard element.
        
        Args:
            element_id: Element ID
            updates: Dictionary of updates
            
        Returns:
            Updated DashboardElement
        """
        try:
            element_data = await self.client._make_request(
                "PUT",
                f"/dashboard_elements/{element_id}",
                data=updates
            )
            
            updated_element = DashboardElement.from_api_response(element_data)
            
            self.logger.info(
                "Updated dashboard element",
                element_id=element_id,
                updates=list(updates.keys())
            )
            
            return updated_element
            
        except LookerAPIError as e:
            self.logger.error(
                "Failed to update dashboard element",
                error=str(e),
                element_id=element_id
            )
            raise
    
    async def delete_dashboard_element(self, element_id: str) -> None:
        """Delete a dashboard element.
        
        Args:
            element_id: Element ID
        """
        try:
            await self.client._make_request(
                "DELETE",
                f"/dashboard_elements/{element_id}"
            )
            
            self.logger.info("Deleted dashboard element", element_id=element_id)
            
        except LookerAPIError as e:
            self.logger.error(
                "Failed to delete dashboard element",
                error=str(e),
                element_id=element_id
            )
            raise
    
    async def create_chart_element(
        self, 
        dashboard_id: str,
        query_id: str,
        title: str,
        row: int,
        col: int,
        width: int = 6,
        height: int = 4,
        subtitle: Optional[str] = None
    ) -> DashboardElement:
        """Create a chart element on a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            query_id: Query ID for the chart
            title: Chart title
            row: Row position
            col: Column position
            width: Element width
            height: Element height
            subtitle: Optional subtitle
            
        Returns:
            Created DashboardElement
        """
        element = DashboardElement(
            id="",  # Will be set by API
            type="vis",
            title=title,
            subtitle=subtitle,
            query_id=query_id,
            look_id=None,
            body_text=None,
            row=row,
            col=col,
            width=width,
            height=height
        )
        
        return await self.add_element_to_dashboard(dashboard_id, element)
    
    async def create_text_element(
        self, 
        dashboard_id: str,
        body_text: str,
        title: Optional[str] = None,
        row: int = 0,
        col: int = 0,
        width: int = 12,
        height: int = 2
    ) -> DashboardElement:
        """Create a text element on a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            body_text: Text content
            title: Optional title
            row: Row position
            col: Column position
            width: Element width
            height: Element height
            
        Returns:
            Created DashboardElement
        """
        element = DashboardElement(
            id="",  # Will be set by API
            type="text",
            title=title,
            subtitle=None,
            query_id=None,
            look_id=None,
            body_text=body_text,
            row=row,
            col=col,
            width=width,
            height=height
        )
        
        return await self.add_element_to_dashboard(dashboard_id, element)
    
    def calculate_next_position(self, dashboard: Dashboard) -> tuple[int, int]:
        """Calculate the next available position for a new element.
        
        Args:
            dashboard: Dashboard object
            
        Returns:
            Tuple of (row, col) for next position
        """
        if not dashboard.elements:
            return (0, 0)
        
        # Find the maximum row
        max_row = max(elem.row + elem.height for elem in dashboard.elements)
        
        return (max_row, 0)