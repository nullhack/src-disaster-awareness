---
name: agent-generator
description: Comprehensive guide for creating OpenCode agents and subagents with step-by-step instructions and best practices
compatibility: "1.0.0+"
metadata:
  category: development
  difficulty: intermediate
  type: agent-creation
---

# Agent Generator Skill

This skill provides detailed instructions and workflows for creating new OpenCode agents and subagents tailored to specific use cases.

## When to Use This Skill

- Creating a new subagent for specialized tasks
- Defining agent capabilities and constraints
- Setting up role-specific agents (code-reviewer, documenter, tester, etc.)
- Configuring agent permissions and tool access

## What Are Agents?

**Agents** in OpenCode are autonomous assistants with:
- Specific capabilities (enabled/disabled tools)
- Specialized system prompts and instructions
- Custom models or temperature settings
- Permission controls for sensitive operations
- Stepping limits to prevent infinite loops

## Creating an Agent - Step by Step

### Step 1: Determine Agent Purpose and Scope

Before creating, define:
- **What is the agent's primary responsibility?** (e.g., "review code for security issues")
- **What tools does it need?** (write, edit, bash, webfetch, etc.)
- **What tools should it NOT have?** (e.g., no bash for read-only agents)
- **What's the agent's expertise level?** (junior, mid, expert)
- **Temperature setting**: 0.1 (focused), 0.3-0.5 (balanced), 0.7+ (creative)

### Step 2: Create Agent Using Interactive CLI

```bash
opencode agent create
```

This will prompt you for:
1. Agent name (lowercase, hyphens ok: `code-reviewer`, `test-writer`)
2. Description (brief, ~50 chars)
3. Tool selection (check yes/no for each tool)
4. Mode selection (primary/subagent)

### Step 3: Create Agent Using Markdown File

Create `.opencode/agents/<agent-name>.md`:

```yaml
---
description: Clear one-sentence description of agent purpose
mode: subagent  # 'primary', 'subagent', or 'all'
model: anthropic/claude-haiku-4-5  # optional: override default model
temperature: 0.3  # 0.0-1.0: 0.1=focused, 0.7=creative
tools:
  write: true
  edit: true
  bash: true
  webfetch: true
  read: true
  glob: true
  grep: true
  task: true
permission:
  edit: allow    # allow/ask/deny
  bash: ask      # require user confirmation
  webfetch: ask  # require user confirmation
steps: 15  # max iterations before responding
hidden: false  # hide from @ autocomplete
---

# System Prompt

You are a specialized code reviewer focused on security and performance.

Your responsibilities:
- Review code for security vulnerabilities
- Identify performance bottlenecks
- Suggest improvements using best practices
- Provide constructive feedback

## How to Operate

1. Always ask clarifying questions about the code's context
2. Use concrete examples when suggesting improvements
3. Prioritize security over optimization
4. Reference OWASP guidelines when relevant
5. Never modify code without explicit permission

## Tools You Can Use

- **read**: Review code files
- **grep**: Search for patterns
- **bash**: Run tests and linters
- **webfetch**: Look up security advisories
- **edit**: Make suggested changes (with permission)

## When to Stop

- After thorough review
- When user confirms understanding
- On second request for same code
```

### Step 4: Configuration Options Explained

**mode:**
- `primary`: Main agent available in interface (Build, Plan)
- `subagent`: Invoked via `@agent-name` or Task tool
- `all`: Works in both contexts

**tools:**
Enable/disable specific tools. Common tools:
- `read`, `write`, `edit`, `bash`, `glob`, `grep`
- `webfetch`, `task`, `distill`, `prune`
- `skill`: Load specialized skill instructions

**permission:**
Controls sensitive operations:
- `allow`: Can use tool without asking
- `ask`: Ask user for permission each time
- `deny`: Cannot use tool

**temperature:**
- `0.0`: Deterministic, focused
- `0.1-0.3`: Best for code generation and analysis
- `0.5`: Balanced creativity and focus
- `0.7-1.0`: Creative, exploratory

**steps:**
Maximum agentic iterations (default: 10). Higher = longer conversations before final response.

### Step 5: Test the Agent

Use `@` mention in conversation:
```
@code-reviewer Review this function for security issues
```

Or via Task tool:
```
Task(description="Code review", prompt="Review app/auth.py for vulnerabilities", subagent_type="code-reviewer")
```

## Best Practices

1. **Be Specific with Purpose**: Narrow focus = better results
2. **Restrict Dangerous Tools**: Limit bash/edit for untrusted use cases
3. **Set Appropriate Temperature**: 0.1-0.3 for technical tasks
4. **Clear Instructions**: Write unambiguous system prompts
5. **Test Thoroughly**: Try various inputs before deploying
6. **Document Constraints**: Explain what agent CAN'T do
7. **Use Descriptive Names**: `python-tester` is better than `tester`

## Common Agent Patterns

### Code Reviewer Agent
```yaml
tools:
  bash: true
  read: true
  grep: true
  webfetch: true
permission:
  bash: ask
temperature: 0.2
```

### Documentation Generator
```yaml
tools:
  read: true
  write: true
  bash: true
permission:
  write: allow
temperature: 0.5
```

### Test Writer Agent
```yaml
tools:
  read: true
  write: true
  bash: true
  edit: true
permission:
  bash: allow
  edit: allow
temperature: 0.3
```

### Research Agent
```yaml
tools:
  webfetch: true
  read: true
  grep: true
permission:
  webfetch: allow
temperature: 0.6
```

## Troubleshooting

**Agent not responding:**
- Check if tools are enabled (`tools: true`)
- Verify agent file is in correct directory
- Restart OpenCode CLI

**Agent keeps asking questions:**
- Lower `steps` value or be more specific in prompts
- Increase `temperature` for exploratory tasks

**Permission denied errors:**
- Check `permission` settings match intended access
- Update agent config with correct permissions

## File Structure

```
.opencode/
├── agents/
│   ├── code-reviewer.md
│   ├── doc-generator.md
│   └── test-writer.md
└── opencode.json (optional, for global config)
```

Or globally:
```
~/.config/opencode/agents/
├── code-reviewer.md
└── test-writer.md
```
