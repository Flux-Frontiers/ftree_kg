# FTreeKG MCP Setup & Verification

Set up the MCP servers for the FTreeKG repository and configure them for use with Claude Code and/or Claude Desktop. FTreeKG exposes two MCP servers: **pycodekg** (code knowledge graph) and **dockg** (documentation knowledge graph). Execute the following steps in sequence.

## Command Argument Handling

**Usage:**
- `/setup-mcp` — Interactive mode; prompts for the target repository path
- `/setup-mcp /path/to/repo` — Set up MCP for the specified FTreeKG repository

---

## Step 0: Resolve the Target Repository

1. If a path argument was provided, use it as `REPO_ROOT`.
2. If no argument was provided, ask the user:
   > "Which FTreeKG repository do you want to set up? Please provide the absolute path."
3. Verify the path exists and contains the package source:
   ```bash
   ls "$REPO_ROOT/src/ftree_kg/__init__.py"
   ```
4. If not found, stop and report — the path may not be an FTreeKG repo.

All artifact paths default relative to `REPO_ROOT`:
- `FILETREEKG_DB` → `$REPO_ROOT/.filetreekg/graph.sqlite`
- `FILETREEKG_VECTORS` → `$REPO_ROOT/.filetreekg/vectors.sqlite`
- `PYCODEKG_DB` → `$REPO_ROOT/.pycodekg/graph.sqlite`
- `DOCKG_DB` → `$REPO_ROOT/.dockg/graph.sqlite`

---

## Step 1: Verify Installation

All packages are managed via Poetry. Confirm the key entry points are available:

```bash
cd "$REPO_ROOT"
poetry run ftreekg --version
poetry run pycodekg --version
poetry run dockg-mcp --help | head -5
```

If any command fails:
- Check `poetry install --all-extras` has been run
- Confirm `.venv/` exists: `ls "$REPO_ROOT/.venv/bin/ftreekg"`
- If missing, instruct the user to run `./scripts/setup.sh` or `poetry install --all-extras`

---

## Step 2: Build the FTreeKG Index

Build the filesystem tree knowledge graph (SQLite + sqlite-vec) under `.filetreekg/`.

1. Check whether the index already exists:
   ```bash
   ls -lh "$REPO_ROOT/.filetreekg/graph.sqlite" 2>/dev/null
   ```

2. If it exists, ask the user:
   > "A FTreeKG index already exists at `$REPO_ROOT/.filetreekg/graph.sqlite`. Rebuild it (wipe), or keep it?"
   - **Wipe**: proceed (default wipes)
   - **Keep**: skip to Step 3

3. Build the index (default wipes existing):
   ```bash
   cd "$REPO_ROOT" && poetry run ftreekg build
   ```
   To keep existing data:
   ```bash
   cd "$REPO_ROOT" && poetry run ftreekg build --no-wipe
   ```

4. Verify the index was created:
   ```bash
   sqlite3 "$REPO_ROOT/.filetreekg/graph.sqlite" "SELECT COUNT(*) FROM nodes; SELECT COUNT(*) FROM edges;"
   ```

5. Report node and edge counts. If both are zero, warn — the repo may have no indexable paths.

---

## Step 3: Build the PyCodeKG Index

Build the Python code knowledge graph under `.pycodekg/`.

1. Check whether the index exists:
   ```bash
   ls -lh "$REPO_ROOT/.pycodekg/graph.sqlite" 2>/dev/null
   ```

2. If it exists and the user chose to keep the FTreeKG index (Step 2), ask:
   > "A PyCodeKG index already exists at `$REPO_ROOT/.pycodekg/graph.sqlite`. Rebuild it?"
   - **Yes**: proceed
   - **No**: skip to Step 4

3. Build (always wipes):
   ```bash
   cd "$REPO_ROOT" && poetry run pycodekg build --repo .
   ```

4. Verify:
   ```bash
   sqlite3 "$REPO_ROOT/.pycodekg/graph.sqlite" "SELECT COUNT(*) FROM nodes; SELECT COUNT(*) FROM edges;"
   ```

