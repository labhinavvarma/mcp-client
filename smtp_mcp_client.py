#!/usr/bin/env python
"""
smtp_mcp_client.py

MCP client that connects to and interacts with the SMTP MCP server.
This client allows you to:
1. Start the SMTP server
2. Configure SMTP settings
3. Test the SMTP connection
4. Send emails
"""

import asyncio
import os
import sys
import json
import argparse
import subprocess
from contextlib import AsyncExitStack

# MCP Client Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Default configuration path
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smtp_config.json")

# ASCII art banner
BANNER = """
┌─────────────────────────────────────────┐
│             SMTP MCP CLIENT             │
│         Email Sending Interface         │
└─────────────────────────────────────────┘
"""

def print_banner():
    """Print the application banner"""
    print(BANNER)

def read_config():
    """Read the SMTP configuration from file"""
    try:
        if os.path.exists(DEFAULT_CONFIG_PATH):
            with open(DEFAULT_CONFIG_PATH, 'r') as f:
                return json.load(f)
        else:
            return {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "use_tls": True,
                "email": "",
                "password": ""
            }
    except Exception as e:
        print(f"Error reading config: {e}")
        return None

def save_config(config):
    """Save the SMTP configuration to file"""
    try:
        with open(DEFAULT_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

async def start_smtp_server():
    """Start the SMTP MCP server as a subprocess"""
    # Path to the SMTP server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(script_dir, "smtp_mcp_server.py")
    
    if not os.path.exists(server_script):
        print(f"❌ SMTP server script not found at: {server_script}")
        return None
    
    # Start the server process
    print(f"🚀 Starting SMTP server: {server_script}")
    
    # Set environment variables
    env = os.environ.copy()
    env["CONFIG_PATH"] = DEFAULT_CONFIG_PATH
    
    # Start the server process
    process = await asyncio.create_subprocess_exec(
        sys.executable, server_script,
        "--transport", "stdio",
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    print("✅ SMTP server started")
    return process

async def run_client():
    """Run the SMTP MCP client"""
    print_banner()
    
    # Start the SMTP server
    server_process = await start_smtp_server()
    if not server_process:
        print("❌ Failed to start SMTP server")
        return
    
    # Create server parameters
    server_params = StdioServerParameters(
        stdin=server_process.stdin,
        stdout=server_process.stdout
    )
    
    # Setup error output handling
    async def handle_stderr():
        while True:
            line = await server_process.stderr.readline()
            if not line:
                break
            error_text = line.decode().strip()
            if error_text:
                print(f"🔴 Server: {error_text}")
    
    stderr_task = asyncio.create_task(handle_stderr())
    
    try:
        # Connect to the server
        print("🔄 Connecting to SMTP MCP server...")
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                print("✅ Connected to SMTP MCP server")
                
                # Get available tools
                methods = await session.list_methods()
                print(f"📋 Available tools: {', '.join(methods)}")
                
                # Interactive loop
                await interactive_loop(session)
    
    except asyncio.CancelledError:
        print("❌ Client was cancelled")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up
        stderr_task.cancel()
        try:
            server_process.kill()
            await server_process.wait()
        except Exception:
            pass
        print("👋 SMTP MCP client closed")

async def interactive_loop(session):
    """Interactive command loop for the SMTP client"""
    while True:
        print("\n📎 SMTP Client Menu:")
        print("1. Configure SMTP settings")
        print("2. Test SMTP connection")
        print("3. Send email")
        print("4. View current configuration")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == "1":
            await configure_smtp(session)
        elif choice == "2":
            await test_connection(session)
        elif choice == "3":
            await send_email(session)
        elif choice == "4":
            await view_config(session)
        elif choice == "5":
            print("Exiting SMTP client...")
            break
        else:
            print("❌ Invalid choice. Please enter a number from 1 to 5.")

async def configure_smtp(session):
    """Configure SMTP settings"""
    print("\n⚙️ Configure SMTP Settings")
    
    # Get current config
    current_config = read_config()
    
    # Get user input
    smtp_server = input(f"SMTP Server [{current_config.get('smtp_server', '')}]: ") or current_config.get('smtp_server', '')
    
    # Get port with validation
    while True:
        port_input = input(f"SMTP Port [{current_config.get('smtp_port', 587)}]: ") or str(current_config.get('smtp_port', 587))
        try:
            smtp_port = int(port_input)
            break
        except ValueError:
            print("❌ Port must be a number")
    
    # Get TLS setting
    use_tls_input = input(f"Use TLS (yes/no) [{current_config.get('use_tls', True) and 'yes' or 'no'}]: ") or (current_config.get('use_tls', True) and 'yes' or 'no')
    use_tls = use_tls_input.lower() in ('yes', 'y', 'true', 't', '1')
    
    email = input(f"Email [{current_config.get('email', '')}]: ") or current_config.get('email', '')
    
    # Only prompt for password if it's not already set or the user changed the email
    if not current_config.get('password') or email != current_config.get('email', ''):
        password = input("Password: ")
    else:
        password = input("Password (leave empty to keep current): ") or current_config.get('password', '')
    
    # Call the configure_smtp method on the server
    result = await session.call_method("configure_smtp", {
        "smtp_server": smtp_server,
        "smtp_port": smtp_port,
        "use_tls": use_tls,
        "email": email,
        "password": password
    })
    
    print(f"🔄 {result}")

async def test_connection(session):
    """Test the SMTP connection"""
    print("\n🔄 Testing SMTP connection...")
    result = await session.call_method("test_smtp_connection", {})
    print(f"📊 Test result: {result}")

async def send_email(session):
    """Send an email"""
    print("\n📧 Send Email")
    
    to = input("To (comma-separated for multiple recipients): ")
    subject = input("Subject: ")
    
    print("Body (end with a line containing only '.'): ")
    body_lines = []
    while True:
        line = input()
        if line == '.':
            break
        body_lines.append(line)
    body = '\n'.join(body_lines)
    
    cc = input("CC (optional, comma-separated): ")
    bcc = input("BCC (optional, comma-separated): ")
    
    use_html = input("Send as HTML? (yes/no) [no]: ").lower() in ('yes', 'y', 'true', 't', '1')
    
    if use_html:
        html_body = body
        result = await session.call_method("send_email", {
            "to": to,
            "subject": subject,
            "body": body,  # Plain text fallback
            "html_body": html_body,
            "cc": cc,
            "bcc": bcc
        })
    else:
        result = await session.call_method("send_email", {
            "to": to,
            "subject": subject,
            "body": body,
            "cc": cc,
            "bcc": bcc
        })
    
    print(f"📬 {result}")

async def view_config(session):
    """View the current SMTP configuration"""
    print("\n⚙️ Current SMTP Configuration")
    result = await session.call_method("get_smtp_config", {})
    
    try:
        config = json.loads(result)
        for key, value in config.items():
            print(f"{key}: {value}")
    except Exception:
        print(result)

if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("\n👋 SMTP client stopped by user")