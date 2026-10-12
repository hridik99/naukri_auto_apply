import os
import logging
from pathlib import Path
from rich.console import Console

console = Console()

LOG_DIR = Path(__file__).resolve().parent.parent / "data"
LOG_FILE = LOG_DIR / "bot.log"

def setup_logger():
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("naukri_bot")
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

log = setup_logger()

def log_info(msg: str, console_style: str = "cyan"):
    clean_msg = msg
    for tag in ["[bold]", "[/bold]", "[dim]", "[/dim]", "[cyan]", "[/cyan]", "[blue]", "[/blue]", "[magenta]", "[/magenta]"]:
        clean_msg = clean_msg.replace(tag, "")
    log.info(clean_msg)
    if console_style:
        console.print(f"[{console_style}]{msg}[/{console_style}]")
    else:
        console.print(msg)

def log_success(msg: str):
    clean_msg = msg.replace("[bold green]", "").replace("[/bold green]", "").replace("[green]", "").replace("[/green]", "")
    log.info(f"SUCCESS: {clean_msg}")
    console.print(f"[bold green]{msg}[/bold green]")

def log_warning(msg: str):
    clean_msg = msg.replace("[bold yellow]", "").replace("[/bold yellow]", "").replace("[yellow]", "").replace("[/yellow]", "").replace("[dim]", "").replace("[/dim]", "")
    log.warning(clean_msg)
    console.print(f"[yellow]{msg}[/yellow]")

def log_error(msg: str):
    clean_msg = msg.replace("[bold red]", "").replace("[/bold red]", "").replace("[red]", "").replace("[/red]", "")
    log.error(clean_msg)
    console.print(f"[bold red]{msg}[/bold red]")