5. Report the node and edge counts.

---

## Step 4: Build the DocKG Index

Build the documentation knowledge graph under `.dockg/`.

1. Check whether the index exists:
   ```bash
   ls -lh "$REPO_ROOT/.dockg/graph.sqlite" 2>/dev/null
   ```

2. If it exists and the user chose to keep the prior indices, ask:
   > "A DocKG index already exists at `$REPO_ROOT/.dockg/graph.sqlite`. Rebuild it?"
   - **Yes**: proceed
   - **No**: skip to Step 5

3. Build:
   ```bash
   cd "$REPO_ROOT" && poetry run dockg build --repo . --wipe
   ```

4. Verify:
   ```bash
   sqlite3 "$REPO_ROOT/.dockg/graph.sqlite" "SELECT COUNT(*) FROM nodes; SELECT COUNT(*) FROM edges;"
   ```

5. Report node and edge counts.

---

## Step 5: Smoke-Test the Query Pipeline

Quick end-to-end test before configuring any agent.

1. Test FTreeKG query:
   ```bash
   cd "$REPO_ROOT" && poetry run ftreekg query "Python source files"
   ```

2. Test PyCodeKG query:
   ```bash
   cd "$REPO_ROOT" && poetry run pycodekg query "module structure"
   ```

3. Test DocKG query:
   ```bash
   cd "$REPO_ROOT" && poetry run dockg query "installation"
   ```

4. If any command errors, diagnose and report the issue before proceeding.

---

## Step 6: Configure MCP Clients

Configure the per-repo `.mcp.json` (Claude Code / Kilo Code) and optionally Claude Desktop.

### MCP config by agent — quick reference

