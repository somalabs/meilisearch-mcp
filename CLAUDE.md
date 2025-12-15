# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 IMPORTANT: Development Workflow Guidelines

**ALL coding agents MUST follow these mandatory guidelines for every task.**

### 🔄 Fresh Start Protocol

**BEFORE starting ANY new task or issue:**

1. **Always start from latest main**:
   ```bash
   git checkout main
   git pull origin main  # Ensure you have the latest changes
   git checkout -b feature/your-branch-name  # Create new branch
   ```

2. **Verify clean state**:
   ```bash
   git status  # Should show clean working directory
   ```

3. **Never carry over unrelated changes** from previous work
4. **Each task gets its own focused branch** from latest main

### 🎯 Focused Development Rules

**ONLY make changes directly related to the specific task/issue:**

- ✅ **DO**: Add/modify code that solves the specific issue
- ✅ **DO**: Add focused tests for the specific functionality
- ✅ **DO**: Update documentation if specifically required
- ❌ **DON'T**: Include formatting changes to unrelated files
- ❌ **DON'T**: Add comprehensive test suites unless specifically requested
- ❌ **DON'T**: Refactor unrelated code
- ❌ **DON'T**: Include previous work from other branches

### 📋 Task Assessment Phase

Before writing any code, determine scope:

1. **Read the issue/task carefully** - understand exact requirements
2. **Identify minimal changes needed** - what files need modification?
3. **Plan focused tests** - only for the specific functionality being added
4. **Avoid scope creep** - resist urge to "improve" unrelated code

### 🧪 Test-Driven Development (TDD) Approach

When tests are required for the specific task:

```bash
# 1. Write failing tests FIRST (focused on the issue)
python -m pytest tests/test_specific_issue.py -v  # Should fail

# 2. Write minimal code to make tests pass
# Edit ONLY files needed for the specific issue

# 3. Run tests to verify they pass
python -m pytest tests/test_specific_issue.py -v  # Should pass

# 4. Refactor if needed, but stay focused
```

### 📝 Commit Standards

**Each commit should be atomic and focused:**

```bash
# Format only the files you changed
black src/ tests/

# Run tests to ensure no regressions
python -m pytest tests/ -v

# Commit with descriptive message
git add src/specific_file.py tests/test_specific_file.py
git commit -m "Fix issue #X: Brief description of what was fixed"
```

### 🚫 What NOT to Include in PRs

- Formatting changes to files you didn't functionally modify
- Test files not related to your specific task
- Refactoring of unrelated code
- Documentation updates not specifically requested
- Code from previous branches or incomplete work

### ✅ PR Quality Checklist

Before creating PR, verify:
- [ ] Branch created from latest main
- [ ] Only files related to the specific issue are modified
- [ ] Tests pass and are focused on the issue
- [ ] Commit messages are clear and specific
- [ ] No unrelated formatting or code changes
- [ ] PR description clearly links to the issue being solved

**⚠️ PRs with unrelated changes will be rejected and must be redone.**

## Project Overview

This is a **Model Context Protocol (MCP) server** for Meilisearch, allowing LLM interfaces like Claude to interact with Meilisearch search engines. The project implements a Python-based MCP server using **FastMCP** that provides comprehensive tools for index management, document operations, search functionality, and system monitoring.

## Development Commands

### Environment Setup
```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Install development dependencies
uv pip install -r requirements-dev.txt
```

### Testing (MANDATORY for all development)
```bash
# Run all tests (required before any commit)
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_mcp_client.py -v

# Run tests with coverage (required for new features)
python -m pytest --cov=src tests/

# Watch mode for development (optional)
pytest-watch tests/
```

### Code Quality (MANDATORY before commit)
```bash
# Format code (required before commit)
black src/ tests/

# Check formatting without applying
black --check src/ tests/

# Run the MCP server locally for testing
python -m src.meilisearch_mcp

# Test with MCP Inspector
npx @modelcontextprotocol/inspector python -m src.meilisearch_mcp
```

### Prerequisites for Testing
- **Meilisearch server** must be running on `http://localhost:7700`
- **Docker option**: `docker run -d -p 7700:7700 getmeili/meilisearch:v1.6`
- **Node.js** for MCP Inspector testing

