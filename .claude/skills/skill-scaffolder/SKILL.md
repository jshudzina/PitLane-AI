---
name: skill-scaffolder
description: Create new skills following pitlane-agent conventions. Use when adding new functionality that requires skill scaffolding, script generation, or test creation.
allowed-tools: Write, Read, Bash(mkdir:*), Glob
---

# Skill Scaffolder

This skill provides comprehensive instructions and templates for creating new skills in the pitlane-agent project. Use this skill when you need to scaffold new capabilities, add scripts, or set up test infrastructure.

## When to Use This Skill

Use this skill when:
- **Adding new functionality**: Creating a new skill to handle specific user requests
- **Building script-backed features**: Need a click-based Python script with the skill
- **Setting up tests**: Creating test infrastructure for new scripts
- **Creating skill hierarchies**: Building parent skills with multiple related subskills

## Naming Conventions

### Skills
- **Directory name**: `kebab-case` (e.g., `skill-scaffolder`, `f1-analyst`)
- **YAML name field**: Must match directory name exactly
- **Markdown title**: Title Case (e.g., "Skill Scaffolder", "F1 Data Analyst")

### Scripts
- **File name**: `snake_case.py` (e.g., `event_schedule.py`, `lap_times.py`)
- **Business logic functions**: `snake_case` (e.g., `get_event_schedule`, `generate_chart`)
- **CLI function**: Always named `cli`
- **Invocation**: `python -m pitlane_agent.scripts.script_name`

### Tests
- **File name**: `test_<script_name>.py` (e.g., `test_event_schedule.py`)
- **Test classes**: `Test<ClassName>` (e.g., `TestBusinessLogic`, `TestCLI`)
- **Test methods**: `test_<what_it_tests>` (e.g., `test_cli_success`, `test_validation_error`)

## Directory Structure

```
PitLane-AI/
├── packages/
│   └── pitlane-agent/
│       ├── src/
│       │   └── pitlane_agent/
│       │       ├── .claude/
│       │       │   └── skills/
│       │       │       ├── skill-name/           # Flat skill
│       │       │       │   └── SKILL.md
│       │       │       └── parent-skill/         # Hierarchical skill
│       │       │           ├── SKILL.md          # Parent with table
│       │       │           ├── subskill-1.md     # Subskill 1
│       │       │           └── subskill-2.md     # Subskill 2
│       │       └── scripts/
│       │           └── script_name.py
│       └── tests/
│           └── scripts/
│               └── test_script_name.py
```

## Step 1: Create a Flat Skill

A flat skill is a standalone skill contained in a single SKILL.md file.

### Instructions

1. Create the skill directory:
   ```bash
   mkdir -p packages/pitlane-agent/src/pitlane_agent/.claude/skills/your-skill-name
   ```

2. Create SKILL.md using the template below
3. Customize the template:
   - Replace `skill-name` with your kebab-case skill name
   - Update `description` to explain when to use the skill
   - Set appropriate `allowed-tools` (common: `Bash(python:*)`, `Read`, `Write`, `Skill`)
   - Fill in the skill content with instructions for Claude

### Flat Skill Template (SKILL.md)

```markdown
---
name: skill-name
description: Brief description of when to use this skill. Should explain the trigger conditions.
allowed-tools: Bash(python:*), Read, Write
---

# Skill Title

Introduction paragraph explaining what this skill does and its purpose.

## When to Use This Skill

Use this skill when users ask about:
- **Use case 1**: Describe when this applies (e.g., "Race calendars and event dates")
- **Use case 2**: Another trigger scenario
- **Use case 3**: Additional context

## Step 1: Understand the Request

Provide guidance on how to parse and understand the user's request. Include:
- What parameters to extract
- Default values to use
- How to handle ambiguous requests

## Step 2: Execute the Main Task

Instructions for performing the core functionality. This might include:
- Running a script with bash
- Reading/analyzing files
- Using other tools

### Example Commands

If this skill uses scripts, provide examples:

```bash
python -m pitlane_agent.scripts.script_name --param1 value --param2 value
```

## Step 3: Format the Response

Guidance on how Claude should structure the response to the user:
- What format to use (table, list, prose)
- What information to highlight
- How to handle edge cases

## Data Reference (Optional)

If applicable, include reference data like:
- Field descriptions
- Valid values
- Lookup tables
- Common abbreviations

## Example Questions and Approaches

Provide 3-5 realistic example questions with suggested approaches:

**"Example question 1?"**
1. Step to handle it
2. What to do next
3. How to respond

**"Example question 2?"**
1. Different approach for this scenario
2. Handling variations
3. Response format

## Notes

Any important caveats, limitations, or additional context.
```

