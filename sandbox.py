#!/usr/bin/env python3
"""
SparzaFI Sandbox Manager - Interactive CLI
Easily set up and manage your testing environment
"""

import os
import sys
import subprocess
import sqlite3
import time
from datetime import datetime

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_banner():
    """Display SparzaFI banner"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ███████╗██████╗  █████╗ ██████╗ ███████╗ █████╗        ║
║   ██╔════╝██╔══██╗██╔══██╗██╔══██╗╚══███╔╝██╔══██╗       ║
║   ███████╗██████╔╝███████║██████╔╝  ███╔╝ ███████║       ║
║   ╚════██║██╔═══╝ ██╔══██║██╔══██╗ ███╔╝  ██╔══██║       ║
║   ███████║██║     ██║  ██║██║  ██║███████╗██║  ██║       ║
║   ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝       ║
║                                                           ║
║              🧪 SANDBOX MANAGER v1.0                      ║
║         Social Video Marketplace Platform                ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
{Colors.ENDC}"""
    print(banner)

def print_menu():
    """Display main menu"""
    menu = f"""
{Colors.BOLD}Main Menu:{Colors.ENDC}
{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}

  {Colors.GREEN}1.{Colors.ENDC} 🚀 Start Sandbox (Local + ngrok)
  {Colors.GREEN}2.{Colors.ENDC} 🔧 Quick Setup (Database Only)
  {Colors.GREEN}3.{Colors.ENDC} 🔄 Reset Database with Demo Data
  {Colors.GREEN}4.{Colors.ENDC} 📊 View Database Stats
  {Colors.GREEN}5.{Colors.ENDC} 👥 Show Demo Accounts
  {Colors.GREEN}6.{Colors.ENDC} 🌐 Get Network URLs
  {Colors.GREEN}7.{Colors.ENDC} 📦 Install ngrok
  {Colors.GREEN}8.{Colors.ENDC} ☁️  Deploy to Cloud
  {Colors.GREEN}9.{Colors.ENDC} 🛠️  Advanced Options
  {Colors.GREEN}0.{Colors.ENDC} 🚪 Exit

{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}
"""
    print(menu)

def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}✓{Colors.ENDC} {message}")

def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}✗{Colors.ENDC} {message}")

def print_info(message):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ{Colors.ENDC} {message}")

def print_warning(message):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠{Colors.ENDC} {message}")

def run_command(command, description=None):
    """Run a shell command and show output"""
    if description:
        print(f"\n{Colors.CYAN}Running:{Colors.ENDC} {description}")

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            if result.stdout:
                print(result.stdout)
            return True
        else:
            if result.stderr:
                print_error(result.stderr)
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def check_database():
    """Check if database exists"""
    return os.path.exists('sparzafi.db')

