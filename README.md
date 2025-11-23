# IAM Lens MCP Server

An MCP (Model Context Protocol) server that provides AWS IAM analysis capabilities using the [iam-lens](https://github.com/cloud-copilot/iam-lens) tool. This server enables AI assistants like Claude, Cursor, and others to interact with `iam-lens` through natural language.

## Live Demo

https://github.com/user-attachments/assets/402b5fa9-3138-450d-ab33-552601d69c36

## MCP Tools

The following capabilities of `iam-lens` are exposed via this MCP server:

- **IAM Request Simulation**: Test if a principal can perform specific actions on resources
- **Resource Access Discovery**: Identify which principals have access to a specific resource with certain permissions
- **Principal Permissions Analysis**: Get a consolidated view of all permissions for a specific principal (user or role)

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

Once configured, you can use the prompts like these in your AI assistant:

### Simulate IAM Request
```
Check if arn:aws:iam::123456789012:user/myuser can fetch the contents of the S3 bucket: arn:aws:s3:::mybucket/myfile.txt
```

### Find Resource Access
```
Who can access the S3 bucket: arn:aws:s3:::mybucket?
```

### Get Principal Permissions
```
Show me all permissions for arn:aws:iam::123456789012:role/MyRole
```

```
What can arn:aws:iam::123456789012:user/Alice do? Show condensed action lists.
```

## Configuration

### Environment Variables

- `COLLECT_CONFIGS`: Path to your `iam-collect.jsonc` configuration file

## Troubleshooting

### "Principal does not exist" Error / "Account not found" Error
- Ensure that `iam-collect.jsonc` is correctly configured and points to the right data directory
- Ensure that the path to `iam-collect.jsonc` is absolute
