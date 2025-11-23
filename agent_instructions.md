> Note for human reader: This is based on github.com/cloud-copilot/iam-collect/blob/main/docs/AgentInstructions.md

# AI Agent Instructions: iam-collect Data Analysis

## Available MCP Tools for Direct IAM Data Analysis

This MCP server exposes three tools for direct IAM data analysis that can be used by an AI agent:

1. **`query_iam_data(query, focus_accounts, focus_services)`**: Primary analysis tool that automatically:
   - Returns the complete data structure showing all accounts, services, and resources
   - Reads and provides all index files (principals-to-trust-policies, accounts-to-orgs, etc.)
   - Includes these agent instructions for reference
   - Suggests relevant file paths for deeper analysis
   - Use this as your starting point for any IAM query

2. **`read_iam_file(file_path, read_metadata=True)`**: Reads specific files or directories:
   - For files: returns parsed JSON content or raw text
   - For directories: lists contents and optionally reads metadata.json from all subdirectories
   - Automatically retrieves up to 100 resources when reading resource directories
   - Use this when you need specific files beyond what query_iam_data provides

3. **`get_iam_data_structure(focus_accounts)`**: Returns just the folder structure:
   - Shows available accounts, services, resource types, and counts
   - Lightweight alternative when you only need to understand what data exists
   - Use this for quick structure checks without reading file contents

## Core Data Organization

The iam-collect system organizes AWS IAM data in a hierarchical filesystem structure. Data lives under `aws/<partition>/` where partitions include 'aws', 'aws-cn', or 'aws-us-gov'. Within each partition, "accounts" contain service-specific resources, while "organizations" holds AWS Organizations metadata.

## Key Directory Patterns

Account resources follow this pattern: `accounts/<account-id>/<service>/[region]/[resource-type]/<resource-id>/`. For example, an IAM role might be found at `accounts/123456789012/iam/role/myrole/`. Regional services include location information, while global services omit it.

Organizations data mirrors this structure: `organizations/<org-id>/` contains metadata, accounts listings, organizational unit hierarchies, Service Control Policies, and Resource Control Policies.

## File Types and Contents

Each resource directory contains standardized JSON files:
- **metadata.json**: Core resource information including ARN, name, and creation timestamp
- **policy.json**: Resource-based policies for S3 buckets, Lambda functions, etc.
- **trust-policy.json**: IAM role trust relationships (principal assumptions)
- **inline-policies.json**: Inline policies attached to IAM entities
- **tags.json**: Resource tags
- **service-specific files**: encryption.json, bpa.json (Block Public Access)

## Path Encoding Rules

Resource identifiers in filesystem paths are URL-encoded and lowercased. For instance, `aws-service-role/sso.amazonaws.com/AWSServiceRoleForSSO` becomes `aws-service-role%2fsso.amazonaws.com%2fawsserviceroleforSSO`. Colons and forward slashes in RAM filenames convert to hyphens.

## Pre-built Search Indexes

The `indexes/` directory provides efficient lookups. **Note: `query_iam_data` automatically reads and provides all index files**, so you typically don't need to read them separately:

- **principals-to-trust-policies.json**: Maps principals to roles trusting them (useful for cross-account analysis)
- **accounts-to-orgs.json**: Account ID to organization mappings
- **buckets-to-accounts.json**: S3 bucket to account associations
- **apigateways-to-accounts.json**: API Gateway resource mappings
- **vpcs.json**: VPC information across accounts

To access index files manually, use `read_iam_file("<partition>/indexes/<index-name>.json")`.

## Common Analysis Workflows

**Note**: In all examples below, `<partition>` represents your AWS partition path (e.g., `aws/aws`, `aws-cn/aws-cn`, or `aws-us-gov/aws-us-gov`). Check the `partition_info` in your `query_iam_data` response to see which partition your data uses.

### Finding Overly Permissive Access

To identify overly permissive access, first examine the `index_files` provided by `query_iam_data` for initial insights. Then use `read_iam_file` to scan specific trust-policy.json files (e.g., `<partition>/accounts/<account-id>/iam/role/<role-name>/trust-policy.json`) for principals matching `"*"` or containing wildcards. Similarly, check inline-policies.json and policy.json files for statements with `"Resource": "*"`. Use `read_iam_file` with directory paths like `<partition>/accounts/<account-id>/iam/role` to retrieve all role metadata and their associated policies at once. These patterns indicate resources accessible to any principal or granting access to all resources.

### Cross-Account Analysis

