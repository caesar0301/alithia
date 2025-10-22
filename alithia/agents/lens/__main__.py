"""
CLI entrypoint for the AlithiaLens agent.
"""

import logging

import typer

from alithia.agents.lens.agent import LensAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = typer.Typer(help="AlithiaLens - Deep Paper Interaction Agent")


@app.command(name="interact", help="Start an interactive session with a research paper.")
def interact_with_paper(
    paper_id: str = typer.Argument(..., help="The ArXiv ID, DOI, or PDF path of the paper to analyze."),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode for more verbose output."),
):
    """
    Starts an interactive session to ask questions and analyze a specific research paper.
    """
    logger.info(f"Starting AlithiaLens session for paper: '{paper_id}'")

    # The initial query tells the agent to load the paper first.
    initial_query = f"load {paper_id}"
    config = {
        "initial_query": initial_query,
        "debug": debug,
    }

    agent = LensAgent()
    # The 'run' method will handle the interactive loop based on the graph design.
    # In a real implementation, the nodes would handle real-time user input.
    # Here, we run the pre-scripted conversation from the nodes.
    typer.echo("Starting scripted interaction with AlithiaLens...")
    typer.echo(f"Agent will simulate the following conversation:")
    typer.echo(f"1. User: {initial_query}")
    typer.echo(f"2. User: What is the main contribution?")
    typer.echo(f"3. User: exit")
    typer.echo("-" * 20)

    result = agent.run(config)

    typer.echo("-" * 20)
    if result["success"]:
        typer.secho("✅ AlithiaLens session completed successfully.", fg=typer.colors.GREEN)
    else:
        typer.secho(f"❌ AlithiaLens session failed: {result.get('error')}", fg=typer.colors.RED)


if __name__ == "__main__":
    app()
