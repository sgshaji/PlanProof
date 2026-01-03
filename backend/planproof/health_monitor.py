"""
Enhanced health monitoring with detailed metrics.

Extends the basic health checks with:
- System resource monitoring (CPU, memory, disk)
- Application performance metrics
- Dependency health status
- Alerting integration

Usage:
    from planproof.health_monitor import HealthMonitor
    
    monitor = HealthMonitor()
    status = monitor.get_full_health_status()
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

LOGGER = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthMonitor:
    """Comprehensive health monitoring system."""
    
    def __init__(self):
        """Initialize health monitor."""
        self.start_time = time.time()
        self._check_results: Dict[str, Any] = {}
    
    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system-level metrics.
        
        Returns:
            Dictionary with CPU, memory, and disk metrics
        """
        if not HAS_PSUTIL:
            return {
                "available": False,
                "message": "psutil not installed"
            }
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get process-specific metrics
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info()
            
            return {
                "available": True,
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(),
                    "load_avg": os.getloadavg() if hasattr(os, 'getloadavg') else None
                },
                "memory": {
                    "total_mb": memory.total / (1024 * 1024),
                    "available_mb": memory.available / (1024 * 1024),
                    "used_mb": memory.used / (1024 * 1024),
                    "percent": memory.percent,
                    "process_rss_mb": process_memory.rss / (1024 * 1024),
                    "process_vms_mb": process_memory.vms / (1024 * 1024)
                },
                "disk": {
                    "total_gb": disk.total / (1024 * 1024 * 1024),
                    "used_gb": disk.used / (1024 * 1024 * 1024),
                    "free_gb": disk.free / (1024 * 1024 * 1024),
                    "percent": disk.percent
                },
                "process": {
                    "pid": os.getpid(),
                    "threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                    "connections": len(process.connections())
                }
            }
        except Exception as e:
            LOGGER.error(f"Error getting system metrics: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    def check_database(self, db) -> Dict[str, Any]:
        """
        Check database health.
        
        Args:
            db: Database instance
        
        Returns:
            Health check result
        """
        start = time.time()
        try:
            session = db.get_session()
            
            # Execute simple query to test connectivity
            from planproof.db import Application, Document, Submission
            
            app_count = session.query(Application).count()
            doc_count = session.query(Document).count()
            sub_count = session.query(Submission).count()
            
            # Check query performance
            query_time = time.time() - start
            
            session.close()
            
            status = HealthStatus.HEALTHY
            if query_time > 1.0:
                status = HealthStatus.DEGRADED
            
            return {
                "status": status.value,
                "connected": True,
                "query_time_ms": query_time * 1000,
                "statistics": {
                    "applications": app_count,
                    "documents": doc_count,
                    "submissions": sub_count
                },
                "pool_info": {
                    "size": db.engine.pool.size() if hasattr(db.engine.pool, 'size') else None,
                    "checked_in": db.engine.pool.checkedin() if hasattr(db.engine.pool, 'checkedin') else None,
                    "overflow": db.engine.pool.overflow() if hasattr(db.engine.pool, 'overflow') else None
                }
            }
        except Exception as e:
            LOGGER.error(f"Database health check failed: {e}")
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "connected": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def check_storage(self, storage_client) -> Dict[str, Any]:
        """
        Check Azure Blob Storage health.
        
        Args:
            storage_client: StorageClient instance
        
        Returns:
            Health check result
        """
        start = time.time()
        try:
            # List containers to test connectivity
            blob_service = storage_client.blob_service_client
            containers = list(blob_service.list_containers(max_results=5))
            
            response_time = time.time() - start
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "connected": True,
                "response_time_ms": response_time * 1000,
                "containers_found": len(containers),
                "containers": [c.name for c in containers]
            }
        except Exception as e:
            LOGGER.error(f"Storage health check failed: {e}")
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "connected": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def check_docintel(self, docintel_client) -> Dict[str, Any]:
        """
        Check Azure Document Intelligence health.
        
        Args:
            docintel_client: DocumentIntelligence instance
        
        Returns:
            Health check result
        """
        try:
            # Check if client is initialized
            if not docintel_client.client:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "connected": False,
                    "error": "Client not initialized"
                }
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "connected": True,
                "endpoint": docintel_client.endpoint
            }
        except Exception as e:
            LOGGER.error(f"DocIntel health check failed: {e}")
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "connected": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def check_llm(self, aoai_client) -> Dict[str, Any]:
        """
        Check Azure OpenAI health.
        
        Args:
            aoai_client: AzureOpenAIClient instance
        
        Returns:
            Health check result
        """
        try:
            # Check if client is initialized
            if not aoai_client.client:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "connected": False,
                    "error": "Client not initialized"
                }
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "connected": True,
                "deployment": aoai_client.deployment,
                "total_calls": aoai_client._call_count,
                "total_tokens": aoai_client.total_tokens,
                "estimated_cost": aoai_client.total_cost
            }
        except Exception as e:
            LOGGER.error(f"LLM health check failed: {e}")
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "connected": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def get_full_health_status(
        self,
        db=None,
        storage_client=None,
        docintel_client=None,
        aoai_client=None
    ) -> Dict[str, Any]:
        """
        Get comprehensive health status for all components.
        
        Args:
            db: Optional Database instance
            storage_client: Optional StorageClient instance
            docintel_client: Optional DocumentIntelligence instance
            aoai_client: Optional AzureOpenAIClient instance
        
        Returns:
            Complete health status report
        """
        components = {}
        overall_status = HealthStatus.HEALTHY
        
        # System metrics
        components["system"] = self.get_system_metrics()
        
        # Database
        if db:
            db_health = self.check_database(db)
            components["database"] = db_health
            if db_health["status"] != HealthStatus.HEALTHY.value:
                overall_status = HealthStatus.DEGRADED if overall_status == HealthStatus.HEALTHY else HealthStatus.UNHEALTHY
        
        # Storage
        if storage_client:
            storage_health = self.check_storage(storage_client)
            components["storage"] = storage_health
            if storage_health["status"] != HealthStatus.HEALTHY.value:
                overall_status = HealthStatus.DEGRADED if overall_status == HealthStatus.HEALTHY else HealthStatus.UNHEALTHY
        
        # Document Intelligence
        if docintel_client:
            docintel_health = self.check_docintel(docintel_client)
            components["docintel"] = docintel_health
            if docintel_health["status"] != HealthStatus.HEALTHY.value:
                overall_status = HealthStatus.DEGRADED
        
        # LLM
        if aoai_client:
            llm_health = self.check_llm(aoai_client)
            components["llm"] = llm_health
            if llm_health["status"] != HealthStatus.HEALTHY.value:
                overall_status = HealthStatus.DEGRADED
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": self.get_uptime(),
            "service": "planproof",
            "version": os.getenv("DEPLOYMENT_VERSION", "1.0.0"),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "components": components
        }


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get or create the global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
