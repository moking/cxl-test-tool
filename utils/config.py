import os

import os
import re

# Function to resolve nested environment variables
def resolve_var(value, env_dict):
    # This pattern matches ${VAR_NAME}
    pattern = re.compile(r'\$\{([^}]+)\}')

    # Use a loop to resolve all nested variables
    while True:
        match = pattern.search(value)
        if not match:
            break
        # Extract the variable name from ${VAR_NAME}
        var_name = match.group(1)

        # Replace ${VAR_NAME} with its value from env_dict
        var_value = env_dict.get(var_name, '')
        var_value = var_value.strip("\"").strip("\'")
        value = value.replace(f'${{{var_name}}}', var_value)

    return value

# Function to parse .env file with nested definitions
def parse_config(conf):
    env_dict = {}

    with open(conf) as file:
        for line in file:
            # Strip the line and ignore comments or empty lines
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Split the line into key and value
            key, value = line.split('=', 1)

            # Resolve nested variables for this line
            value = resolve_var(value, env_dict)
            # Save the resolved value in the dictionary
            env_dict[key] = value
            # Export the variable to the environment
            os.environ[key] = value

    return env_dict
