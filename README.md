# IAM Lens MCP Server

An MCP (Model Context Protocol) server that provides AWS IAM analysis capabilities using the [iam-lens](https://github.com/cloud-copilot/iam-lens) tool. This server enables AI assistants like Claude, Cursor, and others to interact with `iam-lens` through natural language.

## Live Demo

## MCP Tools

The following capabilities of `iam-lens` are exposed via this MCP server:

- **IAM Request Simulation**: Test if a principal can perform specific actions on resources
- **Resource Access Discovery**: Identify which principals have access to a specific resource with certain permissions

## Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- [iam-lens](https://github.com/cloud-copilot/iam-lens) CLI tool

## Setup Instructions

### 1. Install Dependencies

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup iam-lens tool: https://github.com/cloud-copilot/iam-lens?tab=readme-ov-file#getting-started
## Setup iam-collect
npm install -g @cloud-copilot/iam-collect
iam-collect init
iam-collect download

## Setup iam-lens
npm install -g @cloud-copilot/iam-lens
```

### 2. Clone and Setup the MCP Server

```bash
# Clone this repository
git clone <repository-url>
cd iam-lens-mcp

# Create virtual environment and install dependencies
uv sync

# Install the package in development mode
uv pip install -e .
```

### 3. Configure IAM Data Collection

On running `iam-collect download`, a default `iam-collect.jsonc` configuration file is created. This file points to the directory where IAM data will be stored. You can modify the `path` in the `storage` section to specify where you want to store the collected IAM data. This file is important as it will be referenced by the MCP server to read IAM data.

```jsonc
{
  // The name of the configuration, used if you need to have multiple configurations.
  "name": "default config",
  "iamCollectVersion": "0.1.131",

  // Default storage is on the file system.
  "storage": {
    "type": "file",
    //If this starts with a '.', it is relative to the config file, otherwise it is an absolute path.
    "path": "~/TKTK/iam-data"
  }
}
```

> Note: The `path` value should be an absolute path to avoid issues when the MCP server runs in different environments.

### 4. Setup Configuration - Usage with AI Assistants

Add the MCP server to your Claude Code configuration:

#### For Claude:

**macOS**: Edit `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "iam-lens-mcp": {
      "command": "<Path to iam-lens-mcp>/.venv/bin/iam-lens-mcp>",
      "env": {
        "COLLECT_CONFIGS": "<Path to iam-collect.jsonc>"
      }
    }
  }
}
```

Example:

```json
{
  "mcpServers": {
    "iam-lens-mcp": {
      "command": "~/Tools/iam-lens-mcp/.venv/bin/iam-lens-mcp",
      "env": {
        "COLLECT_CONFIGS": "~/Tools/iam-lens-mcp/iam-collect.jsonc"
      }
    }
  }
}
```

## Usage

Once configured, you can use the prompts like these in your AI assistant:

### Simulate IAM Request
```
Check if arn:aws:iam::123456789012:user/myuser can perform get the S3 bucket arn:aws:s3:::mybucket/myfile.txt
```

### Find Resource Access
```
Who can access arn:aws:s3:::mybucket with s3:GetObject permission?
```

## Configuration

### Environment Variables

- `COLLECT_CONFIGS`: Path to your `iam-collect.jsonc` configuration file

## Troubleshooting

### "Principal does not exist" Error" / "Account not found" Error"
- Ensure that `iam-collect.jsonc` is correctly configured and points to the right data directory
- Ensure that the path to `iam-collect.jsonc` is absolute and the `storage.path` value in the config file is also absolute.