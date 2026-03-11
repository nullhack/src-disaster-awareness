---
name: skill-generator
description: Complete guide for creating and managing OpenCode skills with templates, naming conventions, and best practices
compatibility: "1.0.0+"
metadata:
  category: development
  difficulty: intermediate
  type: skill-creation
---

# Skill Generator Skill

This skill provides comprehensive instructions for creating reusable OpenCode skills that encapsulate domain-specific knowledge, workflows, and instructions.

## When to Use This Skill

- Creating specialized instruction packages for agents
- Building domain-specific workflows (testing, documentation, API design, etc.)
- Packaging templates and best practices
- Creating organization-specific guidelines
- Building training materials for complex tasks

## What Are Skills?

**Skills** in OpenCode are:
- Reusable instruction blocks loaded on-demand
- Domain-specific knowledge packages
- Bundled templates and workflows
- Referenced in agent configurations or via `@skill` mentions
- Shareable across projects and agents

## Creating a Skill - Step by Step

### Step 1: Define Skill Purpose

Ask yourself:
- **What is this skill teaching?** (e.g., "how to write Python tests", "React patterns", "API security")
- **Who is the audience?** (junior devs, architects, DevOps engineers)
- **What problems does it solve?**
- **When should it be used?**

### Step 2: Create Skill Directory Structure

```bash
mkdir -p .opencode/skills/<skill-name>
touch .opencode/skills/<skill-name>/SKILL.md
```

Examples:
- `.opencode/skills/python-testing/SKILL.md`
- `.opencode/skills/react-patterns/SKILL.md`
- `.opencode/skills/security-audit/SKILL.md`

### Step 3: Create SKILL.md with Frontmatter

Every skill requires a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: my-skill-name
description: One-sentence description of what this skill covers
license: MIT
compatibility: "1.0.0+"
metadata:
  category: development
  difficulty: beginner
  author: Your Name
  tags:
    - testing
    - python
---

# Skill Title

Your skill content starts here...
```

### Step 4: Naming Rules

**Valid names:**
- Regex pattern: `^[a-z0-9]+(-[a-z0-9]+)*$`
- `python-testing` ✅
- `api-security` ✅
- `react-hooks-patterns` ✅

**Invalid names:**
- `Python-Testing` ❌ (uppercase)
- `python--testing` ❌ (consecutive hyphens)
- `_testing` ❌ (leading underscore)
- `testing-` ❌ (trailing hyphen)

**Directory name MUST match `name` field:**
```
.opencode/skills/python-testing/
                 └── matches "name: python-testing" in SKILL.md
```

### Step 5: Write Skill Content

Structure your skill markdown logically:

```markdown
# Main Skill Title

## Overview
- Brief description
- What it covers
- Who should use it

## Core Concepts
- Key ideas and definitions
- Terminology

## Step-by-Step Workflows
- Procedure 1
- Procedure 2
- Procedure 3

## Templates
- Code templates
- Configuration examples
- Document templates

## Best Practices
- Do's and don'ts
- Common pitfalls
- Pro tips

## Examples
- Real-world examples
- Before/after comparisons
- Case studies

## Troubleshooting
- Common issues
- Solutions
- When to ask for help

## Resources
- Links to documentation
- Related skills
- External references
```

### Step 6: Configure Skill Permissions (Optional)

In `opencode.json` or agent frontmatter, control who can access skills:

```json
{
  "skills": {
    "python-testing": "allow",
    "internal-*": "ask",
    "experimental-*": "deny"
  }
}
```

Permission options:
- `allow`: Load automatically
- `ask`: Ask user for permission
- `deny`: Completely hidden

### Step 7: Test Skill Loading

```bash
# In OpenCode CLI:
@skill python-testing

# Or via agent that has skill enabled
```

## Complete Skill Example

### File Structure
```
.opencode/skills/python-testing/
└── SKILL.md
```

### SKILL.md Content
```yaml
---
name: python-testing
description: Comprehensive guide to unit testing in Python using pytest
license: MIT
compatibility: "1.0.0+"
metadata:
  category: testing
  difficulty: beginner
  tags: [python, pytest, unit-testing]
---

# Python Testing with pytest

## Overview

This skill teaches how to write effective unit tests in Python using the pytest framework.

## Core Concepts

