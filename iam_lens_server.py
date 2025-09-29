import json
import subprocess
import asyncio
import os
# from datetime import datetime
from typing import Optional, Dict, List, Any
from fastmcp import FastMCP

mcp = FastMCP("IAM Lens MCP Server")


class IamLensClient:
    """Client wrapper for iam-lens CLI tool"""

    def __init__(self, iam_lens_path: str = "iam-lens", collect_configs: str = None):
        self.iam_lens_path = iam_lens_path
        if not collect_configs:
            raise ValueError("collect_configs is required and cannot be None or empty")
        self.collect_configs = collect_configs

    async def run_command(self, args: List[str]) -> Dict[str, Any]:
        """Run iam-lens command and return parsed result"""
        try:
            cmd = [self.iam_lens_path] + args
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
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


@mcp.tool
def greet(name: str) -> str:
    """Greet a user by name."""
    return f"Hello, {name}!"


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


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