| Agent | Config file | Per-repo? | Key name |
|-------|-------------|-----------|----------|
| **GitHub Copilot** | `.vscode/mcp.json` | ✅ Yes | `"servers"` |
| **Kilo Code** | `.mcp.json` (project root) | ✅ Yes | `"mcpServers"` |
| **Claude Code** | `.mcp.json` (project root) | ✅ Yes | `"mcpServers"` |
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` | ❌ Global only | `"mcpServers"` |

> ⚠️ **Do NOT add ftreekg MCP entries to any global settings file.**
> Global files are shared across all windows — hardcoded paths will point every window to the same repo.

### 6a: Claude Code / Kilo Code (.mcp.json)

1. Read the existing file:
   ```bash
   cat "$REPO_ROOT/.mcp.json" 2>/dev/null
   ```

2. The correct entries are:
   ```json
   {
     "mcpServers": {
       "pycodekg": {
         "command": "poetry",
         "args": [
           "run", "pycodekg", "mcp",
           "--repo", "<REPO_ROOT>"
         ],
         "env": {
           "POETRY_VIRTUALENVS_IN_PROJECT": "false"
         }
       },
       "dockg": {
         "command": "poetry",
         "args": [
           "run", "dockg-mcp",
           "--repo", "<REPO_ROOT>"
         ],
         "env": {
           "POETRY_VIRTUALENVS_IN_PROJECT": "false"
         }
       }
     }
   }
   ```
   Replace `<REPO_ROOT>` with the absolute path.

3. Check whether `pycodekg` or `dockg` entries already exist.
   - If they exist with wrong paths, replace them.
   - Merge into the existing `mcpServers` object — do not overwrite other entries.

4. **Verify no stale `codekg` entry exists** — the old entry name was `codekg` (wrong binary). Remove it if present.

5. After saving, restart Claude Code to pick up the new config.

### 6b: GitHub Copilot (.vscode/mcp.json)

Note the format differences vs `.mcp.json`:
- Uses `"servers"` (not `"mcpServers"`)
- Requires `"type": "stdio"`

1. Check if the file exists:
   ```bash
   cat "$REPO_ROOT/.vscode/mcp.json" 2>/dev/null
   ```

2. The correct entries:
   ```json
   {
     "servers": {
       "pycodekg": {
         "type": "stdio",
         "command": "poetry",
         "args": [
           "run", "pycodekg", "mcp",
           "--repo", "<REPO_ROOT>"
         ],
         "env": {
           "POETRY_VIRTUALENVS_IN_PROJECT": "false"
         }
       },
       "dockg": {
         "type": "stdio",
         "command": "poetry",
         "args": [
           "run", "dockg-mcp",
           "--repo", "<REPO_ROOT>"
         ],
         "env": {
           "POETRY_VIRTUALENVS_IN_PROJECT": "false"
         }
       }
     }
   }
   ```

3. Merge into the existing `servers` object — do not overwrite other entries.

4. After saving, VS Code will prompt to trust the MCP servers — click **Trust** to activate.

### 6c: Claude Desktop (claude_desktop_config.json)

Claude Desktop does not have Poetry on its PATH. Use the absolute venv binary path.

1. Get the venv path:
   ```bash
   cd "$REPO_ROOT" && poetry env info --path
   ```
   Binaries are at `<venv_path>/bin/pycodekg` and `<venv_path>/bin/dockg-mcp`.

2. Config path (macOS): `~/Library/Application Support/Claude/claude_desktop_config.json`

3. The correct entries (use absolute venv path):
   ```json
   "pycodekg": {
     "command": "<venv_path>/bin/pycodekg",
     "args": ["mcp", "--repo", "<REPO_ROOT>"]
   },
   "dockg": {
     "command": "<venv_path>/bin/dockg-mcp",
     "args": ["--repo", "<REPO_ROOT>"]
   }
   ```

4. Merge into the existing `mcpServers` object — do not overwrite other entries.

5. **Remove any stale `codekg` entry** — the binary `codekg` does not exist in this venv.

6. Restart Claude Desktop to activate.

---

## Step 7: Final Report

```
✓ FTreeKG index:    $REPO_ROOT/.filetreekg/graph.sqlite  (<N> nodes, <M> edges)
✓ PyCodeKG index:   $REPO_ROOT/.pycodekg/graph.sqlite       (<N> nodes, <M> edges)
✓ DocKG index:      $REPO_ROOT/.dockg/graph.sqlite        (<N> nodes, <M> edges)
✓ Smoke test:       passed
✓ .mcp.json:        $REPO_ROOT/.mcp.json  (pycodekg + dockg entries)

Restart Claude Code / Claude Desktop to activate the MCP servers.

Available tools once active:

  pycodekg server:
    • graph_stats()              — codebase size and shape
    • query_codebase(q)          — semantic + structural code search
    • pack_snippets(q)           — source-grounded code snippets
    • callers(node_id)           — find all callers of a function
    • explain(node_id)           — natural-language explanation of a node
    • centrality(top)            — structural importance ranking

  dockg server:
    • graph_stats()              — doc corpus size
    • query_docs(q)              — semantic search over documentation
    • pack_docs(q)               — doc snippets for LLM context
    • get_node(node_id)          — single doc node lookup

Suggested first queries after restart:
  pycodekg: graph_stats()
  dockg:    graph_stats()
```

---

## Important Rules

- **Do NOT modify source files** in the target repository.
- **Do NOT run `git commit`** or any destructive git operations.
- Use **absolute paths** everywhere — relative paths will break MCP clients.
- Always use `poetry run` for CLI calls — the packages are not installed globally.
- The `codekg-mcp` binary does **not** exist in this venv — use `pycodekg mcp` instead.
- If any step fails, stop and report the error clearly before proceeding.

---

## Rebuilding After Code Changes

When the codebase or docs change, rebuild the affected indices:

```bash
# Rebuild FTreeKG index
cd "$REPO_ROOT" && poetry run ftreekg build

# Rebuild PyCodeKG index (always wipes)
cd "$REPO_ROOT" && poetry run pycodekg build --repo .

# Rebuild DocKG index
cd "$REPO_ROOT" && poetry run dockg build --repo . --wipe
```

MCP client configs do not need to change — they point to the same file paths.
