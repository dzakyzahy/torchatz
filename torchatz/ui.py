"""
Terminal User Interface for TorChatZ using prompt_toolkit and rich.
Designed for Kali Linux & Windows CMD/PowerShell with full copy-paste,
history, and rich color rendering.
"""

import sys
import os
import time
import threading
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
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML

from .config import Config
from .network import NetworkManager
from .tor_manager import TorManager


def get_clipboard_text() -> str:
    """Safely retrieves text from the operating system clipboard (Windows & Linux)."""
    import sys
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            user32.OpenClipboard.argtypes = [wintypes.HWND]
            user32.OpenClipboard.restype = wintypes.BOOL
            user32.CloseClipboard.argtypes = []
            user32.CloseClipboard.restype = wintypes.BOOL
            user32.GetClipboardData.argtypes = [wintypes.UINT]
            user32.GetClipboardData.restype = wintypes.HANDLE
            kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
            kernel32.GlobalLock.restype = wintypes.LPVOID
            kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
            kernel32.GlobalUnlock.restype = wintypes.BOOL
            if user32.OpenClipboard(None):
                try:
                    h = user32.GetClipboardData(13)  # CF_UNICODETEXT
                    if h:
                        p = kernel32.GlobalLock(h)
                        if p:
                            try:
                                return ctypes.c_wchar_p(p).value or ""
                            finally:
                                kernel32.GlobalUnlock(h)
                finally:
                    user32.CloseClipboard()
        except Exception:
            pass

    elif sys.platform.startswith("linux"):
        import shutil, subprocess
        for bin_cmd in [["xclip", "-selection", "clipboard", "-o"], ["xsel", "-b", "-o"], ["wl-paste"]]:
            if shutil.which(bin_cmd[0]):
                try:
                    res = subprocess.run(bin_cmd, capture_output=True, text=True, timeout=1)
                    if res.returncode == 0:
                        return res.stdout
                except Exception:
                    pass

    # Fallback to tkinter
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        val = root.clipboard_get()
        root.destroy()
        return val or ""
    except Exception:
        pass

    return ""