## Step 2: Create a Hierarchical Skill

Hierarchical skills have a parent SKILL.md that references multiple subskill markdown files.

### Instructions

1. Create the parent skill directory:
   ```bash
   mkdir -p packages/pitlane-agent/src/pitlane_agent/.claude/skills/parent-skill-name
   ```

2. Create the parent SKILL.md with a table of subskills
3. Create separate markdown files for each subskill (e.g., `subskill-1.md`)
4. Keep hierarchy to 1 level (parent → subskills only)

### Hierarchical Parent Template (SKILL.md)

```markdown
---
name: parent-skill
description: Parent skill managing multiple related subskills. Briefly explain the domain.
allowed-tools: Skill
---

# Parent Skill Title

This skill provides access to multiple related subskills for [domain/topic area].

## Available Subskills

| Subskill | Description | Documentation |
|----------|-------------|---------------|
| subskill-1 | Brief description of what it does | [subskill-1.md](./subskill-1.md) |
| subskill-2 | Brief description of what it does | [subskill-2.md](./subskill-2.md) |
| subskill-3 | Brief description of what it does | [subskill-3.md](./subskill-3.md) |

## How to Use

When a user asks about [topic], determine which subskill is most appropriate based on:
- **Criteria 1**: Use subskill-1
- **Criteria 2**: Use subskill-2
- **Criteria 3**: Use subskill-3

Invoke the appropriate subskill using the Skill tool.

## Example Questions

Map common user questions to the right subskill:

- "Question pattern 1" → Use subskill-1
- "Question pattern 2" → Use subskill-2
- "Question pattern 3" → Use subskill-3

## Notes

Any cross-cutting concerns or general guidance for using these subskills together.
```

### Subskill File Template (subskill-1.md)

```markdown
# Subskill Title

Detailed instructions for this specific subskill. This file has the same structure as a flat SKILL.md but without the YAML front matter (that's only in the parent).

## When to Use

Specific trigger conditions for this subskill.

## Step 1: [First Step]

Detailed instructions...

## Step 2: [Second Step]

More instructions...

## Example Usage

Examples specific to this subskill...
```

## Step 3: Create a Click-Based Script (Optional)

If your skill needs a Python script to perform actions, create it using click.

### Instructions

1. Create the script file:
   ```bash
   touch packages/pitlane-agent/src/pitlane_agent/scripts/your_script_name.py
   ```

2. Use the template below as a starting point
3. Customize:
   - Replace `script_name` and `main_function` with your names
   - Add appropriate click options
   - Implement business logic in the main function
   - Ensure JSON output to stdout
   - Handle errors with JSON to stderr and sys.exit(1)

### Click Script Template

```python
"""
Brief description of what this script does.

Usage:
    python -m pitlane_agent.scripts.script_name [OPTIONS]
"""

import json
import sys
from pathlib import Path

import click


def main_function(
    param1: str,
    param2: int,
) -> dict:
    """Business logic function.

    Separate the business logic from CLI handling to make it easier to test.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter

    Returns:
        Dictionary with results in a structured format

    Raises:
        ValueError: If validation fails
        RuntimeError: If operation fails
    """
    # Input validation
    if not param1:
        raise ValueError("param1 cannot be empty")

    if param2 < 0:
        raise ValueError("param2 must be non-negative")

    # Business logic implementation
    # ... your code here ...

    # Return structured result
    result = {
        "param1": param1,
        "param2": param2,
        "status": "success",
        "data": {
            # Your actual results
        }
    }

    return result


@click.command()
@click.option(
    "--param1",
    required=True,
    help="Description of param1"
)
@click.option(
    "--param2",
    type=int,
    default=100,
    help="Description of param2 (default: 100)"
)
@click.option(
    "--output",
    type=click.Path(),
    help="Optional output file path"
)
def cli(param1: str, param2: int, output: str | None):
    """Command description that appears in --help."""
    try:
        result = main_function(param1=param1, param2=param2)

        # Pretty-print JSON output
        output_json = json.dumps(result, indent=2)

        if output:
            # Write to file if specified
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(output_json)
            click.echo(json.dumps({"status": "written", "path": output}))
        else:
            # Print to stdout
            click.echo(output_json)

    except Exception as e:
        # Error output to stderr with exit code 1
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
```

