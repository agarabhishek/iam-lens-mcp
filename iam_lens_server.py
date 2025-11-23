"""
IAM Lens MCP Server

This module implements an MCP (Model Context Protocol) server that provides AWS IAM
analysis capabilities through two approaches:
1. iam-lens CLI tools for fast, deterministic policy evaluation
2. Direct IAM data analysis tools for flexible, AI-powered exploration

The server exposes tools for simulating IAM requests, identifying resource access,
analyzing principal permissions, and performing complex IAM queries.
"""

import json
import subprocess
import asyncio
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from fastmcp import FastMCP

# Import IAM data analysis functions
from iam_data_analysis import (
    get_data_directory,
    get_iam_data_structure_internal,
    read_iam_file_internal,
    build_query_iam_data_response,
)

mcp = FastMCP("IAM Lens MCP Server")


class IamLensClient:
    """Client wrapper for iam-lens CLI tool"""

    def __init__(self, iam_lens_path: str = "iam-lens", collect_configs: str = None):
        self.iam_lens_path = iam_lens_path
        if not collect_configs:
            raise ValueError("collect_configs is required and cannot be None or empty")
        self.collect_configs = collect_configs
        # Store the directory containing the config file
        # This allows iam-lens to resolve relative paths in the config correctly
        self.config_dir = str(Path(collect_configs).parent.absolute())

    async def run_command(self, args: List[str]) -> Dict[str, Any]:
        """Run iam-lens command and return parsed result"""
        try:
            cmd = [self.iam_lens_path] + args
            # Run iam-lens from the config file's directory
            # This allows relative paths in the config to be resolved correctly
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config_dir,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                return {
                    "success": False,
                    "error": error_msg,
                    "returncode": process.returncode,
                }

            # Try to parse JSON output
            try:
                result = json.loads(stdout.decode())
                return {"success": True, "data": result}
            except json.JSONDecodeError:
                # If not JSON, return raw text
                return {"success": True, "data": stdout.decode().strip()}

        except Exception as e:
            return {"success": False, "error": f"Failed to execute iam-lens: {str(e)}"}


# Initialize the IAM client with collectConfigs from environment variable
collect_configs = os.getenv("COLLECT_CONFIGS")
if not collect_configs:
    raise ValueError("COLLECT_CONFIGS environment variable is required but not set")
iam_client = IamLensClient(collect_configs=collect_configs)


# ============================================================================
#                           iam-lens CLI Tools
# ============================================================================


