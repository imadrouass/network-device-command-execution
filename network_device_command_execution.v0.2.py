from netmiko import ConnectHandler
from netmiko import NetMikoTimeoutException, NetMikoAuthenticationException
from paramiko.ssh_exception import SSHException
from concurrent.futures import ThreadPoolExecutor
import time
import sys, os, re
from colorama import init, Fore, Style
from getpass import getpass
from datetime import datetime
# Adds a single line that imports idna encoding which prevents Lookup Error on unicode hostname resolution
import encodings.idna

# Initialize colorama with autoreset enabled
init(autoreset=True)


# Ensure the given file exists, create if not
def ensure_file_exists(filename):
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            pass  # Create an empty file


# Display the main menu
def main_menu():
    while True:
        print('\n' + ('=' * 50))
        print(f"{Fore.MAGENTA}Welcome to SSH Tool {Style.RESET_ALL}")
        print('-' * 50)
        print("i. Update the list of IPs")
        print("c. Update the list of commands")
        print("r. Run SSH script")
        print("e. Exit")
        print('=' * 50)

        choice = input(f"{Fore.MAGENTA}Enter your choice: {Style.RESET_ALL}")
        if choice.lower() == "i":
            ensure_file_exists('IPAddressList.txt')
            os.startfile('IPAddressList.txt')
        elif choice.lower() == "c":
            ensure_file_exists('commands.txt')
            os.startfile('commands.txt')
        elif choice.lower() == "r":
            main()
        elif choice.lower() == "e":
            print(f"{Fore.MAGENTA}Exiting...{Style.RESET_ALL}")
            time.sleep(3)
            break
        else:
            print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")


# Prompt user for SSH credentials
def get_credentials():
    username = input("Enter your username: ")
    password = getpass("Enter your password: ")
    return username, password


# Check if required files exist
def check_files_exist():
    files = ["IPAddressList.txt", "commands.txt"]
    # Iterate over each file and check if it exists						   
    for file_name in files:
        if not os.path.isfile(file_name):
            print(f"File '{file_name}' not found.")
            return False
    return True


# Execute commands on a given device
def execute_commands(ip_address, commands, username, password):
    try:
        # Define device parameters
        device = {
            "device_type": "nokia_sros",
            "host": ip_address,
            "username": username,
            "password": password,
            "read_timeout_override": 20,
        }
        # Establish SSH connection to the device
        ssh_conn = ConnectHandler(**device, global_delay_factor=2)
        # Find the prompt and hostname (A:R1# or *A:R1#)
        prompt_hostname = ssh_conn.find_prompt()[0:-1]
        # Get hostname from find_prompt
        host_name = re.split(":", prompt_hostname)[1]
        # Create a file name for the output based on the Hostname & IP address & DateTime
        log_time = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Outputs/{host_name}_{ip_address}_{log_time}.txt"

        # Iterate over each command, execute it, and save the result to the file
        with open(filename, "w") as file:
            for command in commands:
                output = ssh_conn.send_command(command, delay_factor=2)
                file.write(f"{prompt_hostname}# {command}\n")
                file.write(output)
                file.write("\n")

        # Disconnect from the device
        ssh_conn.disconnect()
        print(Fore.LIGHTGREEN_EX + f"[SUCCESS] {host_name} : Output saved ==> {filename}")

    # Handle timeout errors specifically
    except NetMikoTimeoutException:
        error_msg = f" Host unreachable ==> {ip_address}"
        print(Fore.LIGHTRED_EX + "[ERROR]" + error_msg)
        log_error(error_msg)
    # Handle authentication errors specifically
    except NetMikoAuthenticationException:
        error_msg = f" Authentication failure->Login using : {username} ==> {ip_address}"
        print(Fore.LIGHTRED_EX + "[ERROR]" + error_msg)
        log_error(error_msg)
    # Handle SSH errors specifically
    except SSHException:
        error_msg = f" SSH Issue. Are you sure SSH is enabled? ==> {ip_address}"
        print(Fore.LIGHTRED_EX + "[ERROR]" + error_msg)
        log_error(error_msg)


# Log errors to a file with timestamp
def log_error(error_msg):
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    with open("LOGs/error_log.txt", "a") as error_file:
        error_file.write(f"{timestamp}: {error_msg}\n")


# Main function to execute the SSH commands
def main():
    # Record the start time
    start_time = datetime.now()
    CurrentDateTime = time.strftime("%Y-%m-%d %H-%M-%S")
    print(Fore.LIGHTBLUE_EX + f"Current date and time : {CurrentDateTime}")
    print(20 * '#', 'Event Log', 20 * '#')

    # Check the 'Outputs' and 'LOGs' folder availability, create if not exist
    if not os.path.exists("Outputs/"):
        os.mkdir("Outputs/", 0o777)
    if not os.path.exists("LOGs/"):
        os.mkdir("LOGs/", 0o777)

    # Check if the required files 'IPAddressList.txt' and 'commands.txt' exist
    if not check_files_exist():
        print(Fore.LIGHTRED_EX + "[ERROR] Please make sure 'IPAddressList.txt' and 'commands.txt' are available.\n\n")
        return

    # Get username and password from the user
    username, password = get_credentials()

    # Inform the user that all required files are available
    print(Fore.CYAN + "[INFO] All required files 'IPAddressList.txt' and 'commands.txt' are available.")

    # Read IP addresses from the text file
    with open("IPAddressList.txt", "r") as file:
        # Read all lines from a file and return them as a list
        ip_addresses = file.readlines()
        # Strips leading and trailing whitespace and newline characters
        ip_addresses = [ip.strip() for ip in ip_addresses]

    # Read commands from the text file
    with open("commands.txt", "r") as file:
        commands = file.readlines()
        commands = [cmd.strip() for cmd in commands]

    # Create a ThreadPoolExecutor with maximum workers equal to 8
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit each device connection task to the executor
        executor.map(execute_commands, ip_addresses, [commands] * len(ip_addresses), [username] * len(ip_addresses),
                     [password] * len(ip_addresses))

    # Record the end time
    end_time = datetime.now()
    print(Fore.CYAN + f"[INFO] Elapsed Time: {end_time - start_time} Min\n")

    # Prompt user to open the Outputs folder
    want_save = input(f'\n{Fore.YELLOW}Do you want to open the Outputs folder? (y/n):')
    if want_save.lower() == "y":
        os.startfile(os.path.realpath("Outputs"))

    # Exit the script
    input(Fore.MAGENTA + "Press enter to exit >")
    time.sleep(3)
    sys.exit()


# Call the main menu function when the script is executed
if __name__ == "__main__":
    main_menu()
