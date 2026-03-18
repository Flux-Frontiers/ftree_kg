# Knowledge Copilot

Build a shared knowledge repository for your company or team. This knowledge becomes available across all your projects automatically.

## What This Does

Knowledge Copilot guides you through:
1. **Discovery** - Structured questions about your company, voice, products, and standards
2. **Documentation** - Creates organized markdown files as you answer
3. **Git Setup** - Initializes a repo you can push to GitHub
4. **Connection** - Links to `~/.claude/knowledge` for automatic access

## Why GitHub?

Your knowledge repository should be:
- **Version controlled** - Track changes over time
- **Shareable** - Team members can clone and contribute
- **Backed up** - Safe in the cloud
- **Collaborative** - PRs for knowledge updates

We'll help you set up a Git repo that can be pushed to GitHub (private repos are free).

---

## Detect Mode

First, check current state:

```bash
# Check for existing symlink
ls -la ~/.claude/knowledge 2>/dev/null

# Check for initiative in progress
```

Also call `initiative_get` to check for in-progress discovery.

**Based on results:**
- If symlink exists and points to valid repo → Offer to extend or verify
- If initiative exists for knowledge discovery → Resume
- Otherwise → Start fresh or link existing

---

## Mode Selection

Use AskUserQuestion:

**Question:** "What would you like to do?"
**Header:** "Mode"
**Options:**
1. **"Create new knowledge repository"** - Start fresh with guided discovery
2. **"Link existing repository"** - Connect to a repo you or your team already created
3. **"Check status"** - Verify your current knowledge setup
4. **"Continue discovery"** - Resume where you left off (if applicable)

---

## Mode: Create New Repository

### Step 1: Choose Location

Use AskUserQuestion:

**Question:** "Where should I create your knowledge repository?"
**Header:** "Location"
**Options:**
1. **"~/[company]-knowledge (Recommended)"** - Standard location, easy to find
2. **"Custom location"** - You specify the path

If custom, ask for the path.

**Also ask:**

**Question:** "What's your company or team name?"
**Header:** "Name"
**Options:** Let user type (will be used for folder name and manifest)

### Step 2: Create Structure

```bash
# Create directory (replace [company] with actual name, lowercase, hyphens)
mkdir -p ~/[company]-knowledge

cd ~/[company]-knowledge

# Create directory structure
mkdir -p 01-company
mkdir -p 02-voice
mkdir -p 03-products
mkdir -p 04-standards
mkdir -p .claude/extensions
```

### Step 3: Create Manifest

Create `knowledge-manifest.json`:

```json
{
  "version": "1.0",
  "name": "[company]",
  "description": "Knowledge repository for [Company Name]"
}
```

### Step 4: Create README

Create `README.md`:

```markdown
# [Company Name] Knowledge Repository

This repository contains shared knowledge for [Company Name], accessible across all projects via Claude Copilot.

## Structure

| Directory | Purpose |
|-----------|---------|
| `01-company/` | Company identity, values, mission |
| `02-voice/` | Communication style, terminology |
| `03-products/` | Product/service documentation |
| `04-standards/` | Development, design, operations standards |
| `.claude/extensions/` | Custom agent behaviors |

## Setup for Team Members

1. Clone this repo:
   ```bash
   git clone [repo-url] ~/[company]-knowledge
   ```

2. Create symlink:
   ```bash
   ln -sf ~/[company]-knowledge ~/.claude/knowledge
   ```

3. Verify:
   ```bash
   ls ~/.claude/knowledge/knowledge-manifest.json
   ```

## Usage

Once linked, use in any Claude Copilot project:
- `knowledge_search("company")` - Search company info
- `knowledge_search("voice")` - Search voice guidelines
- `knowledge_search("standards")` - Search standards

---

Built with [Claude Copilot](https://github.com/Everyone-Needs-A-Copilot/claude-copilot)
```

### Step 5: Create .gitignore

```
.DS_Store
*.swp
*.swo
*~
```

### Step 6: Initialize Git

```bash
cd ~/[company]-knowledge
git init
git add .
git commit -m "Initialize knowledge repository"
```

### Step 7: Create Symlink

```bash
# Remove existing symlink if present
rm -f ~/.claude/knowledge

# Create new symlink
ln -sf ~/[company]-knowledge ~/.claude/knowledge
```

**Verify:**
```bash
ls ~/.claude/knowledge/knowledge-manifest.json
```

### Step 8: Start Initiative

```
initiative_start({
  name: "[Company] Knowledge Discovery",
  goal: "Build comprehensive knowledge repository through guided discovery",
  status: "IN PROGRESS"
})
```