@mcp.tool
async def simulate_iam_request(
    principal: str,
    action: str,
    resource: Optional[str] = None,
    resource_account: Optional[str] = None,
    context_keys: Optional[Dict[str, str]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Simulate an IAM request to determine if a principal can perform an action on a resource.

    Args:
        principal: The principal ARN (user, role, etc.) to simulate
        action: The IAM action to test (e.g., 's3:GetObject')
        resource: The resource ARN to test access to (optional for wildcard actions)
        resource_account: The account ID if not determinable from resource ARN
        context_keys: Additional context keys for the simulation
        verbose: Enable verbose output

    Returns:
        Simulation result with decision (Allowed/ImplicitlyDenied/ExplicitlyDenied)
    """
    args = ["simulate", "--principal", principal, "--action", action]

    if resource:
        args.extend(["--resource", resource])

    if resource_account:
        args.extend(["--resource-account", resource_account])

    if context_keys:
        for key, value in context_keys.items():
            args.extend(["--context", key, value])

    if verbose:
        args.append("--verbose")

    # Add collectConfigs from client configuration (always present since it's required)
    args.extend(["--collectConfigs", iam_client.collect_configs])

    result = await iam_client.run_command(args)

    if not result["success"]:
        return {
            "error": result["error"],
            "principal": principal,
            "action": action,
            "resource": resource,
        }

    return {
        "principal": principal,
        "action": action,
        "resource": resource,
        "result": result["data"],
    }


@mcp.tool
async def who_can_access_resource(
    resource: str,
    actions: List[str],
    resource_account: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find all principals that can perform specified actions on a resource.

    Args:
        resource: The resource ARN to analyze
        actions: List of actions to check (e.g., ['s3:GetObject', 's3:PutObject'])
        resource_account: The account ID if not determinable from resource ARN

    Returns:
        List of principals with access to the resource
    """
    args = ["who-can", "--resource", resource]

    if actions:
        args.extend(["--actions"] + actions)

    if resource_account:
        args.extend(["--resource-account", resource_account])

    # Add collectConfigs from client configuration (always present since it's required)
    args.extend(["--collectConfigs", iam_client.collect_configs])

    result = await iam_client.run_command(args)

    if not result["success"]:
        return {"error": result["error"], "resource": resource, "actions": actions}

    return {
        "resource": resource,
        "actions": actions,
        "principals_with_access": result["data"],
    }


@mcp.tool
async def principal_can(
    principal: str,
    shrink_action_lists: bool = False,
) -> Dict[str, Any]:
    """
    Get a consolidated view of all permissions for a principal.

    Args:
        principal: The principal ARN to analyze (user or role)
        shrink_action_lists: Reduce policy size by condensing action lists

    Returns:
        Consolidated IAM policy showing all effective permissions for the principal
    """
    args = ["principal-can", "--principal", principal]

    if shrink_action_lists:
        args.append("--shrink-action-lists")

    # Add collectConfigs from client configuration (always present since it's required)
    args.extend(["--collectConfigs", iam_client.collect_configs])

    result = await iam_client.run_command(args)

    if not result["success"]:
        return {"error": result["error"], "principal": principal}

    return {
        "principal": principal,
        "permissions": result["data"],
    }


# ============================================================================
#                   Direct IAM Data Analysis Tools
# ============================================================================

@mcp.tool
async def get_iam_data_structure(
    focus_accounts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Get the IAM data folder structure showing available accounts, services, and resources.

    This tool provides an overview of what IAM data is available without reading
    the actual file contents. Use this to understand what data exists before
    requesting specific files.

    Args:
        focus_accounts: Optional list of account IDs to limit the structure to

    Returns:
        Dict containing the folder structure with accounts, services, resource types, and counts
    """
    try:
        data_directory = get_data_directory(iam_client.collect_configs)
        structure = get_iam_data_structure_internal(data_directory, focus_accounts)
        return {"success": True, **structure}
    except Exception as e:
        return {"success": False, "error": f"Error getting data structure: {str(e)}"}


@mcp.tool
async def read_iam_file(
    file_path: str,
    read_metadata: bool = True,
) -> Dict[str, Any]:
    """
    Read and return the content of a specific IAM data file or directory.

    This tool can handle both files and directories:
    - For files: returns the file content (parsed JSON or raw text)
    - For directories: lists the contents and optionally reads metadata.json from subdirectories

    Use this after get_iam_data_structure to explore specific paths.

    Args:
        file_path: Relative path from the data directory
                  Examples:
                  - File: "aws/aws/indexes/principals-to-trust-policies.json"
                  - File: "aws/aws/accounts/123456789012/iam/user/myuser/metadata.json"
                  - Directory: "aws/aws/accounts/123456789012/iam/user"
        read_metadata: If True and path is a directory containing resource subdirectories,
                      automatically reads metadata.json from each (up to 100 resources)

    Returns:
        For files: Dict with file_path, content_type (json/text), and content
        For directories: Dict with file_path, content_type (directory), items list,
                        and optionally a resources list with metadata
    """
    try:
        data_directory = get_data_directory(iam_client.collect_configs)
        file_content = read_iam_file_internal(data_directory, file_path, read_metadata)
        return {"success": True, **file_content}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error reading file: {str(e)}"}


@mcp.tool
async def query_iam_data(
    query: str,
    focus_accounts: Optional[List[str]] = None,
    focus_services: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Analyze IAM data to answer complex questions using direct filesystem access.

    This tool orchestrates get_iam_data_structure and read_iam_file to gather
    relevant IAM data and provide it with analysis instructions. It provides
    comprehensive information about IAM configurations, permissions, relationships,
    and security posture.

    This is more flexible than the other tools but may be slower. Use this for:
    - Exploratory questions about IAM setup (e.g., "What IAM users exist?")
    - Complex cross-account or cross-service analysis
    - Custom queries not covered by other tools
    - Finding security issues or overly permissive configurations

    Args:
        query: Natural language question about IAM data (e.g., "What IAM users are there?")
        focus_accounts: Optional list of account IDs to limit analysis to
        focus_services: Optional list of services to focus on (e.g., ["iam", "s3", "lambda"])

    Returns:
        Dict containing query, structure, index files content, and analysis instructions
    """
    try:
        # Get the data directory from the config
        data_directory = get_data_directory(iam_client.collect_configs)

        # Load agent instructions
        instructions_path = Path(__file__).parent / "agent_instructions.md"
        if not instructions_path.exists():
            return {
                "success": False,
                "error": "Agent instructions file not found. Please ensure agent_instructions.md exists.",
            }

        with open(instructions_path, "r") as f:
            agent_instructions = f.read()

        # Build comprehensive response using the imported function
        return build_query_iam_data_response(
            data_directory=data_directory,
            query=query,
            agent_instructions=agent_instructions,
            focus_accounts=focus_accounts,
            focus_services=focus_services,
        )

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "query": query,
        }


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