## Architecture

### FastMCP-Based Design

The codebase uses **FastMCP** for a clean, decorator-based tool implementation:

```
src/meilisearch_mcp/
├── server.py           # FastMCP instance + HTTP/SSE endpoints
├── context.py          # ServerContext for shared state management
├── tools/              # Organized tool modules
│   ├── __init__.py     # Tool registration
│   ├── connection.py   # Connection management tools
│   ├── indexes.py      # Index operation tools
│   ├── documents.py    # Document operation tools
│   ├── search.py       # Search tool
│   ├── settings.py     # Settings tools
│   ├── tasks.py        # Task management tools
│   ├── keys.py         # API key tools
│   ├── monitoring.py   # Health/monitoring tools
│   └── chat.py         # Chat completion tools
├── client.py           # MeilisearchClient
├── chat.py             # ChatManager
├── documents.py        # DocumentManager
├── indexes.py          # IndexManager
├── keys.py             # KeyManager
├── logging.py          # MCPLogger
├── monitoring.py       # MonitoringManager
├── settings.py         # SettingsManager
└── tasks.py            # TaskManager
```

### Modular Manager Design
Business logic is organized into specialized managers:

```
MeilisearchClient
├── IndexManager      - Index creation, listing, deletion
├── DocumentManager   - Document CRUD operations 
├── SettingsManager   - Index configuration management
├── TaskManager       - Asynchronous task monitoring
├── KeyManager        - API key management
└── MonitoringManager - Health checks and system metrics
```

### MCP Server Integration
- **FastMCP Server**: Uses `FastMCP` class with decorator-based tool registration
- **Tool Registration**: All tools defined with `@mcp.tool()` decorator for automatic schema generation
- **Shared Context**: `ServerContext` class provides shared state via `get_context()`
- **Error Handling**: Comprehensive exception handling with logging through `MCPLogger`
- **Dynamic Configuration**: Runtime connection settings updates via context

### Key Components

#### Tool Registration Pattern (FastMCP)
All MCP tools follow the FastMCP decorator pattern:
```python
from fastmcp import FastMCP
from ..context import get_context

def register_tools(mcp):
    @mcp.tool(name="tool-name")
    def my_tool(param: str) -> str:
        """Tool description for auto-generated schema."""
        ctx = get_context()
        result = ctx.meili_client.do_something(param)
        return f"Result: {result}"
```

#### ServerContext
The `ServerContext` class in `context.py` provides:
- Lazy initialization of `MeilisearchClient` and `ChatManager`
- Dynamic connection settings updates
- Shared state across all tools

#### Search Architecture
- **Single Index Search**: Direct search in specified index
- **Multi-Index Search**: Parallel search across all indices when no `indexUid` provided
- **Result Aggregation**: Smart filtering of results with hits

#### Connection Management
- **Runtime Configuration**: Dynamic URL and API key updates via `ServerContext`
- **Environment Variables**: `MEILI_HTTP_ADDR` and `MEILI_MASTER_KEY` for defaults
- **Connection State**: Maintained in context for session persistence

## Testing Strategy

### Test Structure
- **Integration Tests** (`test_mcp_client.py`): End-to-end MCP tool execution with real Meilisearch
- **Unit Tests** (`test_server.py`): Basic server instantiation and configuration

### Test Categories by Development Task

#### When Tests are REQUIRED:
- **New MCP Tools**: Add tests to `test_mcp_client.py` using `simulate_mcp_call()`
- **Existing Tool Changes**: Update corresponding test methods
- **Manager Class Changes**: Test through MCP tool integration
- **Bug Fixes**: Add regression tests to prevent reoccurrence
- **API Changes**: Update tests to reflect new interfaces

#### When Tests are OPTIONAL:
- **Documentation Updates**: README.md, CLAUDE.md changes
- **Code Formatting**: Black formatting, comment changes
- **Minor Refactoring**: Internal reorganization without behavior changes