### Step 9: Begin Discovery

Now invoke the Knowledge Copilot agent behavior:

---

**Knowledge Repository Created!**

I've set up your knowledge repository at `~/[company]-knowledge` and linked it to `~/.claude/knowledge`.

**Ready for discovery.** I'll guide you through defining:
1. **Company Identity** - Who you are, values, mission
2. **Voice** - How you communicate
3. **Products/Services** - What you offer
4. **Standards** - How you work

We can do this in one session or across multiple. Each session, we'll save progress so you can resume anytime.

**Let's start with your company's foundation.**

Why does [Company] exist? What problem were you trying to solve when you started?

---

Continue with Phase 1 questions from the Knowledge Copilot agent profile.

---

## Mode: Link Existing Repository

### Step 1: Get Repository Location

Use AskUserQuestion:

**Question:** "Where is your knowledge repository?"
**Header:** "Source"
**Options:**
1. **"GitHub URL"** - Clone from GitHub
2. **"Local path"** - Already on this machine

### Step 2a: Clone from GitHub

If GitHub:

**Ask:** "What's the GitHub repository URL?"

```bash
# Clone the repo
git clone [url] ~/[company]-knowledge
```

### Step 2b: Use Local Path

If local:

**Ask:** "What's the full path to your knowledge repository?"

Verify it exists and has a manifest:
```bash
ls [path]/knowledge-manifest.json
```

### Step 3: Create Symlink

```bash
# Get company name from manifest
cat [path]/knowledge-manifest.json | grep '"name"'

# Remove existing symlink
rm -f ~/.claude/knowledge

# Create symlink
ln -sf [path] ~/.claude/knowledge
```

### Step 4: Verify

```bash
ls ~/.claude/knowledge/knowledge-manifest.json
```

### Step 5: Report Success

---

**Knowledge Repository Linked!**

Connected `~/.claude/knowledge` → `[path]`

This knowledge is now available in all your Claude Copilot projects.

**Test it:**
```
knowledge_search("company")
```

**To update knowledge:**
- Edit files in `[path]`
- Commit and push changes
- Team members: `git pull` to get updates

---

---

## Mode: Check Status

```bash
# Check symlink
ls -la ~/.claude/knowledge

# Check manifest
cat ~/.claude/knowledge/knowledge-manifest.json 2>/dev/null

# List directories
ls ~/.claude/knowledge/ 2>/dev/null

# Count files
find ~/.claude/knowledge -name "*.md" -type f 2>/dev/null | wc -l
```

Report:
- Whether knowledge is configured
- Repository name and location
- Number of knowledge files
- Directory structure

---

## Mode: Continue Discovery

1. Call `initiative_get` to load current state
2. Review what's been completed
3. Identify next phase
4. Resume questioning from Knowledge Copilot agent profile

---

## GitHub Setup Guide

When user is ready to push to GitHub:

### Step 1: Create GitHub Repository

---

**Let's push your knowledge to GitHub.**

1. Go to [github.com/new](https://github.com/new)
2. Name it: `[company]-knowledge`
3. Set to **Private** (recommended for company knowledge)
4. **Don't** initialize with README (we have content)
5. Click "Create repository"

What's your GitHub username or organization name?

---

### Step 2: Add Remote and Push

```bash
cd ~/[company]-knowledge
git remote add origin git@github.com:[username]/[company]-knowledge.git
git branch -M main
git push -u origin main
```

### Step 3: Confirm

---

**Your knowledge is now on GitHub!**

Repository: `github.com/[username]/[company]-knowledge`

**Team members can now:**
1. Clone: `git clone git@github.com:[username]/[company]-knowledge.git ~/[company]-knowledge`
2. Link: `ln -sf ~/[company]-knowledge ~/.claude/knowledge`
3. Or run `/knowledge-copilot` and choose "Link existing repository"

**To update:**
- Make changes locally
- `git add . && git commit -m "Update"`
- `git push`

---

---

## Tips

- One topic per session is fine - discovery takes time
- Your words become the documentation - speak naturally
- Generic answers get challenged - be specific
- Progress is saved - resume anytime with `/knowledge-copilot`
- Commit often - version control is your friend

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `/knowledge-copilot` | Start or continue knowledge discovery |
| `/knowledge-copilot link` | Link to existing repository |
| `/knowledge-copilot status` | Check current knowledge setup |
| `knowledge_search(query)` | Search your knowledge |
| `knowledge_get(path)` | Get specific knowledge file |
