"""
cli.py - Main CLI for SkillForge
Utilitarian command-line interface for compiling, validating, and managing Agent Skills.
"""

import json
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .compiler.python_ast import PythonASTExtractor
from .compiler.cli_parser import CLIToolExtractor
from .compiler.doc_parser import DocumentationParser
from .compiler.generator import SkillPackageGenerator
from .compiler.validator import SkillStandardValidator
from .manager.registry import SkillRegistryManager

console = Console()


@click.group()
def main():
    """SkillForge: Agent Skill Open Standard Compiler and Package Manager."""
    pass


@main.command()
@click.argument("source")
@click.option("--output", "-o", default="./output_skills", help="Destination root directory for compiled skill")
@click.option("--name", "-n", default=None, help="Override skill identifier (kebab-case)")
@click.option("--type", "-t", "source_type", type=click.Choice(["auto", "python", "cli", "doc"]), default="auto", help="Source type")
def compile(source, output, name, source_type):
    """Compile any Python library, CLI tool, or documentation into a compliant Agent Skill."""
    src_path = Path(source)
    console.print(f"[bold white]Compiling Agent Skill from:[/bold white] [cyan]{source}[/cyan]")

    # 1. Extraction phase
    if source_type == "python" or (source_type == "auto" and (src_path.suffix == ".py" or src_path.is_file())):
        extractor = PythonASTExtractor(source)
        meta = extractor.extract()
    elif source_type == "doc" or (source_type == "auto" and src_path.suffix in [".md", ".txt"]):
        doc_parser = DocumentationParser(source)
        doc_data = doc_parser.parse()
        from .compiler.base import ExtractedToolMeta, CapabilitySpec
        s_name = name or src_path.stem.lower().replace("_", "-")
        meta = ExtractedToolMeta(
            name=s_name,
            title=src_path.stem.replace("_", " ").title(),
            description=f"Documentation reference and capabilities for {src_path.stem}.",
            source_type="doc",
            source_path=str(src_path),
            capabilities=[
                CapabilitySpec(
                    name=f"inspect-{s_name}",
                    description=f"Inspects specifications for {s_name}",
                    parameters=[]
                )
            ]
        )
    else:
        # CLI tool or executable
        cli_extractor = CLIToolExtractor(source, is_command=True)
        meta = cli_extractor.extract()

    if name:
        meta.name = name

    console.print(f"Detected [bold green]{len(meta.capabilities)}[/bold green] capabilities in source.")

    # 2. Package generation phase
    out_root = Path(output)
    generator = SkillPackageGenerator(out_root)
    compiled = generator.generate(meta)

    console.print(Panel.fit(
        f"Skill: [bold white]{compiled.name}[/bold white]\n"
        f"Location: [cyan]{compiled.output_dir}[/cyan]\n"
        f"Status: [{'bold green' if compiled.is_compliant else 'bold red'}]{'COMPLIANT' if compiled.is_compliant else 'NON-COMPLIANT'}[/] "
        f"Score: [bold cyan]{compiled.validation_report['score']}/100[/bold cyan]",
        title="Compilation Summary"
    ))

    # Display files generated
    table = Table(title="Generated Package Files", border_style="dim")
    table.add_column("Type", style="bold white")
    table.add_column("Filename", style="cyan")
    table.add_column("Path", style="dim")

    table.add_row("Specification", "SKILL.md", str(compiled.output_dir / "SKILL.md"))
    for s_name in compiled.scripts:
        table.add_row("Runner Script", s_name, str(compiled.output_dir / "scripts" / s_name))
    for e_name in compiled.examples:
        table.add_row("Fixture", e_name, str(compiled.output_dir / "examples" / e_name))
    for r_name in compiled.references:
        table.add_row("Reference", r_name, str(compiled.output_dir / "references" / r_name))

    console.print(table)


@main.command()
@click.argument("skill_dir")
def validate(skill_dir):
    """Audit any Agent Skill against Agent Skill Open Standard (ASOS)."""
    target = Path(skill_dir)
    validator = SkillStandardValidator(target)
    report = validator.audit()

    console.print()
    console.print(Panel.fit(
        f"Target: [cyan]{report['skill_path']}[/cyan]\n"
        f"Compliance: [{'bold green' if report['compliant'] else 'bold red'}]{'PASS (100% Compliant)' if report['compliant'] else 'FAIL'}[/] | "
        f"Score: [bold cyan]{report['score']}/100[/bold cyan]",
        title="Agent Skill Open Standard Audit"
    ))

    table = Table(title="Specification Checklist", border_style="dim")
    table.add_column("Rule", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    for chk in report["checks"]:
        st = "[bold green]PASS[/bold green]" if chk["passed"] else "[bold red]FAIL[/bold red]"
        table.add_row(chk["name"], st, chk["message"])

    console.print(table)
    if not report["compliant"]:
        sys.exit(1)


@main.command()
@click.argument("skill_dir")
@click.option("--target", "-t", default=None, help="Target skills directory")
@click.option("--workspace", "-w", is_flag=True, help="Install to workspace (.agents/skills)")
@click.option("--global", "-g", "is_global", is_flag=True, help="Install globally (~/.gemini/config/skills)")
def install(skill_dir, target, workspace, is_global):
    """Install a compiled skill into an AI agent workspace or global registry."""
    if target:
        t_dir = Path(target).resolve()
    elif is_global:
        t_dir = Path.home() / ".gemini" / "config" / "skills"
    else:
        t_dir = Path.cwd() / ".agents" / "skills"

    res = SkillRegistryManager.install_skill(Path(skill_dir), t_dir)
    if res["success"]:
        console.print(f"[bold green][SUCCESS][/bold green] Installed [white]{res['skill_name']}[/white] into [cyan]{res['installed_path']}[/cyan]")
    else:
        console.print(f"[bold red][ERROR][/bold red] {res['error']}")
        sys.exit(1)


@main.command("list")
@click.option("--target", "-t", default=None, help="Skills directory to inspect")
def list_skills(target):
    """List all installed skills in active workspace or global registry."""
    t_dir = Path(target) if target else Path.cwd() / ".agents" / "skills"
    skills = SkillRegistryManager.list_skills(t_dir)

    table = Table(title=f"Installed Skills in {t_dir}", border_style="dim")
    table.add_column("Skill Name", style="bold white")
    table.add_column("Version", style="cyan")
    table.add_column("Compliance", justify="center")
    table.add_column("Description", style="dim")

    if not skills:
        console.print(f"No skills found in [cyan]{t_dir}[/cyan]")
        return

    for s in skills:
        st = "[bold green]PASS[/bold green]" if s["compliant"] else "[bold red]FAIL[/bold red]"
        desc = (s["description"][:60] + "...") if len(s["description"]) > 60 else s["description"]
        table.add_row(s["name"], s["version"], st, desc)

    console.print(table)


@main.command()
@click.argument("skill_dir")
@click.option("--output", "-o", default=None, help="Output zip filename")
def export(skill_dir, output):
    """Export skill into portable distribution archive (.zip)."""
    s_path = Path(skill_dir)
    out_zip = Path(output) if output else s_path.with_suffix(".zip")
    archive = SkillRegistryManager.export_archive(s_path, out_zip)
    console.print(f"[bold green][SUCCESS][/bold green] Exported skill bundle to [cyan]{archive}[/cyan]")


@main.command()
@click.option("--port", "-p", default=8899, help="Port to serve developer console")
def serve(port):
    """Launch local developer studio."""
    from .web.server import run_server
    run_server(port=port)


if __name__ == "__main__":
    main()
