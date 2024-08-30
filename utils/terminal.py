import paramiko
import time
# Define the VM's SSH details
password = None  # Use None if using a private key

def gdb_on_vm(prog, hostname="localhost", port=2024, username="root"):
    # Create an SSH client instance
    ssh_client = paramiko.SSHClient()

    # Automatically add the host key if it's missing
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the VM using SSH
        ssh_client.connect(hostname, port=port, username=username, password=password)

        print(f"Successfully connected to {hostname}")

        # Open an interactive shell session
        ssh_session = ssh_client.invoke_shell()

        ssh_session.send(prog+"\n")
        time.sleep(1)  # Wait for command execution

        # Read the command output
        if ssh_session.recv_ready():
            output = ssh_session.recv(1024).decode()
            print(output, end="\n")
        # Example: Keep the session open for further commands
        while True:
            #command = input("Enter a command to execute ('exit' to quit): ")
            command = input()
            if command.strip().lower() == 'quit':
                break

            ssh_session.send(command + "\n")
            #time.sleep(1)  # Wait for the command execution

            # Read the command output
            if ssh_session.recv_ready():
                output = ssh_session.recv(1024).decode()
                print(output, end="")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the SSH connection
        ssh_client.close()
        print("gdb session closed.")

def login_vm(hostname="localhost", port=2024, username="root"):
    # Create an SSH client instance
    ssh_client = paramiko.SSHClient()

    # Automatically add the host key if it's missing
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the VM using SSH
        ssh_client.connect(hostname, port=port, username=username, password=password)

        print(f"Successfully connected to {hostname}")

        # Open an interactive shell session
        ssh_session = ssh_client.invoke_shell()

        ssh_session.send("clear\n")
        time.sleep(1)  # Wait for command execution

        # Read the command output
        if ssh_session.recv_ready():
            output = ssh_session.recv(1024).decode()
            print(output, end="")
        # Example: Keep the session open for further commands
        while True:
            #command = input("Enter a command to execute ('exit' to quit): ")
            command = input()
            if command.strip().lower() == 'exit':
                break

            ssh_session.send(command + "\n")
            time.sleep(1)  # Wait for the command execution

            # Read the command output
            if ssh_session.recv_ready():
                output = ssh_session.recv(1024).decode()
                print(output, end="")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the SSH connection
        ssh_client.close()
        print("SSH session closed.")
