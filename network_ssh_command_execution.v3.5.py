import encodings.idna
import os
import re
import sys
import time
import logging
import ipaddress
from colorama import init, Fore, Style
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from getpass import getpass
from netmiko import (
    ConnectHandler,
    NetMikoTimeoutException,
    NetMikoAuthenticationException,
)
from paramiko.ssh_exception import SSHException
from tqdm import tqdm
import subprocess

# Initialize colorama with autoreset enabled
init(autoreset=True)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def ensure_file_exists(filename):
    """Ensure the given file exists, creating it if not."""
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            pass  # Create an empty file


def open_file(filename):
    """Open a file based on the operating system."""
    try:
        if sys.platform == "win32":
            os.startfile(filename)
        elif sys.platform == "darwin":
            subprocess.call(("open", filename))
        else:
            subprocess.call(("xdg-open", filename))
    except Exception as e:
        print(f"Error opening file {filename}: {e}")


def main_menu():
    """Display the main menu and handle user choices."""
    while True:
        clear_screen()
        print("=" * 50)
        print(f"{Fore.CYAN}Welcome to SSH Tool {Style.RESET_ALL}")
        print("=" * 50)
        print("i. Update the list of IPs")
        print("c. Update the list of commands")
        print("r. Run SSH script")
        print("e. Exit")
        print("-" * 50)

        choice = input(f"{Fore.YELLOW}Enter your choice: {Style.RESET_ALL}")
        if choice.lower() == "i":
            clear_screen()
            ensure_file_exists("IPAddressList.txt")
            open_file("IPAddressList.txt")
        elif choice.lower() == "c":
            clear_screen()
            ensure_file_exists("commands.txt")
            open_file("commands.txt")
        elif choice.lower() == "r":
            clear_screen()
            main()
        elif choice.lower() == "e":
            print(Fore.YELLOW + "Exiting the program. Goodbye!" + Style.RESET_ALL)
            time.sleep(2)
            sys.exit(0)
        else:
            print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")
            input(Fore.MAGENTA + "Press Enter to continue..." + Style.RESET_ALL)


def get_credentials():
    """Prompt user for SSH credentials."""
    username = input("Enter your username: ")
    password = getpass("Enter your password: ")
    return username, password


def check_files_exist():
    """Check if required files exist."""
    files = ["IPAddressList.txt", "commands.txt"]
    for file_name in files:
        if not os.path.isfile(file_name):
            print(f"File '{file_name}' not found.")
            return False
    return True


