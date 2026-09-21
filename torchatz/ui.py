"""
Terminal User Interface for TorChatZ using prompt_toolkit and rich.
Designed for Kali Linux & Windows CMD/PowerShell with full copy-paste,
history, and rich color rendering.
"""

import sys
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML

from .config import Config
from .network import NetworkManager
from .tor_manager import TorManager

COMMANDS = [
    "/help",
    "/myid",
    "/nick",
    "/add",
    "/del",
    "/contacts",
    "/list",
    "/connect",
    "/chat",
    "/send",
    "/sendfile",
    "/files",
    "/clear",
    "/quit",
    "/exit",
]


class TerminalUI:
    def __init__(self, config: Config, tor_mgr: TorManager, net_mgr: NetworkManager):
        self.config = config
        self.tor_mgr = tor_mgr
        self.net_mgr = net_mgr

        self.console = Console()
        self.active_peer_onion: Optional[str] = None
        self.active_peer_alias: Optional[str] = None
        self.history = InMemoryHistory()
        self.completer = WordCompleter(COMMANDS, ignore_case=True)
        self.session = PromptSession(history=self.history, completer=self.completer)
        self.is_running = True

    def print_banner(self) -> None:
        title = Text("TorChatZ v1.0.0", style="bold cyan")
        subtitle = Text("Zero-Knowledge Anonymous P2P Terminal Chat over Tor Onion v3", style="bold green")
        banner_content = Text()
        banner_content.append("• Anonymity: ")
        banner_content.append("100% Tor Onion Service (No IP / No Network / No OS Leak)\n", style="yellow")
        banner_content.append("• My Onion: ")
        banner_content.append(f"{self.config.onion_address or 'Initializing...'}\n", style="bold magenta")
        banner_content.append("• My Nick: ")
        banner_content.append(f"{self.config.username}\n", style="bold cyan")
        banner_content.append("• Help: Type ")
        banner_content.append("/help", style="bold white on blue")
        banner_content.append(" for list of commands.\n")
        banner_content.append("• Copy & Paste: Standard terminal copy / paste (Ctrl+V / Right-Click) is fully supported.")

        panel = Panel(
            banner_content,
            title=f"{title.plain} - {subtitle.plain}",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)

    def print_help(self) -> None:
        table = Table(title="Available Commands", border_style="dim")
        table.add_column("Command", style="cyan bold", width=22)
        table.add_column("Description", style="white")

        table.add_row("/myid", "Display your .onion address and current configuration")
        table.add_row("/nick <username>", "Change your pseudonymous display name")
        table.add_row("/add <onion> [alias]", "Add a peer to your contact list with optional alias")
        table.add_row("/del <alias/onion>", "Remove a peer from your contacts")
        table.add_row("/contacts or /list", "List all saved contacts and their online/offline status")
        table.add_row("/connect <alias/onion>", "Connect to a peer over Tor network")
        table.add_row("/chat <alias/onion>", "Select active peer to chat with (or switch conversation)")
        table.add_row("/send <filepath>", "Send a photo, video, or file to the active peer")
        table.add_row("/files", "List downloaded files in the downloads/ directory")
        table.add_row("/clear", "Clear terminal screen")
        table.add_row("/help", "Show this help screen")
        table.add_row("/quit or /exit", "Exit TorChatZ cleanly")

        self.console.print(table)
        self.console.print("[dim]Tip: You can directly type text to send a message once a peer is selected via /chat <alias>.[/dim]\n")

    def print_my_id(self) -> None:
        onion = self.config.onion_address or "Not available"
        user = self.config.username
        socks_p = self.config.socks_port
        listen_p = self.config.listen_port

        table = Table(title="My Identity & Network Status", border_style="cyan")
        table.add_column("Property", style="bold yellow")
        table.add_column("Value", style="bold green")

        table.add_row("Username", user)
        table.add_row("Onion Address (v3)", onion)
        table.add_row("SOCKS5 Proxy", f"127.0.0.1:{socks_p}")
        table.add_row("Local Inbound Listener", f"127.0.0.1:{listen_p}")
        table.add_row("Downloads Folder", str(self.config.downloads_dir.resolve()))

        self.console.print(table)

    def print_contacts(self) -> None:
        table = Table(title="Contacts List", border_style="magenta")
        table.add_column("Status", justify="center", width=10)
        table.add_column("Alias", style="bold cyan")
        table.add_column("Onion Address (v3)", style="white")

        if not self.config.contacts:
            self.console.print("[yellow]No contacts found. Add one with: /add <onion_address> [alias][/yellow]\n")
            return

        for onion, data in self.config.contacts.items():
            alias = data.get("alias", onion[:10])
            online = self.net_mgr.is_peer_online(onion)
            status_text = "[bold green]ONLINE[/bold green]" if online else "[dim red]OFFLINE[/dim red]"
            table.add_row(status_text, alias, onion)

        self.console.print(table)

    def print_downloaded_files(self) -> None:
        table = Table(title=f"Downloads Directory ({self.config.downloads_dir})", border_style="green")
        table.add_column("Filename", style="bold cyan")
        table.add_column("Size", justify="right", style="yellow")
        table.add_column("Modified", style="dim")

        files = list(self.config.downloads_dir.glob("*"))
        valid_files = [f for f in files if f.is_file() and not f.name.startswith(".tmp_")]

        if not valid_files:
            self.console.print("[yellow]Downloads folder is empty.[/yellow]\n")
            return

        for f in valid_files:
            size_kb = f.stat().st_size / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.2f} MB"
            mod_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))
            table.add_row(f.name, size_str, mod_str)

        self.console.print(table)

    # --- Callbacks from Network Layer ---
    def on_message_received(self, sender_onion: str, sender_username: str, text: str, ts: int) -> None:
        alias = self.config.get_alias(sender_onion)
        timestr = time.strftime("%H:%M:%S", time.localtime(ts))
        self.console.print(f"\n[bold magenta][{timestr}] <{sender_username} ({alias})>[/bold magenta] {text}")

    def on_file_start(self, sender_onion: str, sender_username: str, filename: str, filesize: int) -> None:
        alias = self.config.get_alias(sender_onion)
        mb = filesize / (1024 * 1024)
        self.console.print(f"\n[bold yellow]>> Incoming file transfer from {sender_username} ({alias}):[/bold yellow] [bold cyan]{filename}[/bold cyan] ({mb:.2f} MB)")

    def on_file_progress(self, sender_onion: str, filename: str, received: int, total: int) -> None:
        # Progress can be shown cleanly
        pct = (received / total * 100) if total > 0 else 100
        if received >= total or received % (512 * 1024) < (64 * 1024):
            self.console.print(f"[dim]Downloading {filename}: {pct:.1f}% ({received // 1024} KB / {total // 1024} KB)[/dim]")

    def on_file_complete(self, sender_onion: str, sender_username: str, saved_path: str, success: bool, msg: str) -> None:
        alias = self.config.get_alias(sender_onion)
        if success:
            self.console.print(f"\n[bold green]✓ File transfer complete from {alias}![/bold green] Saved to: [bold white]{saved_path}[/bold white]")
        else:
            self.console.print(f"\n[bold red]✗ File transfer failed from {alias}:[/bold red] {msg}")

    def on_status_change(self, onion: str, username: str, status: str) -> None:
        alias = self.config.get_alias(onion)
        if status == "connected":
            self.console.print(f"\n[bold green]● Peer connected:[/bold green] {username} ([cyan]{alias}[/cyan])")
        elif status == "disconnected":
            self.console.print(f"\n[bold red]○ Peer disconnected:[/bold red] {username} ([dim]{alias}[/dim])")

    def on_system_log(self, level: str, message: str) -> None:
        color = {"info": "cyan", "success": "green", "warning": "yellow", "error": "red"}.get(level, "white")
        self.console.print(f"[{color}][*] {message}[/{color}]")

    # --- User Input Loop ---
    def run(self) -> None:
        self.print_banner()

        while self.is_running:
            try:
                # Format prompt
                if self.active_peer_onion:
                    prompt_label = f"[{self.config.username} -> {self.active_peer_alias}]> "
                else:
                    prompt_label = f"[{self.config.username}]> "

                user_input = self.session.prompt(prompt_label).strip()
                if not user_input:
                    continue

                self.handle_input(user_input)

            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Exiting TorChatZ...[/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {str(e)}[/red]")

        self.cleanup()

    def handle_input(self, text: str) -> None:
        if text.startswith("/"):
            parts = text.split(" ", 2)
            cmd = parts[0].lower()
            arg1 = parts[1] if len(parts) > 1 else ""
            arg2 = parts[2] if len(parts) > 2 else ""

            if cmd in ("/quit", "/exit"):
                self.is_running = False

            elif cmd == "/help":
                self.print_help()

            elif cmd == "/myid":
                self.print_my_id()

            elif cmd == "/clear":
                self.console.clear()
                self.print_banner()

            elif cmd in ("/contacts", "/list"):
                self.print_contacts()

            elif cmd == "/files":
                self.print_downloaded_files()

            elif cmd == "/nick":
                if not arg1:
                    self.console.print("[red]Usage: /nick <new_username>[/red]")
                else:
                    self.config.username = arg1
                    self.console.print(f"[green]Username updated to: {self.config.username}[/green]")

            elif cmd == "/add":
                if not arg1:
                    self.console.print("[red]Usage: /add <onion_address> [alias][/red]")
                else:
                    onion = self.config.add_contact(arg1, arg2 or None)
                    alias = self.config.get_alias(onion)
                    self.console.print(f"[green]Added contact: {alias} ({onion})[/green]")

            elif cmd == "/del":
                if not arg1:
                    self.console.print("[red]Usage: /del <alias_or_onion>[/red]")
                else:
                    if self.config.remove_contact(arg1):
                        self.console.print(f"[green]Removed contact: {arg1}[/green]")
                    else:
                        self.console.print(f"[red]Contact not found: {arg1}[/red]")

            elif cmd == "/connect":
                if not arg1:
                    self.console.print("[red]Usage: /connect <alias_or_onion>[/red]")
                else:
                    onion = self.config.resolve_onion(arg1)
                    if not onion:
                        self.console.print(f"[red]Could not resolve onion address for: {arg1}[/red]")
                    else:
                        self.net_mgr.connect_to_peer(onion)

            elif cmd == "/chat":
                if not arg1:
                    self.console.print("[red]Usage: /chat <alias_or_onion>[/red]")
                else:
                    onion = self.config.resolve_onion(arg1)
                    if not onion:
                        self.console.print(f"[red]Could not resolve: {arg1}. Add it first with /add <onion> [alias][/red]")
                    else:
                        self.active_peer_onion = onion
                        self.active_peer_alias = self.config.get_alias(onion)
                        self.console.print(f"[green]Active chat switched to: {self.active_peer_alias} ({self.active_peer_onion})[/green]")
                        # Automatically initiate connection if not already connected
                        if not self.net_mgr.is_peer_online(onion):
                            self.net_mgr.connect_to_peer(onion)

            elif cmd in ("/send", "/sendfile"):
                if not self.active_peer_onion:
                    self.console.print("[red]No active peer selected. Choose one with /chat <alias>[/red]")
                    return

                filepath_str = text[len(cmd):].strip()
                # Handle quoted paths on Windows/Linux
                if (filepath_str.startswith('"') and filepath_str.endswith('"')) or \
                   (filepath_str.startswith("'") and filepath_str.endswith("'")):
                    filepath_str = filepath_str[1:-1]

                filepath = Path(filepath_str)
                if not filepath.exists():
                    self.console.print(f"[red]File not found: {filepath}[/red]")
                    return

                conn = self.net_mgr.get_connection(self.active_peer_onion)
                if not conn or not conn.is_alive:
                    self.console.print("[red]Peer is not connected. Connecting first...[/red]")
                    self.net_mgr.connect_to_peer(self.active_peer_onion)
                    return

                self.console.print(f"[cyan]Sending file '{filepath.name}' to {self.active_peer_alias}...[/cyan]")
                
                def _progress(sent: int, total: int):
                    pct = (sent / total * 100) if total > 0 else 100
                    if sent >= total or sent % (512 * 1024) < (64 * 1024):
                        self.console.print(f"[dim]Uploading {filepath.name}: {pct:.1f}% ({sent // 1024} KB / {total // 1024} KB)[/dim]")

                success, message = conn.send_file(filepath, progress_callback=_progress)
                if success:
                    self.console.print(f"[green]✓ {message}[/green]")
                else:
                    self.console.print(f"[red]✗ {message}[/red]")

            else:
                self.console.print(f"[yellow]Unknown command '{cmd}'. Type /help for assistance.[/yellow]")

        else:
            # Direct chat message
            if not self.active_peer_onion:
                self.console.print("[yellow]No active peer selected! Use /chat <alias_or_onion> or /help[/yellow]")
                return

            conn = self.net_mgr.get_connection(self.active_peer_onion)
            if not conn or not conn.is_alive:
                self.console.print(f"[yellow]Peer {self.active_peer_alias} is offline. Attempting to connect...[/yellow]")
                self.net_mgr.connect_to_peer(self.active_peer_onion)
                return

            if conn.send_chat(text):
                timestr = time.strftime("%H:%M:%S")
                self.console.print(f"[bold cyan][{timestr}] <Me>[/bold cyan] {text}")
            else:
                self.console.print("[red]Failed to send message. Connection dropped.[/red]")

    def cleanup(self) -> None:
        self.net_mgr.shutdown()
        self.tor_mgr.shutdown()