### Common Click Patterns

**Multiple values for an option:**
```python
@click.option(
    "--driver",
    multiple=True,
    help="Driver abbreviation (can specify multiple)"
)
def cli(driver: tuple[str, ...]):
    drivers = list(driver)  # Convert tuple to list
```

**Boolean flags:**
```python
@click.option(
    "--include-testing/--no-testing",
    default=True,
    help="Include testing sessions"
)
def cli(include_testing: bool):
    pass
```

**Choice from list:**
```python
@click.option(
    "--session",
    type=click.Choice(['FP1', 'FP2', 'FP3', 'Q', 'S', 'R']),
    required=True,
    help="Session type"
)
def cli(session: str):
    pass
```

**File path:**
```python
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to config file"
)
def cli(config: str):
    pass
```

## Step 4: Create Tests (Optional)

If you created a script, create comprehensive tests using pytest and click.testing.CliRunner.

### Instructions

1. Create the test file:
   ```bash
   mkdir -p packages/pitlane-agent/tests/scripts
   touch packages/pitlane-agent/tests/scripts/test_your_script_name.py
   ```

2. Use the template below
3. Create two test classes:
   - `TestBusinessLogic`: Unit tests for business functions
   - `TestCLI`: Integration tests for CLI interface

### Test Template

```python
"""Tests for script_name script."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from pitlane_agent.scripts.script_name import cli, main_function


class TestMainFunctionBusinessLogic:
    """Unit tests for business logic functions.

    These tests directly call business functions without going through the CLI.
    Mock any external dependencies (APIs, file I/O, etc.).
    """

    def test_main_function_success(self):
        """Test successful execution with valid inputs."""
        result = main_function(param1="test", param2=100)

        assert result["param1"] == "test"
        assert result["param2"] == 100
        assert result["status"] == "success"
        assert "data" in result

    def test_main_function_validation_error_empty_param1(self):
        """Test that empty param1 raises ValueError."""
        with pytest.raises(ValueError, match="param1 cannot be empty"):
            main_function(param1="", param2=100)

    def test_main_function_validation_error_negative_param2(self):
        """Test that negative param2 raises ValueError."""
        with pytest.raises(ValueError, match="param2 must be non-negative"):
            main_function(param1="test", param2=-1)

    @patch("pitlane_agent.scripts.script_name.some_external_dependency")
    def test_main_function_with_mocked_dependency(self, mock_dependency):
        """Test with mocked external dependencies."""
        # Setup mock
        mock_dependency.return_value = {"data": "mocked"}

        result = main_function(param1="test", param2=100)

        # Verify mock was called correctly
        mock_dependency.assert_called_once()
        assert result["status"] == "success"


class TestCLI:
    """Integration tests for CLI interface using CliRunner.

    These tests invoke the CLI as a user would and verify the output.
    """

    def test_cli_help(self):
        """Test that --help displays usage information."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "--param1" in result.output
        assert "--param2" in result.output
        assert "Command description" in result.output

    def test_cli_success(self):
        """Test successful CLI execution."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--param1", "test",
            "--param2", "200"
        ])

        assert result.exit_code == 0

        # Parse JSON output
        output = json.loads(result.output)
        assert output["param1"] == "test"
        assert output["param2"] == 200
        assert output["status"] == "success"

    def test_cli_with_defaults(self):
        """Test CLI with default values for optional params."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--param1", "test"
            # param2 should use default value of 100
        ])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["param2"] == 100

    def test_cli_missing_required(self):
        """Test that missing required option shows error."""
        runner = CliRunner()
        result = runner.invoke(cli, [])

        assert result.exit_code != 0
        assert "param1" in result.output or "required" in result.output.lower()

    def test_cli_error_handling(self):
        """Test that errors are properly formatted as JSON to stderr."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--param1", "",  # This should trigger validation error
            "--param2", "100"
        ])

        assert result.exit_code == 1

        # Error should be JSON formatted
        error_output = json.loads(result.output)
        assert "error" in error_output
        assert "cannot be empty" in error_output["error"]

    def test_cli_with_output_file(self, tmp_path):
        """Test writing output to a file."""
        runner = CliRunner()
        output_file = tmp_path / "output.json"

        result = runner.invoke(cli, [
            "--param1", "test",
            "--param2", "100",
            "--output", str(output_file)
        ])

        assert result.exit_code == 0
        assert output_file.exists()

        # Verify file contents
        saved_data = json.loads(output_file.read_text())
        assert saved_data["param1"] == "test"

    @patch("pitlane_agent.scripts.script_name.main_function")
    def test_cli_calls_business_logic(self, mock_main_function):
        """Test that CLI correctly calls business logic function."""
        mock_main_function.return_value = {"status": "mocked"}

        runner = CliRunner()
        result = runner.invoke(cli, [
            "--param1", "test",
            "--param2", "100"
        ])

        # Verify business function was called with correct args
        mock_main_function.assert_called_once_with(
            param1="test",
            param2=100
        )
```

