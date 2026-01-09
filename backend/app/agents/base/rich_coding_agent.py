"""
Rich Coding Agent

A CodingAgent subclass that provides beautiful terminal output using the rich library.
Displays thoughts, code input, and execution output in a visually appealing manner.
"""

from typing import Any, AsyncGenerator

import structlog
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from app.agents.base.base_agent import CodingAgent
from app.core.memory import SessionMemory
from app.shared.llm import LLMService
from app.shared.models import AgentStatus, AgentStatusType

logger = structlog.get_logger(__name__)

# Custom theme for the agent output
AGENT_THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "thinking": "bold magenta",
        "code": "green",
        "output": "white",
        "iteration": "bold blue",
    }
)


class RichCodingAgent(CodingAgent):
    """
    Coding agent with beautiful terminal output using rich.

    Extends CodingAgent to provide visually appealing console output
    for thoughts, code, and execution results during the ReAct loop.

    Features:
    - Colorful status indicators
    - Syntax-highlighted code blocks
    - Formatted output panels
    - Progress spinners for async operations
    - Structured iteration tracking

    Usage:
        class MyRichAnalyst(RichCodingAgent):
            @property
            def system_prompt(self) -> str:
                return '''You are an analyst agent...'''

        agent = MyRichAnalyst()

        # Stream execution with pretty console output
        async for status in agent.execute_stream(user_prompt="Analyze data", context={"df": df}):
            # Status updates are automatically printed to console
            if status.status_type == AgentStatusType.COMPLETED:
                result = status.data
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        memory_service: SessionMemory | None = None,
        executor_type: str | None = None,
        authorized_imports: list[str] | None = None,
        console: Console | None = None,
        show_output: bool = True,
    ):
        """
        Initialize rich coding agent.

        Args:
            llm_service: LLM service instance
            memory_service: Memory service instance
            executor_type: Code executor type ('smolagents' or 'daytona')
            authorized_imports: List of allowed imports for smolagents executor
            console: Custom rich Console instance
            show_output: Whether to display output to console (default: True)
        """
        super().__init__(llm_service, memory_service, executor_type, authorized_imports)

        self.console = console or Console(theme=AGENT_THEME)
        self.show_output = show_output

    def _print_header(self, title: str, subtitle: str | None = None) -> None:
        """Print a styled header."""
        if not self.show_output:
            return

        header_text = Text()
        header_text.append("🤖 ", style="bold")
        header_text.append(title, style="bold cyan")
        if subtitle:
            header_text.append(f"\n   {subtitle}", style="dim")

        self.console.print(Panel(header_text, border_style="cyan", expand=False))

    def _print_iteration_header(self, iteration: int, total: int, status: str) -> None:
        """Print iteration header with progress indicator."""
        if not self.show_output:
            return

        progress_bar = "●" * iteration + "○" * (total - iteration)
        header = Text()
        header.append(f"\n┌─ Iteration {iteration}/{total} ", style="iteration")
        header.append(f"[{progress_bar}] ", style="dim")
        header.append(status, style="info")
        header.append(" ─" * 20, style="dim")

        self.console.print(header)

    def _print_thoughts(self, thoughts: str) -> None:
        """Print agent's thoughts in a styled panel."""
        if not self.show_output or not thoughts:
            return

        thought_panel = Panel(
            Markdown(thoughts),
            title="💭 Thoughts",
            title_align="left",
            border_style="magenta",
            padding=(1, 2),
        )
        self.console.print(thought_panel)

    def _print_code(self, code: str) -> None:
        """Print generated code with syntax highlighting."""
        if not self.show_output or not code:
            return

        syntax = Syntax(
            code,
            "python",
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )
        code_panel = Panel(
            syntax,
            title="📝 Generated Code",
            title_align="left",
            border_style="green",
        )
        self.console.print(code_panel)

    def _print_output(
        self,
        output: Any,
        logs: str | None = None,
        success: bool = True,
    ) -> None:
        """Print execution output with appropriate styling."""
        if not self.show_output:
            return

        # Create output content
        content = []

        if logs:
            content.append(Text("📋 Stdout:", style="bold"))
            content.append(Text(logs, style="dim"))
            content.append(Text())

        if output is not None:
            content.append(Text("📤 Return Value:", style="bold"))

            # Handle DataFrame-like objects
            if hasattr(output, "to_string"):
                try:
                    # For pandas DataFrames, create a rich table
                    output_table = self._dataframe_to_table(output)
                    if output_table:
                        content.append(output_table)
                    else:
                        content.append(Text(str(output)[:2000], style="output"))
                except Exception:
                    content.append(Text(str(output)[:2000], style="output"))
            else:
                content.append(Text(str(output)[:2000], style="output"))

        if not content:
            content.append(Text("No output or return value", style="dim"))

        # Determine panel style based on success
        title = "✅ Execution Successful" if success else "❌ Execution Failed"
        border_style = "success" if success else "error"

        # Build the panel content
        from rich.console import Group

        output_panel = Panel(
            Group(*content),
            title=title,
            title_align="left",
            border_style=border_style,
            padding=(1, 2),
        )
        self.console.print(output_panel)

    def _print_error(self, error: str) -> None:
        """Print error message in a styled panel."""
        if not self.show_output:
            return

        error_panel = Panel(
            Text(error, style="error"),
            title="❌ Error",
            title_align="left",
            border_style="red",
            padding=(1, 2),
        )
        self.console.print(error_panel)

    def _print_completion(
        self,
        success: bool,
        iterations: int,
        is_complete: bool,
    ) -> None:
        """Print completion summary."""
        if not self.show_output:
            return

        status_emoji = "✅" if success else "❌"
        status_text = "Completed Successfully" if success else "Failed"
        complete_text = "Task complete" if is_complete else "Max iterations reached"

        summary = Table.grid(padding=1)
        summary.add_column(justify="right", style="bold")
        summary.add_column()

        summary.add_row("Status:", f"{status_emoji} {status_text}")
        summary.add_row("Iterations:", str(iterations))
        summary.add_row("Result:", complete_text)

        completion_panel = Panel(
            summary,
            title=f"🏁 {self.agent_name} Finished",
            title_align="left",
            border_style="cyan" if success else "red",
        )
        self.console.print(completion_panel)
        self.console.print()

    def _dataframe_to_table(self, df: Any) -> Table | None:
        """Convert a pandas DataFrame to a rich Table."""
        try:
            # Limit rows for display
            display_df = df.head(10) if hasattr(df, "head") else df

            table = Table(
                show_header=True,
                header_style="bold cyan",
                border_style="dim",
                row_styles=["", "dim"],
            )

            # Add columns
            if hasattr(display_df, "columns"):
                for col in display_df.columns:
                    table.add_column(str(col))

                # Add rows
                for _, row in display_df.iterrows():
                    table.add_row(*[str(v)[:50] for v in row.values])

                # Add footer if truncated
                if hasattr(df, "__len__") and len(df) > 10:
                    table.add_row(*["..." for _ in display_df.columns], style="dim")

                return table
            return None
        except Exception:
            return None

    async def execute_stream(
        self,
        user_prompt: str,
        context: dict[str, Any] | None = None,
        max_iterations: int = 5,
        session_id: str | None = None,
        include_context: bool = False,
    ) -> AsyncGenerator[AgentStatus, None]:
        """
        Execute the coding agent with ReAct loop, yielding status updates
        and printing beautiful output to the console.

        This extends the parent execute_stream to add rich console output
        while maintaining full compatibility with the streaming interface.

        Args:
            user_prompt: User's request/question
            context: Additional context (file IDs, data, etc.)
            max_iterations: Maximum ReAct iterations
            session_id: Optional session ID for memory

        Yields:
            AgentStatus updates during execution
        """
        # Print execution header
        self._print_header(
            f"Starting {self.agent_name}",
            f"Max iterations: {max_iterations}",
        )

        # Track state for rich output
        current_iteration = 0
        final_success = False
        final_iterations = 0
        final_is_complete = False

        # Execute parent stream and intercept for rich output
        async for status in super().execute_stream(
            user_prompt=user_prompt,
            context=context,
            max_iterations=max_iterations,
            session_id=session_id,
            include_context=include_context,
        ):
            # Handle different status types with rich output
            match status.status_type:
                case AgentStatusType.STARTED:
                    pass  # Header already printed

                case AgentStatusType.THINKING:
                    current_iteration = status.iteration or 0
                    self._print_iteration_header(
                        current_iteration,
                        max_iterations,
                        "Thinking...",
                    )

                case AgentStatusType.GENERATING_CODE:
                    if self.show_output:
                        with self.console.status(
                            "[bold cyan]Generating code...[/]",
                            spinner="dots",
                        ):
                            pass  # Status will be brief

                case AgentStatusType.EXECUTING:
                    # Print thoughts and code from the data
                    if status.data:
                        thoughts = status.data.get("thoughts", "")
                        code = status.data.get("code", "")
                        self._print_thoughts(thoughts)
                        self._print_code(code)

                        if self.show_output:
                            self.console.print("[bold yellow]⏳ Executing code...[/]")

                case AgentStatusType.ITERATION_COMPLETE:
                    if status.data:
                        success = status.data.get("success", False)
                        if success:
                            output = status.data.get("output", "")
                            self._print_output(output, success=True)
                        else:
                            error = status.data.get("error", "Unknown error")
                            self._print_error(error)

                case AgentStatusType.ERROR:
                    if status.data:
                        error = status.data.get("error", "Unknown error")
                        self._print_error(error)

                case AgentStatusType.COMPLETED:
                    if status.data:
                        final_success = status.data.get("success", False)
                        final_iterations = status.data.get("iterations", 0)
                        final_is_complete = status.data.get("is_complete", False)

                    self._print_completion(
                        final_success,
                        final_iterations,
                        final_is_complete,
                    )

            # Always yield the status for streaming compatibility
            yield status

    async def execute(
        self,
        user_prompt: str,
        context: dict[str, Any] | None = None,
        max_iterations: int = 5,
        session_id: str | None = None,
        include_context: bool = False,
    ) -> dict[str, Any]:
        """
        Execute the coding agent and return final result with rich output.

        Non-streaming version that consumes all yields and returns the final result.
        Use execute_stream() for real-time progress updates.

        Args:
            user_prompt: User's request/question
            context: Additional context (file IDs, data, etc.)
            max_iterations: Maximum ReAct iterations
            session_id: Optional session ID for memory

        Returns:
            Dict with final result, code history, and metadata
        """
        final_status = None
        async for status in self.execute_stream(
            user_prompt=user_prompt,
            context=context,
            max_iterations=max_iterations,
            session_id=session_id,
            include_context=include_context,
        ):
            final_status = status

        if final_status and final_status.data:
            return final_status.data

        return {
            "success": False,
            "result": None,
            "code_history": [],
            "observations": [],
            "iterations": 0,
            "is_complete": False,
        }


