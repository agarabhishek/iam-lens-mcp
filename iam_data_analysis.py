"""
IAM Data Analysis Module

This module provides direct access to IAM data collected by iam-collect.
It includes tools for exploring data structure, reading files, and performing
flexible AI-powered analysis of IAM configurations.
"""

import json
import json5
from pathlib import Path
from typing import Optional, Dict, List, Any


def get_data_directory(collect_configs_path: str) -> str:
    """
    Extract the data directory path from the iam-collect.jsonc config file.

    Args:
        collect_configs_path: Path to the iam-collect.jsonc configuration file

    Returns:
        Absolute path to the IAM data directory

    Raises:
        ValueError: If config file not found or storage path not configured
    """
    config_path = Path(collect_configs_path)

    if not config_path.exists():
        raise ValueError(f"Config file not found: {collect_configs_path}")

    try:
        # Read and parse the JSONC file (JSON with comments)
        with open(config_path, "r") as f:
            config = json5.load(f)

        # Extract storage path
        storage = config.get("storage", {})
        data_path = storage.get("path")

        if not data_path:
            raise ValueError("No 'storage.path' found in config file")

        # Resolve relative vs absolute path
        # If path starts with '.', it's relative to the config file
        if data_path.startswith("."):
            data_dir = (config_path.parent / data_path).resolve()
        else:
            data_dir = Path(data_path).resolve()

        if not data_dir.exists():
            raise ValueError(
                f"Data directory does not exist: {data_dir}\n"
                f"Please run 'iam-collect download' to populate the data."
            )

        return str(data_dir)

    except Exception as e:
        # Handle JSON parsing errors and other issues
        if "json" in str(type(e)).lower() or "decode" in str(type(e)).lower():
            raise ValueError(f"Failed to parse config file: {e}")
        raise ValueError(f"Error reading config file: {e}")


def detect_partition(data_directory: str) -> tuple[str, str]:
    """
    Detect the AWS partition from the data directory.

    Args:
        data_directory: Absolute path to the IAM data directory

    Returns:
        tuple: (partition_name, partition_relative_path)
        Examples: ("aws", "aws/aws"), ("aws-cn", "aws-cn/aws-cn"), ("aws-us-gov", "aws-us-gov/aws-us-gov")
    """
    data_path = Path(data_directory)

    # Check for each known partition
    for partition in ["aws", "aws-cn", "aws-us-gov"]:
        partition_dir = data_path / partition
        if partition_dir.exists() and partition_dir.is_dir():
            # Check if it has the expected subdirectory structure (partition/partition)
            partition_subdir = partition_dir / partition
            if partition_subdir.exists() and partition_subdir.is_dir():
                return (partition, f"{partition}/{partition}")

    # Fallback to aws if not found
    return ("aws", "aws/aws")


