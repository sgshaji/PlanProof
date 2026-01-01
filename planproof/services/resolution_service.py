"""
Resolution Service - Handle issue resolution actions and auto-recheck logic.

This service processes user actions (document uploads, selections, explanations),
triggers revalidation, and tracks resolution progress.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

# Setup logging
logger = logging.getLogger(__name__)


class ResolutionService:
    """Service for managing issue resolution lifecycle."""
    
    def __init__(self, run_id: int):
        """
        Initialize resolution service for a specific run.
        
        Args:
            run_id: Run ID to track resolutions for
        """
        self.run_id = run_id
        self.run_dir = Path(f"./runs/{run_id}")
        self.inputs_dir = self.run_dir / "inputs"
        self.outputs_dir = self.run_dir / "outputs"
        self.resolution_file = self.outputs_dir / "resolutions.json"
        
        # Ensure directories exist
        self.inputs_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing resolutions
        self.resolutions = self._load_resolutions()
    
    def _load_resolutions(self) -> Dict[str, Any]:
        """Load resolution history from file."""
        if self.resolution_file.exists():
            try:
                with open(self.resolution_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load resolutions: {e}")
                return {"actions": [], "issues": {}}
        return {"actions": [], "issues": {}}
    
    def _save_resolutions(self) -> None:
        """Save resolution history to file."""
        try:
            with open(self.resolution_file, 'w', encoding='utf-8') as f:
                json.dump(self.resolutions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Could not save resolutions: {e}")
    
    def process_document_upload(
        self,
        uploaded_file: Any,
        document_type: str,
        issue_id: str
    ) -> Dict[str, Any]:
        """
        Process a document upload action.
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            document_type: Type of document being uploaded
            issue_id: Issue this resolves
            
        Returns:
            Result dictionary with status and new document info
        """
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = uploaded_file.name
            safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in original_name)
            filename = f"{timestamp}_{safe_name}"
            
            # Save file to inputs directory
            file_path = self.inputs_dir / filename
            
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            logger.info(f"Saved uploaded file: {file_path}")
            
            # Record action
            action_record = {
                "timestamp": datetime.now().isoformat(),
                "action_type": "document_upload",
                "issue_id": issue_id,
                "document_type": document_type,
                "filename": filename,
                "original_name": original_name,
                "file_path": str(file_path)
            }
            
            self.resolutions["actions"].append(action_record)
            
            # Update issue status
            if issue_id not in self.resolutions["issues"]:
                self.resolutions["issues"][issue_id] = {
                    "status": "in_progress",
                    "actions_taken": [],
                    "recheck_pending": True
                }
            
            self.resolutions["issues"][issue_id]["actions_taken"].append(action_record)
            self.resolutions["issues"][issue_id]["recheck_pending"] = True
            self.resolutions["issues"][issue_id]["last_action"] = datetime.now().isoformat()
            
            self._save_resolutions()
            
            return {
                "success": True,
                "filename": filename,
                "file_path": str(file_path),
                "message": f"Successfully uploaded {original_name}"
            }
        
        except Exception as e:
            logger.error(f"Error processing upload: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_bulk_document_upload(
        self,
        uploads: List[Tuple[Any, str]],
        issue_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Process multiple document uploads at once.
        
        Args:
            uploads: List of (uploaded_file, document_type) tuples
            issue_ids: List of issue IDs this resolves
            
        Returns:
            Result dictionary with batch processing results
        """
        results = []
        success_count = 0
        
        for uploaded_file, document_type in uploads:
            # Process each upload
            result = self.process_document_upload(
                uploaded_file,
                document_type,
                issue_id=f"bulk_{document_type}"
            )
            
            results.append({
                "filename": uploaded_file.name,
                "document_type": document_type,
                "result": result
            })
            
            if result.get("success"):
                success_count += 1
        
        # Mark all related issues for recheck
        for issue_id in issue_ids:
            if issue_id not in self.resolutions["issues"]:
                self.resolutions["issues"][issue_id] = {
                    "status": "in_progress",
                    "actions_taken": [],
                    "recheck_pending": True
                }
            self.resolutions["issues"][issue_id]["recheck_pending"] = True
        
        self._save_resolutions()
        
        return {
            "success": success_count == len(uploads),
            "total": len(uploads),
            "successful": success_count,
            "failed": len(uploads) - success_count,
            "results": results
        }
    
    def process_option_selection(
        self,
        issue_id: str,
        selected_option: str,
        option_label: str
    ) -> Dict[str, Any]:
        """
        Process an option selection action (e.g., BNG applicability).
        
        Args:
            issue_id: Issue being resolved
            selected_option: Option value selected
            option_label: Human-readable label
            
        Returns:
            Result dictionary
        """
        try:
            action_record = {
                "timestamp": datetime.now().isoformat(),
                "action_type": "option_selection",
                "issue_id": issue_id,
                "selected_option": selected_option,
                "option_label": option_label
            }
            
            self.resolutions["actions"].append(action_record)
            
            # Update issue status
            if issue_id not in self.resolutions["issues"]:
                self.resolutions["issues"][issue_id] = {
                    "status": "awaiting_verification",
                    "actions_taken": []
                }
            
            self.resolutions["issues"][issue_id]["actions_taken"].append(action_record)
            self.resolutions["issues"][issue_id]["selected_value"] = selected_option
            self.resolutions["issues"][issue_id]["status"] = "awaiting_verification"
            self.resolutions["issues"][issue_id]["last_action"] = datetime.now().isoformat()
            
            self._save_resolutions()
            
            return {
                "success": True,
                "message": f"Selection recorded: {option_label}"
            }
        
        except Exception as e:
            logger.error(f"Error processing selection: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_explanation(
        self,
        issue_id: str,
        explanation_text: str
    ) -> Dict[str, Any]:
        """
        Process an explanation/justification submission.
        
        Args:
            issue_id: Issue being addressed
            explanation_text: User's explanation
            
        Returns:
            Result dictionary
        """
        try:
            action_record = {
                "timestamp": datetime.now().isoformat(),
                "action_type": "explanation_provided",
                "issue_id": issue_id,
                "explanation": explanation_text
            }
            
            self.resolutions["actions"].append(action_record)
            
            # Update issue status
            if issue_id not in self.resolutions["issues"]:
                self.resolutions["issues"][issue_id] = {
                    "status": "awaiting_verification",
                    "actions_taken": []
                }
            
            self.resolutions["issues"][issue_id]["actions_taken"].append(action_record)
            self.resolutions["issues"][issue_id]["explanation"] = explanation_text
            self.resolutions["issues"][issue_id]["status"] = "awaiting_verification"
            self.resolutions["issues"][issue_id]["last_action"] = datetime.now().isoformat()
            
            self._save_resolutions()
            
            return {
                "success": True,
                "message": "Explanation recorded"
            }
        
        except Exception as e:
            logger.error(f"Error processing explanation: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_issues_pending_recheck(self) -> List[str]:
        """
        Get list of issue IDs that need rechecking.
        
        Returns:
            List of issue IDs with recheck_pending=True
        """
        pending = []
        for issue_id, data in self.resolutions["issues"].items():
            if data.get("recheck_pending", False):
                pending.append(issue_id)
        return pending
    
    def mark_issue_rechecked(
        self,
        issue_id: str,
        new_status: str,
        recheck_result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark an issue as rechecked and update its status.
        
        Args:
            issue_id: Issue that was rechecked
            new_status: New status (resolved, still_open, etc.)
            recheck_result: Optional result data from recheck
        """
        if issue_id in self.resolutions["issues"]:
            self.resolutions["issues"][issue_id]["recheck_pending"] = False
            self.resolutions["issues"][issue_id]["status"] = new_status
            self.resolutions["issues"][issue_id]["last_recheck"] = datetime.now().isoformat()
            
            if recheck_result:
                self.resolutions["issues"][issue_id]["recheck_result"] = recheck_result
            
            self._save_resolutions()
    
    def get_issue_status(self, issue_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of an issue.
        
        Args:
            issue_id: Issue to check
            
        Returns:
            Issue status dictionary or None
        """
        return self.resolutions["issues"].get(issue_id)
    
    def get_all_actions(self) -> List[Dict[str, Any]]:
        """Get all actions taken in this run."""
        return self.resolutions.get("actions", [])
    
    def dismiss_issue(
        self,
        issue_id: str,
        officer_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Dismiss an issue (officer override).
        
        Args:
            issue_id: Issue to dismiss
            officer_id: Officer performing dismissal
            reason: Reason for dismissal
            
        Returns:
            Result dictionary
        """
        try:
            action_record = {
                "timestamp": datetime.now().isoformat(),
                "action_type": "dismissed",
                "issue_id": issue_id,
                "officer_id": officer_id,
                "reason": reason
            }
            
            self.resolutions["actions"].append(action_record)
            
            # Update issue status
            if issue_id not in self.resolutions["issues"]:
                self.resolutions["issues"][issue_id] = {
                    "status": "dismissed",
                    "actions_taken": []
                }
            
            self.resolutions["issues"][issue_id]["actions_taken"].append(action_record)
            self.resolutions["issues"][issue_id]["status"] = "dismissed"
            self.resolutions["issues"][issue_id]["dismissed_by"] = officer_id
            self.resolutions["issues"][issue_id]["dismissal_reason"] = reason
            self.resolutions["issues"][issue_id]["dismissed_at"] = datetime.now().isoformat()
            
            self._save_resolutions()
            
            return {
                "success": True,
                "message": "Issue dismissed"
            }
        
        except Exception as e:
            logger.error(f"Error dismissing issue: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class AutoRecheckEngine:
    """Engine for automatically rechecking validation rules after actions."""
    
    def __init__(self, run_id: int):
        """
        Initialize auto-recheck engine.
        
        Args:
            run_id: Run ID to recheck
        """
        self.run_id = run_id
        self.resolution_service = ResolutionService(run_id)
    
    def trigger_recheck(self) -> Dict[str, Any]:
        """
        Trigger recheck for all pending issues.
        
        This would normally re-run the validation pipeline,
        but for now we'll simulate it.
        
        Returns:
            Recheck results
        """
        pending_issues = self.resolution_service.get_issues_pending_recheck()
        
        if not pending_issues:
            return {
                "success": True,
                "message": "No issues pending recheck",
                "issues_checked": 0
            }
        
        logger.info(f"Rechecking {len(pending_issues)} issues...")
        
        # TODO: Actually re-run validation pipeline
        # For now, simulate by marking as resolved
        results = []
        
        for issue_id in pending_issues:
            issue_status = self.resolution_service.get_issue_status(issue_id)
            
            # Check if action was taken
            if issue_status and issue_status.get("actions_taken"):
                # Simulate successful resolution
                self.resolution_service.mark_issue_rechecked(
                    issue_id,
                    "resolved",
                    {"simulated": True, "note": "Revalidation would run here"}
                )
                
                results.append({
                    "issue_id": issue_id,
                    "status": "resolved",
                    "message": "Action processed successfully"
                })
            else:
                results.append({
                    "issue_id": issue_id,
                    "status": "pending",
                    "message": "No action taken yet"
                })
        
        return {
            "success": True,
            "issues_checked": len(pending_issues),
            "results": results
        }
    
    def revalidate_specific_rules(
        self,
        rule_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Re-run specific validation rules.
        
        Args:
            rule_ids: List of rule IDs to re-run
            
        Returns:
            Revalidation results
        """
        # TODO: Implement actual rule re-execution
        logger.info(f"Would revalidate rules: {rule_ids}")
        
        return {
            "success": True,
            "message": f"Revalidation of {len(rule_ids)} rules would run here",
            "rules": rule_ids
        }


class DependencyResolver:
    """Resolve dependencies between issues."""
    
    def __init__(self, issues: List[Any]):
        """
        Initialize dependency resolver.
        
        Args:
            issues: List of EnhancedIssue objects
        """
        self.issues = {issue.issue_id: issue for issue in issues}
        self.dependency_graph = self._build_dependency_graph()
    
    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build graph of issue dependencies."""
        graph = {}
        
        for issue_id, issue in self.issues.items():
            if issue.resolution and issue.resolution.depends_on_issues:
                graph[issue_id] = issue.resolution.depends_on_issues
            else:
                graph[issue_id] = []
        
        return graph
    
    def get_dependent_issues(self, issue_id: str) -> List[str]:
        """
        Get all issues that depend on the given issue.
        
        Args:
            issue_id: Issue to check dependencies for
            
        Returns:
            List of issue IDs that depend on this issue
        """
        dependents = []
        
        for other_id, dependencies in self.dependency_graph.items():
            if issue_id in dependencies:
                dependents.append(other_id)
        
        return dependents
    
    def get_blocking_issues(self, issue_id: str) -> List[str]:
        """
        Get all issues blocking the given issue.
        
        Args:
            issue_id: Issue to check
            
        Returns:
            List of issue IDs that must be resolved first
        """
        return self.dependency_graph.get(issue_id, [])
    
    def cascade_resolution(
        self,
        resolved_issue_id: str,
        resolution_service: ResolutionService
    ) -> List[str]:
        """
        Cascade resolution to dependent issues.
        
        When an issue is resolved, mark dependent issues for recheck.
        
        Args:
            resolved_issue_id: Issue that was just resolved
            resolution_service: Service for tracking resolutions
            
        Returns:
            List of issue IDs marked for recheck
        """
        dependent_issues = self.get_dependent_issues(resolved_issue_id)
        rechecked = []
        
        for issue_id in dependent_issues:
            # Check if all blocking issues are resolved
            blocking = self.get_blocking_issues(issue_id)
            all_resolved = True
            
            for blocker in blocking:
                status = resolution_service.get_issue_status(blocker)
                if not status or status.get("status") != "resolved":
                    all_resolved = False
                    break
            
            if all_resolved:
                # Mark for recheck
                if issue_id not in resolution_service.resolutions["issues"]:
                    resolution_service.resolutions["issues"][issue_id] = {}
                
                resolution_service.resolutions["issues"][issue_id]["recheck_pending"] = True
                rechecked.append(issue_id)
        
        resolution_service._save_resolutions()
        
        return rechecked