### Tool Simulation Framework
Tests use `simulate_mcp_call()` function that:
- Directly invokes FastMCP tool manager
- Returns proper text content responses
- Provides comprehensive coverage of all 26 tools
- Enables fast test execution without MCP protocol complexity

### Test Isolation and Best Practices
- **Unique Index Names**: Timestamped index names prevent test interference
- **Cleanup Fixtures**: Automatic test environment cleanup after each test
- **Service Dependencies**: Tests require running Meilisearch instance
- **Test Naming**: Use descriptive test method names (e.g., `test_create_index_with_primary_key`)
- **Assertions**: Test both success cases and error handling
- **Coverage**: New tools must have comprehensive test coverage
- **Embedder Tests**: Tests requiring Meilisearch embedder configuration should be marked with `@pytest.mark.skip` decorator

## Environment Configuration

### Required Environment Variables
```bash
MEILI_HTTP_ADDR=http://localhost:7700  # Meilisearch server URL
MEILI_MASTER_KEY=your_master_key       # Optional: API key for authenticated instances
```

### Claude Desktop Integration
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "meilisearch": {
      "command": "uvx", 
      "args": ["-n", "meilisearch-mcp"]
    }
  }
}
```

### GitHub Actions Integration
The repository includes Claude Code integration via GitHub Actions:
- **Trigger**: Comments containing `@claude` on issues, PRs, or reviews
- **Workflow**: `.github/workflows/claude.yml` handles automated Claude responses
- **Permissions**: Read contents, write to pull requests and issues

## Available MCP Tools

### Core Categories (26 total)
- **Connection Management** (2): `get-connection-settings`, `update-connection-settings`
- **Index Operations** (3): `create-index`, `list-indexes`, `delete-index`
- **Document Management** (2): `get-documents`, `add-documents`
- **Search Capabilities** (1): `search`
- **Settings Control** (2): `get-settings`, `update-settings`
- **Task Monitoring** (3): `get-task`, `get-tasks`, `cancel-tasks`
- **API Key Management** (3): `get-keys`, `create-key`, `delete-key`
- **System Monitoring** (6): `health-check`, `get-version`, `get-stats`, `get-health-status`, `get-index-metrics`, `get-system-info`
- **Chat Completion** (4): `create-chat-completion`, `get-chat-workspaces`, `get-chat-workspace-settings`, `update-chat-workspace-settings`

### Search Tool Features
- **Flexible Targeting**: Search specific index or all indices
- **Rich Parameters**: Filtering, sorting, pagination support
- **Hybrid Search**: Support for combining keyword and semantic search with `semanticRatio` parameter
- **Vector Search**: Custom vector support for semantic similarity search
- **Result Formatting**: JSON formatted responses with proper serialization
- **Error Resilience**: Graceful handling of index-specific failures

## Development Notes

### Dependencies
- **FastMCP**: `fastmcp>=2.0.0` for MCP server framework with decorator-based tools
- **HTTP Client**: `httpx>=0.28.1` for async HTTP operations
- **Data Validation**: `pydantic>=2.11.7` for structured data handling
- **HTTP Server**: `aiohttp>=3.9.0` for HTTP/SSE endpoints

### Logging Infrastructure
- **Structured Logging**: JSON-formatted logs with contextual information
- **Log Directory**: `~/.meilisearch-mcp/logs/` for persistent logging
- **Error Tracking**: Comprehensive error logging with tool context

### HTTP/SSE Support
The server provides HTTP endpoints for Cloud Run deployment:
- **Health Checks**: `/health`, `/ready` endpoints
- **MCP Endpoints**: `/mcp`, `/sse`, `/v1/sse` for SSE connections
- **Message Endpoints**: `/message`, `/v1/message` for POST requests

### Hybrid Search Implementation
- **Dependency**: Requires `meilisearch>=0.34.0` for stable AI-powered search features
- **Parameters**: `hybrid` object with `semanticRatio` (0.0-1.0) and `embedder` (required)
- **Vector Support**: Custom vectors can be provided via `vector` parameter
- **Testing**: Hybrid search tests require embedder configuration in Meilisearch
- **Backward Compatibility**: All hybrid search parameters are optional to maintain compatibility
