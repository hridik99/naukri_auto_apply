import argparse
import sys
from rich.console import Console
from rich.table import Table
from app.config import load_config
from app.bot import NaukriAutoApplyBot
from app.tracker import ApplicationTracker

console = Console()

def main():
    parser = argparse.ArgumentParser(description="Naukri AI Auto-Apply Bot CLI")
    parser.add_argument("--login", action="store_true", help="Launch browser for one-time manual login & session save")
    parser.add_argument("--logout", action="store_true", help="Clear saved browser session & login data to switch accounts")
    parser.add_argument("--dry-run", action="store_true", help="Run bot without submitting applications")
    parser.add_argument("--run", action="store_true", help="Start automated application loop")
    parser.add_argument("--recommended", action="store_true", default=True, help="Apply to profile-matched Recommended Jobs (Default)")
    parser.add_argument("--search", action="store_true", help="Apply to Search query listings instead of recommendations")
    parser.add_argument("--headed", action="store_true", help="Force visible Chrome browser window (default is background headless)")
    parser.add_argument("--headless", action="store_true", help="Force background headless mode")
    parser.add_argument("--max-jobs", type=int, default=None, help="Override maximum applications for this run")
    parser.add_argument("--status", action="store_true", help="View recent application history and today count")
    parser.add_argument("--config", type=str, default=None, help="Path to custom config.json")
    
    args = parser.parse_args()

    if args.status:
        tracker = ApplicationTracker()
        today = tracker.get_todays_count()
        console.print(f"\n[bold cyan]Applications Submitted Today:[/bold cyan] [bold green]{today}[/bold green]")
        console.print(f"[dim]CSV Log:[/dim] {tracker.csv_path}")
        console.print(f"[dim]Markdown Log:[/dim] {tracker.md_path}")
        console.print(f"[dim]Cross-verify directly on Naukri:[/dim] [bold blue]https://www.naukri.com/mnjuser/appliedjobs[/bold blue]\n")
        
        summary = tracker.get_summary(limit=50)
        if summary:
            table = Table(title="Recent Applied Jobs Log", show_lines=True)
            table.add_column("Date / Time", style="cyan", no_wrap=True)
            table.add_column("Company", style="bold magenta")
            table.add_column("Job Title", style="green")
            table.add_column("Location", style="yellow")
            table.add_column("Status", style="bold")
            table.add_column("Job URL", style="blue")

            for row in summary:
                status_style = "[green]APPLIED[/green]" if row["status"] == "APPLIED" else f"[yellow]{row['status']}[/yellow]"
                table.add_row(
                    row.get("applied_date", "")[:19],
                    row.get("company", "N/A"),
                    row.get("title", "N/A"),
                    row.get("location", "N/A"),
                    status_style,
                    row.get("job_url", "")
                )
            console.print(table)
        else:
            console.print("[yellow]No applications logged yet.[/yellow]")
        return

    config = load_config(args.config)

    # Determine headless mode preference
    headless = None
    if args.headed:
        headless = False
    elif args.headless:
        headless = True

    if args.logout:
        import shutil
        from pathlib import Path
        user_data = Path(__file__).resolve().parent / "data" / "chrome_user_data"
        if user_data.exists():
            shutil.rmtree(user_data, ignore_errors=True)
            console.print("[bold green]Successfully cleared saved browser session and logged out.[/bold green]")
            console.print("[cyan]You can now run [bold]python run.py --login[/bold] to log into your new Naukri account.[/cyan]")
        else:
            console.print("[yellow]No active browser session was found.[/yellow]")
        return

    if args.login:
        bot = NaukriAutoApplyBot(config)
        bot.manual_login_mode()
        return

    if args.dry_run or args.run:
        bot = NaukriAutoApplyBot(config)
        use_search = args.search
        bot.run(max_applications=args.max_jobs, dry_run=args.dry_run, headless=headless, use_search=use_search)
        return

    parser.print_help()

if __name__ == "__main__":
    main()