COMMANDS = [
    "/help",
    "/myid",
    "/nick",
    "/add",
    "/alias",
    "/rename",
    "/del",
    "/contacts",
    "/list",
    "/connect",
    "/disconnect",
    "/reconnect",
    "/chat",
    "/home",
    "/leave",
    "/paste",
    "/send",
    "/sendfile",
    "/files",
    "/tor",
    "/onion",
    "/clear",
    "/update",
    "/pull",
    "/restart",
    "/reload",
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
        self.auto_switch_chat: bool = True
        self.history = InMemoryHistory()
        self.completer = WordCompleter(COMMANDS, ignore_case=True)

        self.kb = KeyBindings()

        @self.kb.add('c-v')
        def _on_paste_cv(event):
            txt = get_clipboard_text()
            if txt:
                event.current_buffer.insert_text(txt)

        @self.kb.add('s-insert')
        def _on_paste_si(event):
            txt = get_clipboard_text()
            if txt:
                event.current_buffer.insert_text(txt)

        self.session = PromptSession(
            history=self.history,
            completer=self.completer,
            key_bindings=self.kb
        )
        self.is_running = True

    def print_banner(self) -> None:
        title = Text("TorChatZ v1.0.0", style="bold cyan")
        subtitle = Text("Zero-Knowledge Anonymous P2P Terminal Chat over Tor Onion v3", style="bold green")
        banner_content = Text()
        banner_content.append("• Anonymity: ")
        banner_content.append("100% Tor Onion Service (No IP / No Network / No OS Leak)\n", style="yellow")
        banner_content.append("• My Onion:\n  ", style="bold yellow")
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
        table.add_row("/add <onion> [alias]", "Add a peer to contacts and connect immediately")
        table.add_row("/alias <old> <new>", "Rename alias of a contact (or /rename)")
        table.add_row("/del <alias/onion>", "Remove a peer from your contacts")
        table.add_row("/contacts or /list", "List all saved contacts and their online/offline status")
        table.add_row("/connect <alias/onion>", "Connect to a peer over Tor network")
        table.add_row("/reconnect", "Retry connecting to all offline contacts")
        table.add_row("/chat <alias/onion>", "Select active peer to chat with (or switch conversation)")
        table.add_row("/home or /leave", "Exit active chat room and return to Home menu")
        table.add_row("/disconnect [alias]", "Disconnect active connection to a peer")
        table.add_row("/paste", "Paste & send text/code directly from clipboard")
        table.add_row("/send <filepath>", "Send a photo, video, or file to the active peer")
        table.add_row("/files", "List downloaded files in the downloads/ directory")
        table.add_row("/tor [restart]", "Show Tor daemon status or restart onion circuit")
        table.add_row("/update or /pull", "Pull latest updates from GitHub and auto-reload")
        table.add_row("/restart", "Restart TorChatZ without closing terminal")
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

        self.console.print("\n[bold cyan]─── TorChatZ Identity & Network ───[/bold cyan]")
        self.console.print(f" • Username      : [bold white]{user}[/bold white]")
        self.console.print(f" • Onion Address : [bold magenta]{onion}[/bold magenta]")
        self.console.print(f" • SOCKS5 Proxy  : [green]127.0.0.1:{socks_p}[/green]")
        self.console.print(f" • Local Listener: [green]127.0.0.1:{listen_p}[/green]")
        self.console.print(f" • Downloads Dir : [dim]{self.config.downloads_dir.resolve()}[/dim]")
        self.console.print("[dim]Tip: Salin seluruh 56 karakter alamat .onion di atas untuk diberikan ke lawan chat.[/dim]\n")

    def print_contacts(self) -> None:
        table = Table(title="Contacts List", border_style="magenta")
        table.add_column("Status", justify="center", width=10)
        table.add_column("Alias", style="bold cyan")
        table.add_column("Onion Address (v3)", style="white")

        all_onions = set(self.config.contacts.keys())
        for o, c in self.net_mgr.connections.items():
            if c.is_alive:
                all_onions.add(o)

        if not all_onions:
            self.console.print("[yellow]No contacts found. Add one with: /add <onion_address> [alias][/yellow]\n")
            return

        for onion in all_onions:
            data = self.config.contacts.get(onion, {})
            alias = data.get("alias")
            if not alias and onion in self.net_mgr.connections:
                alias = self.net_mgr.connections[onion].peer_username
            if not alias:
                alias = onion[:10] + "..."
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

        # Auto-select active chat ONLY IF:
        # 1. No active peer is selected, AND
        # 2. self.auto_switch_chat is True (user has not explicitly exited to Home via /home)
        if not self.active_peer_onion and self.auto_switch_chat:
            self.active_peer_onion = sender_onion
            self.active_peer_alias = alias
            self.console.print(f"[dim]>> Obrolan otomatis disetel ke {alias}. Ketik /home untuk kembali ke Home.[/dim]")

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
            if onion not in self.config.contacts and onion and onion != "unknown":
                self.config.add_contact(onion, username)
                alias = username
            self.console.print(f"\n[bold green]● Peer connected:[/bold green] {username} ([cyan]{alias}[/cyan]) - [bold green]ONLINE[/bold green]")
        elif status == "disconnected":
            self.console.print(f"\n[bold red]○ Peer disconnected:[/bold red] {username} ([dim]{alias}[/dim]) - [dim red]OFFLINE[/dim red]")

    def on_system_log(self, level: str, message: str) -> None:
        color = {"info": "cyan", "success": "green", "warning": "yellow", "error": "red"}.get(level, "white")
        self.console.print(f"[{color}][*] {message}[/{color}]")

    # --- User Input Loop ---
    def run(self) -> None:
        self.print_banner()

        # Background worker: auto-connect to contacts ONCE on startup (no aggressive infinite loop)
        def _startup_auto_connect():
            time.sleep(2)
            if self.config.contacts and self.is_running:
                for onion in list(self.config.contacts.keys()):
                    if not self.is_running:
                        break
                    if not self.net_mgr.is_peer_online(onion):
                        self.net_mgr.connect_to_peer(onion, silent=True)

        threading.Thread(target=_startup_auto_connect, daemon=True).start()

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

            elif cmd in ("/tor", "/onion"):
                if arg1.lower() == "restart":
                    self.console.print("[yellow]Restarting Tor Onion service...[/yellow]")
                    self.tor_mgr.shutdown()
                    ok, msg = self.tor_mgr.setup_onion_service(self.config.listen_port)
                    if ok:
                        self.console.print(f"[green]✓ {msg}[/green]")
                    else:
                        self.console.print(f"[red]✗ {msg}[/red]")
                else:
                    det = self.tor_mgr.auto_detect_tor()
                    s_status = "[green]ONLINE[/green]" if det.get("socks_found") else "[red]OFFLINE[/red]"
                    c_status = "[green]ONLINE[/green]" if det.get("control_found") else "[red]OFFLINE[/red]"
                    self.console.print(f"[bold cyan]Tor Network Status:[/bold cyan]")
                    self.console.print(f" • SOCKS5 Proxy: 127.0.0.1:{det.get('socks_port')} ({s_status})")
                    self.console.print(f" • Control Port: 127.0.0.1:{det.get('control_port')} ({c_status})")
                    self.console.print(f" • Onion v3 Address: [bold magenta]{self.config.onion_address or 'Pending'}[/bold magenta]")
                    self.console.print("[dim]Tip: Use '/tor restart' to refresh your onion service circuit.[/dim]\n")

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
                    valid, msg, formatted_onion = Config.validate_onion_address(arg1)
                    if not valid:
                        self.console.print(f"[bold red]✗ {msg}[/bold red]")
                        clean_input = arg1.strip().lower().replace(".onion", "")
                        self.console.print(f"[dim]Input Anda: '{arg1}' ({len(clean_input)} karakter sebelum .onion)[/dim]")
                    else:
                        onion = self.config.add_contact(formatted_onion, arg2 or None)
                        alias = self.config.get_alias(onion)
                        self.console.print(f"[green]Added contact: {alias} ({onion})[/green]")
                        # Auto-connect immediately
                        self.net_mgr.connect_to_peer(onion)

            elif cmd in ("/alias", "/rename"):
                if not arg1 or not arg2:
                    self.console.print("[red]Usage: /alias <old_alias_or_onion> <new_alias>[/red]")
                else:
                    ok, msg = self.config.update_alias(arg1, arg2)
                    if ok:
                        self.console.print(f"[green]✓ {msg}[/green]")
                        onion = self.config.resolve_onion(arg2)
                        if onion and onion == self.active_peer_onion:
                            self.active_peer_alias = arg2
                    else:
                        self.console.print(f"[red]✗ {msg}[/red]")

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
                        valid, msg, formatted_onion = Config.validate_onion_address(arg1)
                        if valid:
                            onion = formatted_onion
                        else:
                            self.console.print(f"[red]Could not resolve: {arg1} ({msg})[/red]")
                    if onion:
                        self.net_mgr.connect_to_peer(onion)

            elif cmd == "/reconnect":
                self.console.print("[cyan]Attempting to reconnect to all offline contacts...[/cyan]")
                self.net_mgr.reconnect_contacts(silent=False)

            elif cmd == "/chat":
                if not arg1:
                    connected = [o for o, c in self.net_mgr.connections.items() if c.is_alive]
                    if connected:
                        self.console.print("[cyan]Daftar lawan bicara yang sedang terhubung (ONLINE):[/cyan]")
                        for o in connected:
                            a = self.config.get_alias(o)
                            self.console.print(f" • [bold green]/chat {a}[/bold green] ({o[:16]}...)")
                    else:
                        self.console.print("[yellow]Belum ada lawan bicara yang terhubung. Ketik /contacts atau /add <onion>[/yellow]")
                else:
                    onion = self.config.resolve_onion(arg1)
                    if not onion:
                        # Check by peer_username of active connections
                        for o, conn in self.net_mgr.connections.items():
                            if conn.peer_username.lower() == arg1.lower():
                                onion = o
                                break
                    if not onion:
                        self.console.print(f"[red]Could not resolve: {arg1}. Add it first with /add <onion> [alias][/red]")
                    else:
                        self.active_peer_onion = onion
                        self.active_peer_alias = self.config.get_alias(onion)
                        self.auto_switch_chat = True
                        self.console.print(f"[green]Active chat switched to: {self.active_peer_alias} ({self.active_peer_onion})[/green]")
                        # Automatically initiate connection if not already connected
                        if not self.net_mgr.is_peer_online(onion):
                            self.net_mgr.connect_to_peer(onion)

            elif cmd in ("/home", "/leave", "/back", "/main"):
                if self.active_peer_onion:
                    old_alias = self.active_peer_alias
                    self.active_peer_onion = None
                    self.active_peer_alias = None
                    self.auto_switch_chat = False
                    self.console.print(f"[yellow]Keluar dari ruang obrolan dengan {old_alias}. Kembali ke menu Home.[/yellow]")
                    self.console.print("[dim]Tip: Pesan baru tetap muncul di layar. Ketik /chat <alias> kapan pun untuk masuk lagi.[/dim]")
                else:
                    self.console.print("[yellow]Anda sudah berada di menu Home.[/yellow]")

            elif cmd == "/disconnect":
                target = arg1 or self.active_peer_alias or self.active_peer_onion
                if not target:
                    self.console.print("[red]Usage: /disconnect <alias_or_onion>[/red]")
                else:
                    onion = self.config.resolve_onion(target)
                    if not onion and target in self.net_mgr.connections:
                        onion = target
                    if onion:
                        conn = self.net_mgr.get_connection(onion)
                        if conn:
                            conn.close()
                            if self.active_peer_onion == onion:
                                self.active_peer_onion = None
                                self.active_peer_alias = None
                            self.console.print(f"[yellow]Koneksi ke {target} telah diputus.[/yellow]")
                        else:
                            self.console.print(f"[yellow]Tidak ada koneksi aktif ke {target}.[/yellow]")
                    else:
                        self.console.print(f"[red]Kontak '{target}' tidak ditemukan.[/red]")
            elif cmd == "/paste":
                if not self.active_peer_onion:
                    self.console.print("[yellow]No active peer selected. Choose one with /chat <alias>[/yellow]")
                else:
                    clip_text = get_clipboard_text()
                    if not clip_text:
                        self.console.print("[yellow]Clipboard is empty or could not be read.[/yellow]")
                    else:
                        conn = self.net_mgr.get_connection(self.active_peer_onion)
                        if not conn or not conn.is_alive:
                            self.console.print(f"[yellow]Peer {self.active_peer_alias} is offline. Attempting to connect...[/yellow]")
                            self.net_mgr.connect_to_peer(self.active_peer_onion)
                        else:
                            if conn.send_chat(clip_text):
                                timestr = time.strftime("%H:%M:%S")
                                lines = clip_text.splitlines()
                                self.console.print(f"[bold cyan][{timestr}] <Me (Pasted {len(lines)} lines / {len(clip_text)} chars)>[/bold cyan]")
                                if len(lines) <= 12:
                                    self.console.print(f"[dim]{clip_text}[/dim]")
                                else:
                                    preview = "\n".join(lines[:6]) + f"\n... [+{len(lines) - 6} more lines] ..."
                                    self.console.print(f"[dim]{preview}[/dim]")
                            else:
                                self.console.print("[red]Failed to send pasted content. Connection dropped.[/red]")

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

            elif cmd in ("/update", "/pull", "/upgrade"):
                force = (arg1.lower() in ("force", "-f", "--force"))
                if force:
                    self.console.print("[yellow]Mengambil update paksa dari GitHub (git fetch & reset)...[/yellow]")
                else:
                    self.console.print("[cyan]Memeriksa update terbaru dari GitHub (git pull)...[/cyan]")
                try:
                    import subprocess
                    project_root = Path(__file__).resolve().parent.parent
                    if force:
                        subprocess.run(["git", "fetch", "origin"], cwd=str(project_root), capture_output=True, text=True, timeout=30)
                        res = subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=str(project_root), capture_output=True, text=True, timeout=30)
                    else:
                        res = subprocess.run(["git", "pull"], cwd=str(project_root), capture_output=True, text=True, timeout=30)

                    out = ((res.stdout or "") + "\n" + (res.stderr or "")).strip()
                    if not force and ("Already up to date" in out or "Sudah up to date" in out):
                        self.console.print("[bold green]✓ TorChatZ sudah versi paling baru (Already up to date).[/bold green]")
                        self.console.print("[dim]Tip: Gunakan '/restart' jika ingin memuat ulang aplikasi atau '/update force' jika ada konflik file.[/dim]")
                    elif res.returncode == 0:
                        self.console.print("[bold green]✓ Update berhasil diterapkan dari GitHub![/bold green]")
                        self.console.print(f"[dim]{out}[/dim]")
                        self.console.print("[bold yellow]Memuat ulang (restarting) TorChatZ secara otomatis...[/bold yellow]")
                        time.sleep(1)
                        self.restart_app()
                    else:
                        self.console.print(f"[red]Gagal melakukan update (error {res.returncode}):[/red]\n{out}")
                        self.console.print("[dim]Tip: Jika ada konflik atau file lokal berubah, jalankan: /update force[/dim]")
                except Exception as e:
                    self.console.print(f"[red]Error saat menjalankan update: {str(e)}[/red]")

            elif cmd in ("/restart", "/reload"):
                self.console.print("[bold yellow]Memuat ulang (restarting) TorChatZ...[/bold yellow]")
                time.sleep(0.5)
                self.restart_app()

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

    def restart_app(self) -> None:
        """Cleanly shutdown current instance and restart the application in-place."""
        self.cleanup()
        if sys.platform == "win32":
            import subprocess
            subprocess.call([sys.executable] + sys.argv)
            sys.exit(0)
        else:
            os.execv(sys.executable, [sys.executable] + sys.argv)