def get_database_stats():
    """Get database statistics"""
    if not check_database():
        print_error("Database not found!")
        return

    try:
        conn = sqlite3.connect('sparzafi.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        print(f"\n{Colors.BOLD}Database Statistics:{Colors.ENDC}")
        print(f"{Colors.CYAN}{'─' * 60}{Colors.ENDC}")

        # Users
        users = cursor.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
        print(f"  👥 Total Users: {Colors.GREEN}{users}{Colors.ENDC}")

        # Sellers
        sellers = cursor.execute("SELECT COUNT(*) as count FROM sellers").fetchone()['count']
        print(f"  🛍️  Sellers: {Colors.GREEN}{sellers}{Colors.ENDC}")

        # Products
        products = cursor.execute("SELECT COUNT(*) as count FROM products WHERE is_active = 1").fetchone()['count']
        print(f"  📦 Active Products: {Colors.GREEN}{products}{Colors.ENDC}")

        # Transactions
        transactions = cursor.execute("SELECT COUNT(*) as count FROM transactions").fetchone()['count']
        print(f"  💰 Total Transactions: {Colors.GREEN}{transactions}{Colors.ENDC}")

        # Pending orders
        pending = cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE status IN ('PENDING', 'CONFIRMED')").fetchone()['count']
        print(f"  📦 Pending Orders: {Colors.YELLOW}{pending}{Colors.ENDC}")

        # Reviews
        reviews = cursor.execute("SELECT COUNT(*) as count FROM reviews").fetchone()['count']
        print(f"  ⭐ Reviews: {Colors.GREEN}{reviews}{Colors.ENDC}")

        # Top seller
        top_seller = cursor.execute("""
            SELECT name, balance FROM sellers
            ORDER BY balance DESC LIMIT 1
        """).fetchone()

        if top_seller:
            print(f"\n  {Colors.BOLD}Top Seller:{Colors.ENDC} {top_seller['name']} (R{top_seller['balance']:.2f})")

        print(f"{Colors.CYAN}{'─' * 60}{Colors.ENDC}\n")

        conn.close()

    except Exception as e:
        print_error(f"Error reading database: {e}")

def show_demo_accounts():
    """Display demo accounts"""
    print(f"\n{Colors.BOLD}Demo Accounts:{Colors.ENDC}")
    print(f"{Colors.CYAN}{'─' * 60}{Colors.ENDC}")

    accounts = [
        ("🛡️  Admin", "admin@sparzafi.com", "adminpass", "Full platform management"),
        ("🛍️  Seller", "thandi@sparzafi.com", "sellerpass", "Thandi's Kitchen - R3,740 balance"),
        ("👤 Buyer", "buyer1@test.com", "buyerpass", "Browse, shop, review"),
        ("🚚 Deliverer", "sipho.driver@sparzafi.com", "driverpass", "Manage deliveries"),
    ]

    for role, email, password, description in accounts:
        print(f"\n  {Colors.GREEN}{role}{Colors.ENDC}")
        print(f"  Email:    {Colors.CYAN}{email}{Colors.ENDC}")
        print(f"  Password: {Colors.CYAN}{password}{Colors.ENDC}")
        print(f"  {Colors.YELLOW}→{Colors.ENDC} {description}")

    print(f"\n{Colors.CYAN}{'─' * 60}{Colors.ENDC}\n")

def get_network_urls():
    """Get local network URLs"""
    print(f"\n{Colors.BOLD}Network Access URLs:{Colors.ENDC}")
    print(f"{Colors.CYAN}{'─' * 60}{Colors.ENDC}")

    # Localhost
    print(f"\n  {Colors.GREEN}Local:{Colors.ENDC}")
    print(f"  http://localhost:5000")
    print(f"  http://127.0.0.1:5000")

    # Network IP
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"\n  {Colors.GREEN}Local Network:{Colors.ENDC}")
        print(f"  http://{local_ip}:5000")
        print(f"  {Colors.YELLOW}→{Colors.ENDC} Share this with devices on same WiFi")
    except:
        print_warning("Could not determine local IP")

    print(f"\n{Colors.CYAN}{'─' * 60}{Colors.ENDC}\n")

def setup_database():
    """Setup or reset database"""
    if check_database():
        print_warning("Database already exists!")
        choice = input(f"{Colors.YELLOW}Reset with fresh data? (y/n):{Colors.ENDC} ").lower()
        if choice != 'y':
            print_info("Keeping existing database")
            return

        print_info("Removing old database...")
        os.remove('sparzafi.db')

    print_info("Creating database schema...")
    if run_command("python3 database_seed.py", "Seeding base data"):
        print_success("Database created!")

        choice = input(f"\n{Colors.CYAN}Add demo data for Thandi's Kitchen? (y/n):{Colors.ENDC} ").lower()
        if choice == 'y':
            if run_command("python3 seed_thandi_data.py", "Adding demo data"):
                print_success("Demo data added!")

        print(f"\n{Colors.GREEN}{'═' * 60}{Colors.ENDC}")
        print(f"{Colors.BOLD}Database ready!{Colors.ENDC}")
        print(f"{Colors.GREEN}{'═' * 60}{Colors.ENDC}\n")
    else:
        print_error("Failed to create database")

def check_ngrok():
    """Check if ngrok is installed"""
    return subprocess.run("which ngrok", shell=True, capture_output=True).returncode == 0

def install_ngrok():
    """Install ngrok"""
    print(f"\n{Colors.BOLD}Installing ngrok...{Colors.ENDC}\n")

    commands = [
        "curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null",
        'echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list',
        "sudo apt update",
        "sudo apt install ngrok -y"
    ]

    for cmd in commands:
        if not run_command(cmd):
            print_error("Installation failed!")
            return False

    print_success("ngrok installed!")
    print(f"\n{Colors.YELLOW}⚠  IMPORTANT:{Colors.ENDC} You need to authenticate ngrok")
    print(f"   1. Sign up at: {Colors.CYAN}https://dashboard.ngrok.com/signup{Colors.ENDC}")
    print(f"   2. Get your auth token from the dashboard")
    print(f"   3. Run: {Colors.CYAN}ngrok config add-authtoken YOUR_TOKEN_HERE{Colors.ENDC}\n")

    return True