### Test Structure
- Arrange: Set up test data and state
- Act: Execute the code being tested
- Assert: Verify the results

### pytest Conventions
- Test files: `test_*.py` or `*_test.py`
- Test functions: `test_*`
- Test classes: `Test*`

## Step-by-Step: Writing Your First Test

### 1. Install pytest
```bash
pip install pytest
```

### 2. Create a test file
```bash
touch test_calculator.py
```

### 3. Write a simple test
```python
def test_add():
    # Arrange
    a, b = 5, 3
    
    # Act
    result = add(a, b)
    
    # Assert
    assert result == 8
```

### 4. Run tests
```bash
pytest test_calculator.py -v
```

## Best Practices

1. **One assertion per test**: Keep tests focused
2. **Descriptive names**: `test_add_positive_numbers` > `test_add`
3. **Test behavior, not implementation**: Focus on what, not how
4. **Avoid test interdependencies**: Each test should be independent
5. **Mock external dependencies**: Use `unittest.mock` for APIs, databases

## Common pytest Fixtures

```python
import pytest

@pytest.fixture
def sample_data():
    return {"name": "test", "value": 42}

def test_with_fixture(sample_data):
    assert sample_data["value"] == 42
```

## Troubleshooting

**Tests not discovered:**
- Check filenames match `test_*.py` pattern
- Ensure functions start with `test_`
- Run with `pytest --collect-only` to debug

**Import errors:**
- Add `__init__.py` to directories
- Run pytest from project root
```

## File Organization

**Project-level skills:**
```
your-project/
├── .opencode/
│   └── skills/
│       ├── python-testing/
│       │   └── SKILL.md
│       ├── api-design/
│       │   └── SKILL.md
│       └── security-audit/
│           └── SKILL.md
└── src/
```

**User-level skills (global):**
```
~/.config/opencode/skills/
├── my-python-patterns/
│   └── SKILL.md
└── team-practices/
    └── SKILL.md
```

## Best Practices for Skill Creation

1. **Be Specific**: Narrow focus = more useful skill
   - ✅ `python-async-patterns`
   - ❌ `python` (too broad)

2. **Make It Actionable**: Include workflows and examples
   - Include step-by-step procedures
   - Provide code templates
   - Show before/after

3. **Document Assumptions**: What prior knowledge is expected?
   - "Assumes familiarity with async/await"
   - "Requires Python 3.9+"

4. **Include Troubleshooting**: Common problems and solutions

5. **Link Related Skills**: "See also: python-testing, async-debugging"

6. **Version Compatibility**: Include `compatibility` field
   - `"1.0.0+"` (all versions)
   - `"2.1.0+"` (requires feature from v2.1)

7. **Organize with Headers**: Use markdown structure (H1, H2, H3)

8. **Add Metadata**: Use metadata section for categorization
   ```yaml
   metadata:
     category: development
     difficulty: intermediate
     author: Team Name
     tags: [testing, python, patterns]
     updated: 2024-01-15
   ```

## Common Skill Types

### 1. Technology Skills
- `python-testing`, `typescript-patterns`, `react-hooks`

### 2. Process Skills
- `code-review-checklist`, `pr-workflow`, `deployment-process`

### 3. Domain Skills
- `security-audit`, `performance-optimization`, `api-design`

### 4. Organization Skills
- `company-guidelines`, `team-standards`, `architecture-principles`

## Sharing Skills

**Within a project:**
- Commit to `.opencode/skills/` in git
- Team members get skills automatically

**Globally:**
- Save to `~/.config/opencode/skills/`
- Available across all projects

**Across teams:**
- Create organization repository
- Import via opencode.json configuration

## Troubleshooting

**Skill not loading:**
- Check frontmatter YAML is valid
- Verify name matches directory name
- Check file is `SKILL.md` (case-sensitive)

**Permission denied:**
- Check `opencode.json` skill permissions
- Request access from admin

**Outdated skill:**
- Update `SKILL.md` content directly
- Increment `compatibility` version if breaking changes

## Advanced: Creating Skill Collections

Group related skills:

```
.opencode/skills/
├── python-testing/
├── python-async/
├── python-security/
└── README.md (documents all python-* skills)
```

Agents can load multiple skills:
```yaml
# In agent config
I have access to these skills:
@skill python-testing
@skill python-async
@skill python-security
```