The `query_iam_data` tool automatically provides the principals-to-trust-policies index file for fast lookups of cross-account trusts. Examine this index to identify roles that trust external principals. To investigate specific trust relationships, use `read_iam_file` to access trust-policy.json files directly (e.g., `<partition>/accounts/<account-id>/iam/role/<role-name>/trust-policy.json`). Extract account IDs from principal ARNs in the trust policies to identify external account relationships and potential cross-account access paths.

### Organization Policy Review

To review organization policies, use `read_iam_file` to load organization metadata from `<partition>/organizations/<org-id>/metadata.json`, accounts listings from `<partition>/organizations/<org-id>/accounts.json`, and structure hierarchies from `<partition>/organizations/<org-id>/structure.json`. Then examine Service Control Policies by reading files from the `<partition>/organizations/<org-id>/scps/` directory to understand authorization guardrails and administrative delegation. The accounts-to-orgs index (provided by `query_iam_data`) can help map accounts to their organizational units.

### Resource Enumeration

To enumerate resources, first examine the `data_structure` provided by `query_iam_data` which shows available services and resource types for each account. Use `read_iam_file` with service directory paths (e.g., `<partition>/accounts/<account-id>/s3/bucket`) to list resources of that type and automatically retrieve their metadata.json files. For regional services, navigate to region-specific paths. Check the metadata's `available_data` field to see what additional files exist for each resource (policy.json, trust-policy.json, tags.json, etc.), then use `read_iam_file` to access them as needed.

### List IAM Principals

To enumerate IAM principals (users, roles, groups) across accounts, navigate to `<partition>/accounts/<account-id>/iam/` and list subdirectories for each principal type. For users, explore `iam/user/`; for roles, use `iam/role/`; for groups, check `iam/group/`. Each principal has its own subdirectory containing `metadata.json` with core identity information (ARN, name, creation date), `inline-policies.json` for directly attached policies, and `tags.json` for resource tags. Use the `read_iam_file` tool with the principal type directory path (e.g., `<partition>/accounts/123456789012/iam/user`) to automatically retrieve metadata for all principals of that type.

## Common Path Patterns (Quick Reference)

**Important**: Replace `<partition>` with your AWS partition. The `query_iam_data` response includes the detected partition in `partition_info`. Common values:
- Standard AWS: `aws/aws`
- AWS China: `aws-cn/aws-cn`
- AWS GovCloud: `aws-us-gov/aws-us-gov`

Use these patterns with `read_iam_file`:

```
# IAM Resources
<partition>/accounts/<account-id>/iam/user                          # All IAM users
<partition>/accounts/<account-id>/iam/role                          # All IAM roles
<partition>/accounts/<account-id>/iam/group                         # All IAM groups
<partition>/accounts/<account-id>/iam/user/<username>/metadata.json # Specific user
<partition>/accounts/<account-id>/iam/role/<rolename>/trust-policy.json # Role trust policy

# Other Services
<partition>/accounts/<account-id>/s3/bucket                         # All S3 buckets
<partition>/accounts/<account-id>/lambda/us-east-1/function         # Lambda functions (regional)

# Organizations
<partition>/organizations/<org-id>/metadata.json                    # Organization info
<partition>/organizations/<org-id>/accounts.json                    # Organization accounts
<partition>/organizations/<org-id>/structure.json                   # OU hierarchy

# Indexes (auto-provided by query_iam_data)
<partition>/indexes/principals-to-trust-policies.json               # Principal trust mappings
<partition>/indexes/accounts-to-orgs.json                           # Account-to-org mappings
```

## Error Handling Considerations

Not all resources possess all file types—some roles lack inline policies, and certain resources have no tags. Handle JSON parsing failures gracefully. Verify ARNs across metadata and policy files match, and remember that all filesystem paths use lowercase regardless of original casing.

## Performance Optimization Tips

1. **Start with `query_iam_data`**: It provides index files and data structure in one call, avoiding multiple round trips
2. **Use index files first**: The automatically-provided index files (principals-to-trust-policies, accounts-to-orgs, etc.) offer fast lookups before reading individual files
3. **Leverage directory reading**: When using `read_iam_file` on resource directories (e.g., `aws/aws/accounts/<id>/iam/user`), it automatically reads up to 100 metadata files at once
4. **Read specific files only when needed**: Don't read files speculatively; use the `data_structure` to identify what exists first
5. **Batch related queries**: If analyzing multiple accounts, use `focus_accounts` parameter to limit scope
6. **Check `available_data` field**: In metadata.json files, this field shows what additional files exist, preventing failed read attempts