def start_sandbox():
    """Start full sandbox environment"""
    print(f"\n{Colors.BOLD}Starting SparzaFI Sandbox...{Colors.ENDC}\n")

    # Check database
    if not check_database():
        print_warning("Database not found!")
        choice = input(f"Create database now? (y/n): ").lower()
        if choice == 'y':
            setup_database()
        else:
            print_error("Cannot start without database")
            return

    # Check ngrok
    has_ngrok = check_ngrok()

    print(f"\n{Colors.GREEN}{'═' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Sandbox Ready!{Colors.ENDC}")
    print(f"{Colors.GREEN}{'═' * 60}{Colors.ENDC}\n")

    print(f"{Colors.BOLD}Next Steps:{Colors.ENDC}\n")

    print(f"  {Colors.CYAN}Terminal 1:{Colors.ENDC} Start Flask")
    print(f"  {Colors.YELLOW}${Colors.ENDC} python3 app.py\n")

    if has_ngrok:
        print(f"  {Colors.CYAN}Terminal 2:{Colors.ENDC} Start ngrok (for public access)")
        print(f"  {Colors.YELLOW}${Colors.ENDC} ngrok http 5000\n")
        print(f"  Then share the ngrok URL with testers!\n")
    else:
        print(f"  {Colors.YELLOW}⚠{Colors.ENDC}  ngrok not installed - only local access available")
        print(f"  Run option 7 to install ngrok for public access\n")

    get_network_urls()
    show_demo_accounts()

    choice = input(f"\n{Colors.CYAN}Start Flask now? (y/n):{Colors.ENDC} ").lower()
    if choice == 'y':
        print(f"\n{Colors.GREEN}Starting Flask...{Colors.ENDC}")
        print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.ENDC}\n")
        time.sleep(1)
        os.system("python3 app.py")

def cloud_deploy_menu():
    """Cloud deployment options"""
    print(f"\n{Colors.BOLD}Cloud Deployment Options:{Colors.ENDC}")
    print(f"{Colors.CYAN}{'─' * 60}{Colors.ENDC}\n")

    print(f"  {Colors.GREEN}1.{Colors.ENDC} Railway.app (Easiest)")
    print(f"     Free $5/month credit, auto-deploy from Git")
    print(f"     {Colors.CYAN}https://railway.app{Colors.ENDC}\n")

    print(f"  {Colors.GREEN}2.{Colors.ENDC} PythonAnywhere (Free Tier)")
    print(f"     Free hosting for Python apps")
    print(f"     {Colors.CYAN}https://www.pythonanywhere.com{Colors.ENDC}\n")

    print(f"  {Colors.GREEN}3.{Colors.ENDC} Render.com (Free)")
    print(f"     Free tier with auto-deploy")
    print(f"     {Colors.CYAN}https://render.com{Colors.ENDC}\n")

    print(f"{Colors.CYAN}{'─' * 60}{Colors.ENDC}")
    print(f"\n{Colors.INFO}See SANDBOX_SETUP.md for detailed deployment guides{Colors.ENDC}\n")

def advanced_menu():
    """Advanced options menu"""
    while True:
        print(f"\n{Colors.BOLD}Advanced Options:{Colors.ENDC}")
        print(f"{Colors.CYAN}{'─' * 60}{Colors.ENDC}\n")

        print(f"  {Colors.GREEN}1.{Colors.ENDC} Backup Database")
        print(f"  {Colors.GREEN}2.{Colors.ENDC} Restore Database")
        print(f"  {Colors.GREEN}3.{Colors.ENDC} Export Demo Accounts to File")
        print(f"  {Colors.GREEN}4.{Colors.ENDC} Run SQL Query")
        print(f"  {Colors.GREEN}5.{Colors.ENDC} Check Dependencies")
        print(f"  {Colors.GREEN}0.{Colors.ENDC} Back to Main Menu\n")

        choice = input(f"{Colors.CYAN}Choose option:{Colors.ENDC} ").strip()

        if choice == '1':
            backup_database()
        elif choice == '2':
            restore_database()
        elif choice == '3':
            export_accounts()
        elif choice == '4':
            run_sql_query()
        elif choice == '5':
            check_dependencies()
        elif choice == '0':
            break
        else:
            print_error("Invalid option")

def backup_database():
    """Backup database"""
    if not check_database():
        print_error("No database to backup!")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"sparzafi_backup_{timestamp}.db"

    try:
        import shutil
        shutil.copy('sparzafi.db', backup_name)
        print_success(f"Database backed up to: {backup_name}")
    except Exception as e:
        print_error(f"Backup failed: {e}")