# =============================================================================
# Example Usage
# =============================================================================


class DefaultRichCodingAgent(RichCodingAgent):
    """
    Default implementation of RichCodingAgent for general-purpose coding tasks.

    This agent can be used directly for code generation and execution
    with beautiful terminal output.

    Usage:
        agent = DefaultRichCodingAgent()
        result = await agent.execute(
            user_prompt="Calculate the sum of 1 to 100",
            context={}
        )
    """

    @property
    def system_prompt(self) -> str:
        return """You are a Python coding assistant operating as an iterative problem solver.

Your responsibility is to write clean, efficient, and correct Python code
to solve the user's problem. You are not required to reach the final answer
in a single turn. Multiple iterations are allowed and encouraged.

----------------------------------------------------------------------
ITERATIVE EXECUTION MODEL
----------------------------------------------------------------------

You may take multiple turns to complete a task.

In each iteration:
1. Reason about the problem and identify what is currently known.
2. Decide the next step required to move toward the solution.
3. Write Python code to perform that step.
4. Evaluate whether the task is complete or needs another iteration.

Set "final_answer": false if:
- further reasoning or exploration is needed,
- edge cases are not yet handled,
- results need verification,
- or errors occurred.

Set "final_answer": true only when:
- the problem is fully solved,
- the output is correct and validated,
- and no further computation is necessary.

----------------------------------------------------------------------
RESPONSE FORMAT (MANDATORY)
----------------------------------------------------------------------

You MUST always respond with a valid JSON object containing exactly
the following fields:

- "thoughts":
  High-level reasoning for the current step.
  Explain your approach and intent without hidden chain-of-thought.

- "code":
  Executable Python code for this iteration.

- "final_answer":
  Boolean flag indicating completion status.

Example:

{
  "thoughts": "I will first break down the problem and inspect the input to understand constraints.",
  "code": "print(input_data)",
  "final_answer": false
}

----------------------------------------------------------------------
CODING GUIDELINES
----------------------------------------------------------------------

1. Write clear, readable, and idiomatic Python code
2. Add comments where logic is non-trivial
3. Handle edge cases explicitly
4. Prefer correctness and clarity over brevity
5. Return meaningful and well-structured results
6. Break complex solutions into multiple iterations when appropriate

----------------------------------------------------------------------
EXECUTION ENVIRONMENT ASSUMPTIONS
----------------------------------------------------------------------

- Code runs in a sandboxed Python environment
- Common libraries such as pandas and numpy may be available
- Context variables provided by the system are accessible
- The final expression in the code block is returned automatically
- Use print() for intermediate inspection if needed
- Do NOT define the final_answer variable inside the Python code

----------------------------------------------------------------------
WORKING PHILOSOPHY
----------------------------------------------------------------------

Approach each task like an experienced engineer:
- reason before coding
- verify assumptions
- test intermediate results
- iterate until the solution is correct and complete
- Use previous context if available to continue the task

Proceed using this iterative, disciplined approach.
"""
