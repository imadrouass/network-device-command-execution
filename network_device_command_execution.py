from netmiko import ConnectHandler
from netmiko import NetMikoTimeoutException, NetMikoAuthenticationException
from paramiko.ssh_exception import SSHException
from concurrent.futures import ThreadPoolExecutor
import time
import sys
import os
import re
from colorama import init, Fore
from getpass import getpass
# Adds a single line that imports idna encoding which prevents Lookup Error on unicode hostname resolution
import encodings.idna

# Record the start time
start = time.time()

# Initialize colorama with autoreset enabled
init(autoreset=True)

CurrentDateTime = time.strftime("%Y-%m-%d %H-%M-%S")
print(Fore.LIGHTBLUE_EX + f"Current date and time : {CurrentDateTime}")
print(20 * '#', 'Event Log', +20 * '#')


def get_credentials():
    # Ask for username and password
    username = input("Enter your username: ")
    password = getpass("Enter your password: ")
    return username, password


def check_files_exist():
    # List of files to check
    files = ["IPAddressList.txt", "commands.txt"]

    # Iterate over each file and check if it exists
    for file_name in files:
        if not os.path.isfile(file_name):
            print(f"File '{file_name}' not found.")
            return False
    return True


def execute_commands(ip_address, commands, username, password):
    try:
        # Define device parameters
        device = {"device_type": "nokia_sros", "host": ip_address, "username": username, "password": password,
                  "timeout": 2, }

        # Establish SSH connection to the device
        ssh_conn = ConnectHandler(**device, global_delay_factor=0.1)

        # Find the prompt A:R1# or *A:R1#
        prompt_hostname = ssh_conn.find_prompt()[0:-1]
        # Get hostname from find_prompt
        host_name = re.split(":", prompt_hostname)[1]

        # Create a file name for the output based on the Hostname & IP address & DateTime
        log_time = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Outputs/{host_name}_{ip_address}_{log_time}.txt"

        # Iterate over each command and execute it and save the result to the file
        with open(filename, "w") as file:
            for command in commands:
                output = ssh_conn.send_command(command, delay_factor=0.1)
                file.write(f"{prompt_hostname}# {command}\n")
                file.write(output)
                file.write("\n")

        # Disconnect from the device
        ssh_conn.disconnect()

        print(Fore.LIGHTGREEN_EX + f"[SUCCESS] {host_name} : Output saved ==> {filename}")

    # Handle timeout errors specifically
    except NetMikoTimeoutException:
        sys.stdout.flush()
        error_msg = f" Host unreachable ==> {ip_address}"
        print(Fore.LIGHTRED_EX + "[ERROR]" + error_msg )
        # Log the error to a file with timestamp
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        with open("LOGs/error_log.txt", "a") as error_file:
            error_file.write(f"{timestamp}: {error_msg}\n")
    # Handle authentication errors specifically
    except NetMikoAuthenticationException:
        error_msg = f" Authentication failure->Login using : {username} ==> {ip_address}"
        sys.stdout.flush()  # Flush the standard output
        print(Fore.LIGHTRED_EX + "[ERROR]" + error_msg)
        # Log the error to a file with timestamp
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        with open("LOGs/error_log.txt", "a") as error_file:
            error_file.write(f"{timestamp}: {error_msg}\n")
    # Handle SSH errors specifically
    except SSHException:
        error_msg = f" SSH Issue. Are you sure SSH is enabled? ==> {ip_address}"
        sys.stdout.flush()
        print(Fore.LIGHTRED_EX + "[ERROR]" + error_msg)
        # Log the error to a file with timestamp
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        with open("LOGs/error_log.txt", "a") as error_file:
            error_file.write(f"{timestamp}: {error_msg}\n")


def main():
    # Check the 'Outputs' and 'LOGs' folder availability if not will be created
    if not os.path.exists("Outputs/"):
        os.mkdir("Outputs/", 0o777)
    if not os.path.exists("LOGs/"):
        os.mkdir("LOGs/", 0o777)

    # Check if the required files 'ip_addresses.txt' and 'commands.txt' exist
    if not check_files_exist():
        print(Fore.LIGHTRED_EX + "[SUCCESS] Please make sure 'ip_addresses.txt' and 'commands.txt' are available.\n\n")
        return

    # Get username and password from the user
    username, password = get_credentials()


    # If the files exist, continue with the main execution
    print(Fore.CYAN + "[INFO] All required files 'ip_addresses.txt' and 'commands.txt' are available.")

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
    with ThreadPoolExecutor(max_workers=8) as executor:
        # Submit each device connection task to the executor
        # executor.map(execute_commands, ip_addresses, [commands] * len(ip_addresses))
        executor.map(execute_commands, ip_addresses, [commands] * len(ip_addresses), [username] * len(ip_addresses),
                     [password] * len(ip_addresses))


# Call the main function
if __name__ == "__main__":
    main()

# Record the end time
end = time.time()
total = int(end - start)
print(Fore.CYAN + f"[INFO] Elapsed Time: {total} Sec\n")

# Function in Python is used to exit the Python interpreter.
input(Fore.MAGENTA + "Press enter to exit >")
sys.exit()
