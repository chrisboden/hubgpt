import re
import os

def strip_env_keys(input_path, output_path):
    """
    Generate a copy of the .env file with keys stripped out.
    Args:
    input_path (str): Path to the source .env file
    output_path (str): Path to the output .env file
    """
    try:
        # Read the original .env file
        with open(input_path, 'r') as input_file:
            env_lines = input_file.readlines()
        
        # Process lines to strip out key values
        stripped_lines = []
        for line in env_lines:
            # Remove whitespace
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                stripped_lines.append(line + '\n')
                continue
            
            # Split line into key and value
            match = re.match(r'^([^=]+)=', line)
            if match:
                # Keep the key, but set value to empty string
                key = match.group(1)
                stripped_lines.append(f'{key}=\n')
            else:
                # If line doesn't match expected format, keep as is
                stripped_lines.append(line + '\n')
        
        # Write the stripped lines to the output file
        with open(output_path, 'w') as output_file:
            output_file.writelines(stripped_lines)
        
        print(f"Generated stripped env file at {output_path}")
    
    except FileNotFoundError:
        print(f"Error: Input file {input_path} not found.")
    except PermissionError:
        print(f"Error: Permission denied when writing to {output_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def main():
    # Define paths
    current_file = os.path.abspath(__file__)
    root_dir = os.path.dirname(os.path.dirname(current_file))
    input_env_path = os.path.join(root_dir, '.env')
    output_env_path = os.path.join(root_dir, '.env_copy')
    
    # Generate stripped env file
    strip_env_keys(input_env_path, output_env_path)


if __name__ == '__main__':
    main()