### Running Tests

```bash
# Run all tests for a script
pytest packages/pitlane-agent/tests/scripts/test_script_name.py -v

# Run specific test class
pytest packages/pitlane-agent/tests/scripts/test_script_name.py::TestCLI -v

# Run specific test method
pytest packages/pitlane-agent/tests/scripts/test_script_name.py::TestCLI::test_cli_success -v

# Run with coverage
pytest packages/pitlane-agent/tests/scripts/test_script_name.py --cov=pitlane_agent.scripts.script_name
```

## Step 5: Verify Setup

After creating your skill, script, and tests, verify everything works:

### 1. Verify Skill Structure
- [ ] SKILL.md exists in correct location
- [ ] YAML front matter is valid (name, description, allowed-tools)
- [ ] Instructions are clear and actionable
- [ ] Templates are properly formatted
- [ ] For hierarchical skills: parent links to subskills correctly

### 2. Test Script Execution
```bash
# Test help output
python -m pitlane_agent.scripts.your_script_name --help

# Test with sample inputs
python -m pitlane_agent.scripts.your_script_name --param1 test --param2 100

# Verify JSON output format
python -m pitlane_agent.scripts.your_script_name --param1 test | jq .
```

### 3. Run Tests
```bash
# Run all tests
pytest packages/pitlane-agent/tests/scripts/test_your_script_name.py -v

# Check coverage
pytest packages/pitlane-agent/tests/scripts/test_your_script_name.py \
  --cov=pitlane_agent.scripts.your_script_name \
  --cov-report=term-missing
```

### 4. Test Skill Usage
Try using the skill in a Claude conversation to ensure it works as expected.

## Examples

### Example 1: Simple Flat Skill (No Script)

A skill that provides guidance without needing a script:

```markdown
---
name: code-review-helper
description: Assist with code review tasks. Use when user asks for code reviews, style checks, or best practices.
allowed-tools: Read, Glob, Grep
---

# Code Review Helper

This skill helps perform thorough code reviews following best practices.

## When to Use This Skill

Use when users ask to:
- Review code changes
- Check coding standards
- Suggest improvements
- Identify bugs or issues

## Step 1: Understand Scope

Determine what needs to be reviewed:
- Specific files: Use Read tool
- Pattern-based: Use Glob to find files
- Search for patterns: Use Grep

## Step 2: Analyze Code

Review for:
- Code style and formatting
- Potential bugs
- Performance issues
- Security vulnerabilities
- Best practices

## Step 3: Provide Feedback

Structure feedback as:
1. Summary of findings
2. Critical issues (must fix)
3. Suggestions (should consider)
4. Positive observations
```