def is_valid_ip(ip):
    """Check if the given string is a valid IP address."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def execute_commands(ip_address, commands, username, password):
    """Execute commands on a given device via SSH."""
    if not is_valid_ip(ip_address):
        error_msg = f"Invalid IP address format: {ip_address}"
        tqdm.write(Fore.LIGHTRED_EX + f"\r[ERROR] {error_msg}")
        log_error(error_msg)
        return

    try:
        device = {
            "device_type": "nokia_sros",
            "host": ip_address,
            "username": username,
            "password": password,
            "read_timeout_override": 90,
        }
        ssh_conn = ConnectHandler(**device, global_delay_factor=2)
        prompt_hostname = ssh_conn.find_prompt()[0:-1]
        host_name = re.split(":", prompt_hostname)

        if len(host_name) > 1:
            host_name = host_name[1]
        else:
            host_name = ip_address  # Fallback to IP address if the prompt does not contain the expected format

        log_time = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Outputs/{host_name}_{ip_address}_{log_time}.txt"

        with open(filename, "w") as file:
            for command in tqdm(
                    commands,
                    desc=Fore.LIGHTYELLOW_EX + f"Executing on {ip_address}",
                    unit="Cmd",
                    file=sys.stdout,
                    ncols=100,
                    leave=False,
            ):
                output = ssh_conn.send_command(command, delay_factor=1)
                file.write(f"{prompt_hostname}# {command}\n{output}\n")

        ssh_conn.disconnect()
        tqdm.write(
            Fore.LIGHTGREEN_EX
            + f"\r[SUCCESS] {host_name} : Output saved ==> {filename}"
        )

    except NetMikoTimeoutException:
        error_msg = f"Host unreachable ==> {ip_address}"
        tqdm.write(Fore.LIGHTRED_EX + "\r[ERROR]" + error_msg)
        log_error(error_msg)
    except NetMikoAuthenticationException:
        error_msg = f"Authentication failure->Login using : {username} ==> {ip_address}"
        tqdm.write(Fore.LIGHTRED_EX + "\r[ERROR]" + error_msg)
        log_error(error_msg)
    except SSHException:
        error_msg = f" SSH Issue. Are you sure SSH is enabled? ==> {ip_address}"
        tqdm.write(Fore.LIGHTRED_EX + "\r[ERROR]" + error_msg)
        log_error(error_msg)


def log_error(error_msg):
    """Log errors to a file with timestamp, ensuring latest logs appear at the top."""
    logging.error(error_msg)

    # Read existing logs
    if os.path.exists("LOGs/error_log.txt"):
        with open("LOGs/error_log.txt", "r") as file:
            existing_logs = file.readlines()
    else:
        existing_logs = []

    # Prepend the new log entry
    with open("LOGs/error_log.txt", "w") as file:
        timestamp = time.strftime("%Y-%m-%d %H-%M-%S")
        file.write(f"{timestamp}: {error_msg}\n")  # Write the new entry first
        file.writelines(existing_logs)  # Then write the existing logs


def main():
    """Main function to execute the SSH commands."""
    start_time = datetime.now()
    current_date_time = time.strftime("%Y-%m-%d %H-%M-%S")
    print(Fore.LIGHTBLUE_EX + f"Current date and time : {current_date_time}")
    print(20 * "#", "Event Log", 20 * "#")

    os.makedirs("Outputs", exist_ok=True)
    os.makedirs("LOGs", exist_ok=True)
    # Set up logging
    logging.basicConfig(
        filename="LOGs/error_log.txt",
        level=logging.ERROR,
        format="%(asctime)s: %(message)s",
    )

    if not check_files_exist():
        print(
            Fore.LIGHTRED_EX
            + "\r[ERROR] Please make sure 'IPAddressList.txt' and 'commands.txt' are available.\n\n"
        )
        return

    username, password = get_credentials()

    print(
        Fore.CYAN
        + "[INFO] All required files 'IPAddressList.txt' and 'commands.txt' are available."
    )

    with open("IPAddressList.txt", "r") as file:
        ip_addresses = [ip.strip() for ip in file.readlines()]

    with open("commands.txt", "r") as file:
        commands = [cmd.strip() for cmd in file.readlines()]

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for ip_address in ip_addresses:
            futures.append(
                executor.submit(
                    execute_commands, ip_address, commands, username, password
                )
            )

        for future in futures:
            future.result()

    end_time = datetime.now()
    print(Fore.CYAN + f"[INFO] Elapsed Time: {end_time - start_time} Min\n")

    want_save = input(
        f"\n{Fore.YELLOW}Do you want to open the Outputs folder? (y/n): "
        + Style.RESET_ALL
    )
    if want_save.lower() == "y":
        open_file("Outputs")

    input(Fore.MAGENTA + "Press Enter to continue..." + Style.RESET_ALL)
    main_menu()


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Program interrupted by user. Exiting...{Style.RESET_ALL}")
        time.sleep(2)
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}An unexpected error occurred: {e}{Style.RESET_ALL}")
        log_error(f"Unexpected error: {e}")
        time.sleep(5)
        sys.exit(1)
    except BaseException as be:
        # This block will catch `KeyboardInterrupt` if it hasn't been caught earlier
        print(f"\n{Fore.YELLOW}Caught BaseException (likely KeyboardInterrupt). Exiting...{Style.RESET_ALL}")
        time.sleep(2)
        sys.exit(0)
