"""
CLI entrypoint for the AlithiaVigil agent.
"""

import logging

import typer

from alithia.agents.vigil.agent import VigilAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = typer.Typer(help="AlithiaVigil - Proactive Topic Monitoring Agent")


@app.command(name="monitor", help="Monitor topics and get alerts on new research.")
def monitor_topics(
    topic: str = typer.Option(..., "--topic", "-t", help="The research topic to monitor."),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode for more verbose output."),
):
    """
    Monitors a specified research topic for new and relevant papers, articles, and discussions.
    """
    logger.info(f"Starting AlithiaVigil to monitor topic: '{topic}'")

    # The config would be more complex in a real scenario
    config = {
        "topics": [topic],
        "debug": debug,
    }

    agent = VigilAgent()
    result = agent.run(config)

    if result["success"]:
        typer.secho("✅ AlithiaVigil run completed successfully.", fg=typer.colors.GREEN)
        summary = result.get("summary", {})
        final_step = summary.get("current_step", "unknown")
        papers_found = len(summary.get("discovered_papers", []))
        typer.echo(f"Final step: {final_step}")
        typer.echo(f"Items discovered: {papers_found}")
    else:
        typer.secho(f"❌ AlithiaVigil run failed: {result.get('error')}", fg=typer.colors.RED)


if __name__ == "__main__":
    app()