### Example 2: Script-Backed Flat Skill

The f1-schedule skill is a good example:
- SKILL.md provides instructions
- References `event_schedule.py` script
- Explains how to use script with different parameters
- Shows how to format responses

### Example 3: Hierarchical Skill

A data analysis skill with subskills:

**SKILL.md (Parent)**:
```markdown
---
name: data-analysis
description: Comprehensive data analysis tools. Use when user needs data processing, visualization, or statistical analysis.
allowed-tools: Skill
---

# Data Analysis

This skill provides access to specialized data analysis subskills.

## Available Subskills

| Subskill | Description | Documentation |
|----------|-------------|---------------|
| data-cleaning | Clean and prepare datasets | [data-cleaning.md](./data-cleaning.md) |
| data-viz | Create visualizations | [data-viz.md](./data-viz.md) |
| statistics | Statistical analysis | [statistics.md](./statistics.md) |

## How to Use

- Data preparation tasks → data-cleaning
- Chart/graph requests → data-viz
- Statistical questions → statistics
```

**data-cleaning.md (Subskill)**:
```markdown
# Data Cleaning

Instructions for cleaning and preparing datasets.

## When to Use

Use when data needs:
- Missing value handling
- Outlier detection
- Format standardization
- Deduplication

## Steps...
```

## Common Patterns

### Allowed Tools

Choose tools based on what the skill needs to do:

- **Read-only analysis**: `Read, Glob, Grep`
- **Script execution**: `Bash(python:*), Read, Write`
- **File creation**: `Write, Read, Bash(mkdir:*)`
- **Hierarchical skills**: `Skill` (to invoke subskills)
- **Web access**: `WebFetch, WebSearch` (if needed)

### Restrictions

You can restrict Bash usage:
- `Bash(python:*)` - Only Python commands
- `Bash(git:*)` - Only Git commands
- `Bash(npm:*)` - Only npm commands

### Error Handling in Scripts

Always handle errors gracefully:

```python
try:
    result = main_function(...)
    click.echo(json.dumps(result, indent=2))
except ValueError as e:
    click.echo(json.dumps({"error": f"Validation error: {str(e)}"}), err=True)
    sys.exit(1)
except Exception as e:
    click.echo(json.dumps({"error": f"Unexpected error: {str(e)}"}), err=True)
    sys.exit(1)
```

## Best Practices

1. **Keep skills focused**: One skill should do one thing well
2. **Provide examples**: Include 3-5 realistic example questions
3. **Document edge cases**: Note limitations and special cases
4. **Use consistent formatting**: Follow the templates provided
5. **Test thoroughly**: Ensure scripts work before creating the skill
6. **Write clear instructions**: Claude should be able to follow without guessing
7. **Separate concerns**: Business logic separate from CLI handling
8. **Type hints**: Use Python type hints in all functions
9. **JSON output**: Always output structured JSON from scripts
10. **Test coverage**: Aim for >90% coverage with meaningful tests

## Troubleshooting

### Issue: YAML parsing error
**Solution**: Ensure YAML front matter has exactly 3 dashes before and after, no extra whitespace

### Issue: Script not found
**Solution**: Verify script is in `packages/pitlane-agent/src/pitlane_agent/scripts/` and has `.py` extension

### Issue: Tests failing
**Solution**: Check imports match the actual module structure, ensure mocks are properly configured

### Issue: Click options not working
**Solution**: Verify option names match function parameters, check types and defaults

### Issue: Hierarchical skill table not rendering
**Solution**: Ensure table has proper markdown format with pipes and dashes, check file paths are relative

## Notes

- **No automation script**: This skill provides instructions only. You'll create files using Write tool.
- **Convention adherence**: Following conventions ensures consistency across the codebase.
- **Test-first approach**: Consider writing tests before implementing complex business logic.
- **Click is required**: All new scripts must use click, not argparse.
- **Flat is preferred**: Only create hierarchical skills when you have 3+ related subskills.
