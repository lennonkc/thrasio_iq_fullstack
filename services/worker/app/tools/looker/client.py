"""Looker API client for dashboard and visualization management."""

from typing import Any, Dict, List, Optional, Union
import os
import json
import httpx
import structlog
from datetime import datetime, timedelta
from urllib.parse import urljoin


class LookerAPIError(Exception):
    """Custom exception for Looker API errors."""
    pass


class LookerClient:
    """Client for interacting with Looker API."""
    
    def __init__(
        self, 
        base_url: str,
        client_id: str,
        client_secret: str,
        timeout: float = 30.0
    ):
        """Initialize Looker client.
        
        Args:
            base_url: Looker instance base URL
            client_id: API client ID
            client_secret: API client secret
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self.logger = structlog.get_logger()
        
        # Authentication state
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
        # HTTP client
        self._http_client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._http_client.aclose()
    
    async def authenticate(self) -> None:
        """Authenticate with Looker API and get access token.
        
        Raises:
            LookerAPIError: If authentication fails
        """
        try:
            auth_url = urljoin(self.base_url, "/api/4.0/login")
            
            auth_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = await self._http_client.post(auth_url, json=auth_data)
            
            if response.status_code != 200:
                raise LookerAPIError(f"Authentication failed: {response.status_code} - {response.text}")
            
            auth_result = response.json()
            self._access_token = auth_result.get("access_token")
            
            if not self._access_token:
                raise LookerAPIError("No access token received")
            
            # Set token expiration (default to 1 hour if not provided)
            expires_in = auth_result.get("expires_in", 3600)
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)  # 1 min buffer
            
            # Update HTTP client headers
            self._http_client.headers["Authorization"] = f"Bearer {self._access_token}"
            
            self.logger.info("Successfully authenticated with Looker API")
            
        except httpx.RequestError as e:
            raise LookerAPIError(f"Network error during authentication: {str(e)}")
        except Exception as e:
            raise LookerAPIError(f"Authentication error: {str(e)}")
    
    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        if (not self._access_token or 
            not self._token_expires_at or 
            datetime.utcnow() >= self._token_expires_at):
            await self.authenticate()
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Looker API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            
        Returns:
            Response JSON data
            
        Raises:
            LookerAPIError: If request fails
        """
        await self._ensure_authenticated()
        
        url = urljoin(self.base_url, f"/api/4.0{endpoint}")
        
        try:
            if method.upper() == "GET":
                response = await self._http_client.get(url, params=params)
            elif method.upper() == "POST":
                response = await self._http_client.post(url, json=data, params=params)
            elif method.upper() == "PUT":
                response = await self._http_client.put(url, json=data, params=params)
            elif method.upper() == "DELETE":
                response = await self._http_client.delete(url, params=params)
            else:
                raise LookerAPIError(f"Unsupported HTTP method: {method}")
            
            if response.status_code >= 400:
                error_msg = f"API request failed: {response.status_code} - {response.text}"
                self.logger.error("Looker API error", status=response.status_code, error=response.text)
                raise LookerAPIError(error_msg)
            
            # Handle empty responses
            if response.status_code == 204 or not response.content:
                return {}
            
            return response.json()
            
        except httpx.RequestError as e:
            raise LookerAPIError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise LookerAPIError(f"Invalid JSON response: {str(e)}")
    
    async def get_user_info(self) -> Dict[str, Any]:
        """Get current user information.
        
        Returns:
            User information dictionary
        """
        return await self._make_request("GET", "/user")
    
    async def list_dashboards(self, space_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List dashboards.
        
        Args:
            space_id: Optional space ID to filter dashboards
            
        Returns:
            List of dashboard objects
        """
        params = {}
        if space_id:
            params["space_id"] = space_id
        
        dashboards = await self._make_request("GET", "/dashboards", params=params)
        
        self.logger.info("Listed dashboards", count=len(dashboards))
        return dashboards
    
    async def get_dashboard(self, dashboard_id: str) -> Dict[str, Any]:
        """Get dashboard details.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            Dashboard object
        """
        dashboard = await self._make_request("GET", f"/dashboards/{dashboard_id}")
        
        self.logger.info("Retrieved dashboard", dashboard_id=dashboard_id)
        return dashboard
    
    async def create_dashboard(
        self, 
        title: str, 
        space_id: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new dashboard.
        
        Args:
            title: Dashboard title
            space_id: Space ID where dashboard will be created
            description: Optional dashboard description
            
        Returns:
            Created dashboard object
        """
        dashboard_data = {
            "title": title,
            "space_id": space_id
        }
        
        if description:
            dashboard_data["description"] = description
        
        dashboard = await self._make_request("POST", "/dashboards", data=dashboard_data)
        
        self.logger.info(
            "Created dashboard", 
            dashboard_id=dashboard.get("id"),
            title=title
        )
        return dashboard
    
    async def update_dashboard(
        self, 
        dashboard_id: str, 
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated dashboard object
        """
        dashboard = await self._make_request(
            "PUT", 
            f"/dashboards/{dashboard_id}", 
            data=updates
        )
        
        self.logger.info("Updated dashboard", dashboard_id=dashboard_id)
        return dashboard
    
    async def delete_dashboard(self, dashboard_id: str) -> None:
        """Delete dashboard.
        
        Args:
            dashboard_id: Dashboard ID
        """
        await self._make_request("DELETE", f"/dashboards/{dashboard_id}")
        
        self.logger.info("Deleted dashboard", dashboard_id=dashboard_id)
    
    async def list_looks(self, space_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List Looks (saved queries).
        
        Args:
            space_id: Optional space ID to filter Looks
            
        Returns:
            List of Look objects
        """
        params = {}
        if space_id:
            params["space_id"] = space_id
        
        looks = await self._make_request("GET", "/looks", params=params)
        
        self.logger.info("Listed looks", count=len(looks))
        return looks
    
    async def get_look(self, look_id: str) -> Dict[str, Any]:
        """Get Look details.
        
        Args:
            look_id: Look ID
            
        Returns:
            Look object
        """
        look = await self._make_request("GET", f"/looks/{look_id}")
        
        self.logger.info("Retrieved look", look_id=look_id)
        return look
    
    async def create_look(
        self, 
        title: str,
        space_id: str,
        query_id: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new Look.
        
        Args:
            title: Look title
            space_id: Space ID where Look will be created
            query_id: Query ID to base the Look on
            description: Optional Look description
            
        Returns:
            Created Look object
        """
        look_data = {
            "title": title,
            "space_id": space_id,
            "query_id": query_id
        }
        
        if description:
            look_data["description"] = description
        
        look = await self._make_request("POST", "/looks", data=look_data)
        
        self.logger.info(
            "Created look", 
            look_id=look.get("id"),
            title=title
        )
        return look
    
    async def run_query(
        self, 
        query_id: str, 
        result_format: str = "json",
        limit: Optional[int] = None
    ) -> Any:
        """Run a query and get results.
        
        Args:
            query_id: Query ID to run
            result_format: Result format (json, csv, etc.)
            limit: Optional row limit
            
        Returns:
            Query results in specified format
        """
        params = {"result_format": result_format}
        if limit:
            params["limit"] = limit
        
        results = await self._make_request(
            "GET", 
            f"/queries/{query_id}/run/{result_format}",
            params=params
        )
        
        self.logger.info(
            "Executed query", 
            query_id=query_id, 
            format=result_format
        )
        return results
    
    async def list_spaces(self) -> List[Dict[str, Any]]:
        """List all spaces.
        
        Returns:
            List of space objects
        """
        spaces = await self._make_request("GET", "/spaces")
        
        self.logger.info("Listed spaces", count=len(spaces))
        return spaces
    
    async def get_space(self, space_id: str) -> Dict[str, Any]:
        """Get space details.
        
        Args:
            space_id: Space ID
            
        Returns:
            Space object
        """
        space = await self._make_request("GET", f"/spaces/{space_id}")
        
        self.logger.info("Retrieved space", space_id=space_id)
        return space
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List all LookML models.
        
        Returns:
            List of model objects
        """
        models = await self._make_request("GET", "/lookml_models")
        
        self.logger.info("Listed models", count=len(models))
        return models
    
    async def get_model_explores(self, model_name: str) -> List[Dict[str, Any]]:
        """Get explores for a model.
        
        Args:
            model_name: Model name
            
        Returns:
            List of explore objects
        """
        explores = await self._make_request("GET", f"/lookml_models/{model_name}/explores")
        
        self.logger.info(
            "Retrieved model explores", 
            model=model_name, 
            count=len(explores)
        )
        return explores