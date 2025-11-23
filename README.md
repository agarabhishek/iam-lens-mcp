# IAM Lens MCP Server

An MCP (Model Context Protocol) server that provides AWS IAM analysis capabilities using the [iam-lens](https://github.com/cloud-copilot/iam-lens) tool. This server enables AI assistants like Claude, Cursor, and others to interact with `iam-lens` through natural language.

## Live Demo

https://github.com/user-attachments/assets/402b5fa9-3138-450d-ab33-552601d69c36

## Features

- **Dual Analysis Modes**: Fast CLI-based policy simulation AND flexible AI-powered data exploration
- **Multi-Partition Support**: Automatically detects and works with AWS, AWS China, and AWS GovCloud partitions
- **Natural Language Queries**: Ask questions in plain English about your IAM setup
- **Comprehensive Coverage**: Analyze users, roles, groups, policies, S3 buckets, Lambda functions, and more
- **Security Auditing**: Find overly permissive access, cross-account trusts, and security issues
- **Organization Analysis**: Review AWS Organizations structure, SCPs, and account hierarchies
- **Efficient Data Access**: Pre-built indexes for fast lookups, automatic metadata retrieval for directories

## MCP Tools

This MCP server provides two types of IAM analysis capabilities:

### 1. iam-lens CLI Tools (Deterministic Analysis)

These tools use the `iam-lens` CLI for fast, deterministic IAM policy evaluation:

- **`simulate_iam_request`**: Test if a principal can perform specific actions on resources
- **`who_can_access_resource`**: Identify which principals have access to a specific resource with certain permissions
- **`principal_can`**: Get a consolidated view of all permissions for a specific principal (user or role)

### 2. Direct IAM Data Analysis Tools (Flexible, AI-Powered)

These tools provide direct access to collected IAM data for flexible, exploratory analysis:

- **`query_iam_data`**: Primary analysis tool that automatically provides data structure, index files, and agent instructions. Use this for complex questions about IAM setup, security posture, or custom queries.

- **`read_iam_file`**: Read specific IAM data files or directories. Supports both individual files and directory listings with automatic metadata retrieval.

- **`get_iam_data_structure`**: Get a quick overview of available accounts, services, and resources without reading file contents.

**When to use which:**
- Use **iam-lens CLI tools** for specific access checks and permission queries (fast, deterministic)
- Use **direct data analysis tools** for exploratory questions, security audits, and custom analysis (flexible, comprehensive)

## Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- [iam-lens](https://github.com/cloud-copilot/iam-lens) CLI tool

## Setup Instructions

### 1. Install Dependencies

```bash
# Install uv via Homebrew (recommended for Claude Desktop compatibility)
# This installs uv to /opt/homebrew/bin which is in the system PATH
brew install uv

# Setup iam-lens tool: https://github.com/cloud-copilot/iam-lens?tab=readme-ov-file#getting-started
## Setup iam-collect
npm install -g @cloud-copilot/iam-collect
iam-collect init
iam-collect download

## Setup iam-lens
npm install -g @cloud-copilot/iam-lens
```

### 2. Clone the MCP Server

```bash
# Clone this repository
git clone <repository-url>
cd iam-lens-mcp

# Note: No installation needed! uv will automatically create the virtual
# environment and install dependencies when Claude Desktop starts the server
```

### 3. Configure Claude Desktop

#### Step 1: Find your installation paths

```bash
# Navigate to your iam-lens-mcp directory and get the absolute path
cd /path/to/iam-lens-mcp
pwd

# Find the absolute path of your iam-collect.jsonc config file
# iam-collect.jsonrc file is created when you run `iam-collect init`
find ~ -name "iam-collect.jsonc" 2>/dev/null | head -1
```

#### Step 2: Edit Claude Desktop configuration

```bash
# macOS
~/Library/Application\ Support/Claude/claude_desktop_config.json

# Linux
~/.config/Claude/claude_desktop_config.json

# Windows
%APPDATA%\Claude\claude_desktop_config.json
```

#### Step 3: Add the MCP server configuration

```json
{
  "mcpServers": {
    "iam-lens-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/ABSOLUTE/PATH/TO/iam-lens-mcp",
        "python",
        "iam_lens_server.py"
      ],
      "env": {
        "COLLECT_CONFIGS": "/ABSOLUTE/PATH/TO/iam-collect.jsonc"
      }
    }
  }
}
```

**Replace the paths** with your actual paths from Step 1:
- `/ABSOLUTE/PATH/TO/iam-lens-mcp` → Your project directory
- `/ABSOLUTE/PATH/TO/iam-collect.jsonc` → Your IAM data config file

**Example configuration:**

```json
{
  "mcpServers": {
    "iam-lens-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/myuser/Tools/iam-lens-mcp",
        "python",
        "iam_lens_server.py"
      ],
      "env": {
        "COLLECT_CONFIGS": "/Users/myuser/Tools/iam-lens/iam-collect.jsonc"
      }
    }
  }
}
```

#### Step 4: Restart Claude Desktop

Close and reopen Claude Desktop for the changes to take effect.

#### Step 5: Verify the setup

In Claude Desktop, ask:
```
What MCP servers are connected?
```

You should see `iam-lens-mcp` in the list of available servers.

## Usage

Once configured, you can use prompts like these in your AI assistant:

### iam-lens CLI Tools (Fast, Deterministic)

#### Simulate IAM Request
```
Check if arn:aws:iam::123456789012:user/myuser can fetch the contents of the S3 bucket: arn:aws:s3:::mybucket/myfile.txt
```

#### Find Resource Access
```
Who can access the S3 bucket: arn:aws:s3:::mybucket?
```

#### Get Principal Permissions
```
Show me all permissions for arn:aws:iam::123456789012:role/MyRole
```

```
What can arn:aws:iam::123456789012:user/Alice do? Show condensed action lists.
```

### Direct IAM Data Analysis Tools (Flexible, Comprehensive)

#### Exploratory Questions
```
What IAM users exist across all accounts?
```

```
Which IAM roles trust external accounts?
```

```
List all S3 buckets and show which ones have public access policies
```

```
What are the most permissive IAM policies in my environment?
```

#### Security Audits
```
Find all IAM principals with AdministratorAccess
```

```
Show me all roles that can be assumed by EC2 instances
```

```
Which resources have overly permissive access (Resource: "*")?
```

#### Organization Analysis
```
Show me the AWS Organizations structure and Service Control Policies
```

```
What accounts are in my organization and what services do they use?
```

**Note**: The direct analysis tools automatically detect your AWS partition (aws, aws-cn, or aws-us-gov) and work seamlessly with all partitions.

## Configuration

### Environment Variables

- `COLLECT_CONFIGS`: Path to your `iam-collect.jsonc` configuration file

## Troubleshooting

### "Principal does not exist" Error / "Account not found" Error
- Ensure that `iam-collect.jsonc` is correctly configured and points to the right data directory
- Ensure that the path to `iam-collect.jsonc` is absolute