def get_iam_data_structure_internal(data_directory: str, focus_accounts: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Internal function to get IAM data structure.

    Args:
        data_directory: Absolute path to the IAM data directory
        focus_accounts: Optional list of account IDs to focus on

    Returns:
        Dict containing the folder structure
    """
    data_path = Path(data_directory)

    # Detect partition dynamically
    partition_name, partition_rel_path = detect_partition(data_directory)
    partition_path = data_path / partition_rel_path

    # List available accounts
    accounts_path = partition_path / "accounts"
    available_accounts = []
    if accounts_path.exists():
        available_accounts = [d.name for d in accounts_path.iterdir() if d.is_dir()]

    # Filter accounts if focus_accounts specified
    if focus_accounts:
        available_accounts = [acc for acc in available_accounts if acc in focus_accounts]

    # List available indexes
    indexes_path = partition_path / "indexes"
    available_indexes = []
    if indexes_path.exists():
        available_indexes = [f.name for f in indexes_path.iterdir() if f.is_file()]

    # List organizations
    orgs_path = partition_path / "organizations"
    available_orgs = []
    if orgs_path.exists():
        available_orgs = [d.name for d in orgs_path.iterdir() if d.is_dir()]

    # Build detailed structure for each account
    account_structure = {}
    for account_id in available_accounts:
        account_path = accounts_path / account_id
        if account_path.exists():
            services = {}
            for service_dir in account_path.iterdir():
                if service_dir.is_dir():
                    service_name = service_dir.name
                    resource_types = {}

                    # For each service, list resource types and count
                    for resource_type_dir in service_dir.iterdir():
                        if resource_type_dir.is_dir():
                            resource_type = resource_type_dir.name
                            # Count resources
                            resource_count = len([r for r in resource_type_dir.iterdir() if r.is_dir()])
                            resource_types[resource_type] = {
                                "count": resource_count,
                                "path": str(resource_type_dir.relative_to(data_path))
                            }

                    if resource_types:
                        services[service_name] = resource_types

            if services:
                account_structure[account_id] = services

    return {
        "data_directory": data_directory,
        "partition": partition_name,
        "partition_path": partition_rel_path,
        "accounts": available_accounts,
        "organizations": available_orgs,
        "indexes": available_indexes,
        "account_structure": account_structure,
    }


def read_iam_file_internal(data_directory: str, file_path: str, read_metadata: bool = True) -> Dict[str, Any]:
    """
    Internal function to read an IAM data file or list directory contents.

    Args:
        data_directory: Absolute path to the IAM data directory
        file_path: Relative path to the file/directory from data_directory
        read_metadata: If True and path is a directory with resource subdirs, read their metadata.json files

    Returns:
        Dict containing the file content or directory listing
    """
    data_path = Path(data_directory)

    # Construct full path
    full_path = data_path / file_path

    # Security check - ensure the path is within data_directory
    try:
        full_path = full_path.resolve()
        data_path = data_path.resolve()
        if not str(full_path).startswith(str(data_path)):
            raise ValueError(f"Path is outside data directory: {file_path}")
    except Exception as e:
        raise ValueError(f"Invalid path: {e}")

    # Check if path exists
    if not full_path.exists():
        raise ValueError(f"Path not found: {file_path}")

    # Handle directory
    if full_path.is_dir():
        # List directory contents
        items = []
        for item in full_path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "path": str((Path(file_path) / item.name))
            })

        result = {
            "file_path": file_path,
            "content_type": "directory",
            "items": items,
            "count": len(items)
        }

        # If read_metadata is True and items are directories (resource instances),
        # try to read metadata.json from each
        if read_metadata and items and all(item["type"] == "directory" for item in items):
            metadata_list = []
            for item in items[:100]:  # Limit to first 100 items
                metadata_path = Path(file_path) / item["name"] / "metadata.json"
                try:
                    metadata_file = data_path / metadata_path
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            metadata_list.append({
                                "resource_name": item["name"],
                                "metadata": metadata
                            })
                except Exception:
                    # Skip if metadata can't be read
                    pass

            if metadata_list:
                result["resources"] = metadata_list

        return result

    # Handle file
    try:
        with open(full_path, 'r') as f:
            content = f.read()

        # Try to parse as JSON
        try:
            parsed_content = json.loads(content)
            return {
                "file_path": file_path,
                "content_type": "json",
                "content": parsed_content
            }
        except json.JSONDecodeError:
            # Return as text if not JSON
            return {
                "file_path": file_path,
                "content_type": "text",
                "content": content
            }
    except Exception as e:
        raise ValueError(f"Error reading file: {e}")


def build_query_iam_data_response(
    data_directory: str,
    query: str,
    agent_instructions: str,
    focus_accounts: Optional[List[str]] = None,
    focus_services: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Build a comprehensive response for query_iam_data tool.

    Args:
        data_directory: Absolute path to the IAM data directory
        query: User's natural language query
        agent_instructions: Agent instructions content
        focus_accounts: Optional list of account IDs to limit analysis to
        focus_services: Optional list of services to focus on

    Returns:
        Dict containing the complete response
    """
    # Get the data structure using internal function
    structure = get_iam_data_structure_internal(data_directory, focus_accounts)

    # Extract partition info
    partition_path = structure.get("partition_path", "aws/aws")

    # Read all index files for quick lookups
    index_files = {}
    for index_name in structure.get("indexes", []):
        try:
            index_path = f"{partition_path}/indexes/{index_name}"
            file_data = read_iam_file_internal(data_directory, index_path)
            index_files[index_name] = file_data.get("content")
        except Exception as e:
            index_files[index_name] = f"Error reading index: {str(e)}"

    # Build comprehensive response
    return {
        "success": True,
        "query": query,
        "partition_info": {
            "partition": structure.get("partition", "aws"),
            "partition_path": partition_path,
            "note": "Use this partition path in all file paths. Replace <partition> placeholder with this value."
        },
        "agent_instructions": agent_instructions,
        "data_structure": structure,
        "index_files": index_files,
        "analysis_guidance": (
            "ANALYSIS INSTRUCTIONS:\n\n"
            "1. Review the agent_instructions to understand the data structure and analysis patterns\n"
            "2. Check partition_info to see which AWS partition your data uses\n"
            "3. Examine data_structure to see available accounts, services, and resources\n"
            "4. Use index_files for quick lookups (principals-to-trust-policies, accounts-to-orgs, etc.)\n"
            "5. If you need to read specific resource files, note their paths from data_structure\n"
            "6. For deeper analysis, you can call read_iam_file with specific file paths\n"
            "7. Do not try to read the filesystem paths directly\n"
            f"8. Use '{partition_path}' as your partition path in all file paths\n\n"
            f"Query to answer: {query}\n\n"
            "Please analyze the provided data and answer the query. "
            "If you need additional files, you can request them using read_iam_file tool."
        ),
        "suggestions": {
            "available_tools": ["read_iam_file", "get_iam_data_structure"],
            "example_paths": [
                f"{partition_path}/accounts/{structure['accounts'][0]}/iam/user/[username]/metadata.json" if structure.get('accounts') else None,
                f"{partition_path}/accounts/{structure['accounts'][0]}/iam/role/[rolename]/metadata.json" if structure.get('accounts') else None,
                f"{partition_path}/organizations/[org-id]/metadata.json" if structure.get('organizations') else None,
            ]
        }
    }
