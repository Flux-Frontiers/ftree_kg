# Setup Project

Initialize a new project with Claude Copilot. This command only works on projects that haven't been set up yet.

## Step 1: Verify This Is a New Project

```bash
ls .mcp.json 2>/dev/null && echo "PROJECT_EXISTS" || echo "NEW_PROJECT"
```

**If PROJECT_EXISTS:**

Stop and tell the user:

---

**This project is already configured.**

Found `.mcp.json` - this project has already been set up with Claude Copilot.

To update this project with the latest Claude Copilot files, use:

```
/update-project
```

---

Then STOP. Do not continue.

**If NEW_PROJECT:** Continue to Step 2.

---

## Step 2: Verify Machine Setup

```bash
ls ~/.claude/copilot/mcp-servers/copilot-memory/dist/index.js 2>/dev/null && echo "MEMORY_OK" || echo "MEMORY_MISSING"
ls ~/.claude/copilot/mcp-servers/skills-copilot/dist/index.js 2>/dev/null && echo "SKILLS_OK" || echo "SKILLS_MISSING"
```

**If either MISSING:**

Tell user:

---

**Claude Copilot is not installed on this machine.**

Please complete machine setup first:

1. Clone the repository:
   ```bash
   mkdir -p ~/.claude
   cd ~/.claude
   git clone https://github.com/Everyone-Needs-A-Copilot/claude-copilot.git copilot
   ```

2. Open Claude Code in `~/.claude/copilot` and follow the setup instructions in `SETUP.md`

Then return here and run `/setup-project` again.

---

Then STOP.

---

## Step 3: Get Project Info

```bash
echo $HOME
pwd
basename $(pwd)
```

Store:
- `HOME_PATH` = result of $HOME
- `PROJECT_PATH` = result of pwd
- `PROJECT_NAME` = result of basename

---

## Step 4: Create Directory Structure

```bash
mkdir -p .claude/commands
mkdir -p .claude/agents
mkdir -p .claude/skills
```

---

## Step 5: Copy Project Commands

Only copy commands that belong at project level (protocol and continue):

```bash
cp ~/.claude/copilot/.claude/commands/protocol.md .claude/commands/
cp ~/.claude/copilot/.claude/commands/continue.md .claude/commands/
```

**Verify:**
```bash
ls .claude/commands/
```

Should show: `continue.md` and `protocol.md`

---

## Step 6: Copy Agents

```bash
cp ~/.claude/copilot/.claude/agents/*.md .claude/agents/
```

**Verify:**
```bash
ls .claude/agents/ | wc -l
```

Should show 12+ files.

---

## Step 7: Create .mcp.json with Template Variable Expansion

Read the template and expand variables automatically:

```bash
cat ~/.claude/copilot/templates/mcp.json
```

**Expand these variables:**

| Variable | Value | Example |
|----------|-------|---------|
| `$HOME` | User's home directory | `/Users/pabs` |
| `$PROJECT_PATH` | Current working directory | `/Users/pabs/Sites/my-app` |
| `$PROJECT_NAME` | Directory basename | `my-app` |
| `$COPILOT_PATH` | Claude Copilot location | `$HOME/.claude/copilot` |

**Process:**

1. Read template from `~/.claude/copilot/templates/mcp.json`
2. Replace all variables:
   - `$HOME` → actual home path (NO tilde)
   - `$PROJECT_PATH` → result of `pwd`
   - `$PROJECT_NAME` → result of `basename $(pwd)`
   - `$COPILOT_PATH` → `$HOME/.claude/copilot` (expanded)
3. Validate expansion (see validation below)
4. Write to `.mcp.json`

**CRITICAL:**
- All paths must be absolute (no `~` or `$HOME` in final output)
- No unexpanded variables (`$xxx`) in final file
- Verify JSON is valid

**Validation After Expansion:**

```bash
# Check for unexpanded variables
grep -E '\$[A-Z_]+' .mcp.json && echo "ERROR: Unexpanded variables found" || echo "Variables OK"

# Verify critical paths exist
ls -l "$HOME/.claude/copilot/mcp-servers/copilot-memory/dist/index.js" && echo "Memory server OK" || echo "Memory server MISSING"
ls -l "$HOME/.claude/copilot/mcp-servers/skills-copilot/dist/index.js" && echo "Skills server OK" || echo "Skills server MISSING"

# Validate JSON
node -e "JSON.parse(require('fs').readFileSync('.mcp.json', 'utf8'))" && echo "JSON valid" || echo "JSON INVALID"
```

**If validation fails:**

Report clear error with fix instructions:

```
ERROR: Template expansion failed

Variable: $COPILOT_PATH
Expected: ~/.claude/copilot/mcp-servers/copilot-memory/dist/index.js
Found: File does not exist

Fix: Run /setup from ~/.claude/copilot first to build MCP servers
```

---

## Step 8: Detect Knowledge

```bash
ls ~/.claude/knowledge/knowledge-manifest.json 2>/dev/null && echo "KNOWLEDGE_EXISTS" || echo "NO_KNOWLEDGE"
cat ~/.claude/knowledge/knowledge-manifest.json 2>/dev/null | grep '"name"' | head -1
```

Store:
- `KNOWLEDGE_STATUS` = "configured" or "not configured"
- `KNOWLEDGE_NAME` = from manifest (if exists)

---

## Step 9: Ask Project Details

Use AskUserQuestion to gather:

**Question 1:** "What's this project about?"
- Header: "Description"
- Let user type freely

**Question 2:** "What's the main tech stack?"
- Header: "Stack"
- Options:
  - "React/Next.js"
  - "Node.js/Express"
  - "Python/Django"
  - "Other (describe)"

---

## Step 10: Create CLAUDE.md

Read the template from `~/.claude/copilot/templates/CLAUDE.template.md` and create CLAUDE.md with:
- PROJECT_NAME = folder name
- PROJECT_DESCRIPTION = user's answer
- TECH_STACK = user's answer
- KNOWLEDGE_STATUS = detected status
- KNOWLEDGE_NAME = if available

---

## Step 11: Verify Setup

```bash
ls -la .mcp.json
ls -la CLAUDE.md
ls .claude/commands/
ls .claude/agents/ | head -5
```

All must exist.

---

## Step 12: Report Success

---

**Project Setup Complete!**

**Created:**
- `.mcp.json` - MCP server configuration
- `CLAUDE.md` - Project instructions
- `.claude/commands/` - Protocol commands (/protocol, /continue)
- `.claude/agents/` - 12 specialized agents
- `.claude/skills/` - For project-specific skills

**Configuration:**
- Memory workspace: `{{PROJECT_NAME}}`
- Skills: Local (.claude/skills)
{{IF KNOWLEDGE_EXISTS}}
- Knowledge: `{{KNOWLEDGE_NAME}}` (global)
{{ELSE}}
- Knowledge: Not configured
{{END IF}}

**Next steps:**

1. **Restart Claude Code** to load the MCP servers
2. Run `/mcp` to verify servers are connected:
   ```
   ● copilot-memory
   ● skills-copilot
   ```
3. Run `/protocol` to start working

{{IF NO_KNOWLEDGE}}
**Optional: Set up shared knowledge**

Create a knowledge repository for company/product information:
```
/knowledge-copilot
```
{{END IF}}

---

## Remember

- Be patient and encouraging
- Run commands yourself instead of asking user to copy/paste
- Use actual paths, never placeholders in final files
