#!/usr/bin/env python3
"""
TorChatZ - Anonymous Peer-to-Peer Terminal Chat over Tor Onion Services v3.
Runs on Kali Linux (terminal) and Windows (CMD / PowerShell).
Zero-Knowledge IP & OS identity protection.
"""

import sys
import argparse
import signal
from pathlib import Path

from rich.console import Console

from torchatz.config import Config
from torchatz.tor_manager import TorManager
from torchatz.file_transfer import FileTransferManager
from torchatz.network import NetworkManager
from torchatz.ui import TerminalUI

console = Console()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="TorChatZ - Anonymous P2P Terminal Chat over Tor (v3 Onion Services)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=11009,
        help="Local port to listen for incoming connections (default: 11009)"
    )
    parser.add_argument(
        "--socks-port", "-s",
        type=int,
        default=None,
        help="Tor SOCKS5 proxy port (default: auto-detect 9050 or 9150)"
    )
    parser.add_argument(
        "--control-port", "-c",
        type=int,
        default=None,
        help="Tor Control port (default: auto-detect 9051 or 9151)"
    )
    parser.add_argument(
        "--nick", "-n",
        type=str,
        default=None,
        help="Set your pseudonymous display name"
    )
    parser.add_argument(
        "--onion",
        type=str,
        default=None,
        help="Manual/Static Onion address (if not using automatic ephemeral service)"
    )
    parser.add_argument(
        "--dev-mode",
        action="store_true",
        help="Developer mode: Skip Tor checks for local loopback testing"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    config = Config()

    if args.nick:
        config.username = args.nick
    if args.socks_port:
        config.socks_port = args.socks_port
    if args.control_port:
        config.control_port = args.control_port
    if args.onion:
        config.onion_address = args.onion

    file_mgr = FileTransferManager(config.downloads_dir)
    tor_mgr = TorManager(config)

    ui = None

    def _on_msg(sender, user, text, ts):
        if ui:
            ui.on_message_received(sender, user, text, ts)

    def _on_f_start(sender, user, fname, fsize):
        if ui:
            ui.on_file_start(sender, user, fname, fsize)

    def _on_f_prog(sender, fname, rec, tot):
        if ui:
            ui.on_file_progress(sender, fname, rec, tot)

    def _on_f_done(sender, user, path, ok, msg):
        if ui:
            ui.on_file_complete(sender, user, path, ok, msg)

    def _on_status(onion, user, status):
        if ui:
            ui.on_status_change(onion, user, status)

    def _on_log(lvl, msg):
        if ui:
            ui.on_system_log(lvl, msg)
        else:
            console.print(f"[*] {msg}")

    net_mgr = NetworkManager(
        config=config,
        file_mgr=file_mgr,
        on_message=_on_msg,
        on_file_start=_on_f_start,
        on_file_progress=_on_f_prog,
        on_file_complete=_on_f_done,
        on_status_change=_on_status,
        on_system_log=_on_log,
    )

    ui = TerminalUI(config, tor_mgr, net_mgr)

    # Signal handlers for clean termination
    def _sig_handler(sig, frame):
        if ui:
            ui.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig_handler)

    # 1. Start local inbound listener
    ok_listen, listen_msg = net_mgr.start_listener()
    if not ok_listen:
        console.print(f"[bold red]Listener Error:[/bold red] {listen_msg}")
        sys.exit(1)

    # 2. Setup Tor Onion Service
    if not args.dev_mode:
        with console.status("[bold cyan]Connecting to Tor and setting up Onion Service...[/bold cyan]"):
            ok_onion, onion_msg = tor_mgr.setup_onion_service(local_port=config.listen_port)

        if not ok_onion:
            console.print(f"[bold yellow][!] Tor Warning:[/bold yellow]\n{onion_msg}\n")
            console.print("[dim]You can still receive connections if you configure Tor's torrc manually.[/dim]\n")
        else:
            console.print(f"[bold green]✓ {onion_msg}[/bold green]\n")
    else:
        config.onion_address = "dev_mode_local.onion"
        console.print("[yellow][!] DEV-MODE active: Tor setup bypassed for local testing.[/yellow]\n")

    # 3. Start Terminal UI
    try:
        ui.run()
    except Exception as e:
        console.print(f"[bold red]Fatal runtime error:[/bold red] {str(e)}")
    finally:
        ui.cleanup()


if __name__ == "__main__":
    main()