def restore_database():
    """Restore database from backup"""
    import glob
    backups = glob.glob("sparzafi_backup_*.db")

    if not backups:
        print_error("No backups found!")
        return

    print(f"\n{Colors.BOLD}Available Backups:{Colors.ENDC}\n")
    for i, backup in enumerate(backups, 1):
        size = os.path.getsize(backup) / 1024  # KB
        mtime = datetime.fromtimestamp(os.path.getmtime(backup))
        print(f"  {Colors.GREEN}{i}.{Colors.ENDC} {backup} ({size:.1f} KB, {mtime.strftime('%Y-%m-%d %H:%M')})")

    choice = input(f"\n{Colors.CYAN}Select backup to restore (0 to cancel):{Colors.ENDC} ").strip()

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(backups):
            import shutil
            shutil.copy(backups[idx], 'sparzafi.db')
            print_success(f"Database restored from: {backups[idx]}")
        elif choice == '0':
            print_info("Cancelled")
        else:
            print_error("Invalid selection")
    except:
        print_error("Invalid input")

def export_accounts():
    """Export demo accounts to file"""
    accounts_file = "DEMO_ACCOUNTS.txt"

    with open(accounts_file, 'w') as f:
        f.write("SparzaFI Demo Accounts\n")
        f.write("=" * 60 + "\n\n")
        f.write("Admin:      admin@sparzafi.com / adminpass\n")
        f.write("Seller:     thandi@sparzafi.com / sellerpass\n")
        f.write("Buyer:      buyer1@test.com / buyerpass\n")
        f.write("Deliverer:  sipho.driver@sparzafi.com / driverpass\n\n")
        f.write("Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")

    print_success(f"Accounts exported to: {accounts_file}")

def run_sql_query():
    """Run custom SQL query"""
    if not check_database():
        print_error("No database found!")
        return

    print(f"\n{Colors.YELLOW}Enter SQL query (or 'exit' to cancel):{Colors.ENDC}")
    query = input(f"{Colors.CYAN}SQL>{Colors.ENDC} ").strip()

    if query.lower() == 'exit':
        return

    try:
        conn = sqlite3.connect('sparzafi.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(query)

        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            if results:
                print(f"\n{Colors.GREEN}Results:{Colors.ENDC}\n")
                for row in results:
                    print(dict(row))
            else:
                print_info("No results")
        else:
            conn.commit()
            print_success(f"Query executed ({cursor.rowcount} rows affected)")

        conn.close()

    except Exception as e:
        print_error(f"Query error: {e}")

def check_dependencies():
    """Check if all dependencies are installed"""
    print(f"\n{Colors.BOLD}Checking Dependencies...{Colors.ENDC}\n")

    deps = [
        ("Python 3", "python3 --version"),
        ("Flask", "python3 -c 'import flask; print(flask.__version__)'"),
        ("SQLite3", "sqlite3 --version"),
        ("ngrok", "ngrok version"),
    ]

    for name, cmd in deps:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            print(f"  {Colors.GREEN}✓{Colors.ENDC} {name}: {version}")
        else:
            print(f"  {Colors.RED}✗{Colors.ENDC} {name}: Not found")

    print()

def main():
    """Main CLI loop"""
    try:
        while True:
            print_banner()
            print_menu()

            choice = input(f"{Colors.CYAN}Choose an option:{Colors.ENDC} ").strip()

            if choice == '1':
                start_sandbox()
            elif choice == '2':
                setup_database()
            elif choice == '3':
                setup_database()
            elif choice == '4':
                get_database_stats()
            elif choice == '5':
                show_demo_accounts()
            elif choice == '6':
                get_network_urls()
            elif choice == '7':
                install_ngrok()
            elif choice == '8':
                cloud_deploy_menu()
            elif choice == '9':
                advanced_menu()
            elif choice == '0':
                print(f"\n{Colors.CYAN}Thanks for using SparzaFI Sandbox!{Colors.ENDC}\n")
                break
            else:
                print_error("Invalid option. Please try again.")

            if choice != '0':
                input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")

            # Clear screen
            os.system('clear' if os.name != 'nt' else 'cls')

    except KeyboardInterrupt:
        print(f"\n\n{Colors.CYAN}Goodbye!{Colors.ENDC}\n")
        sys.exit(0)

if __name__ == '__main__':
    # Check if running from correct directory
    if not os.path.exists('app.py'):
        print_error("Please run this script from the SparzaFI directory!")
        sys.exit(1)

    main()
