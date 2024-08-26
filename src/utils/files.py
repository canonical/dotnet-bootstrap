import glob
import re
import shutil


def replace_in_file(input_file: str, pattern: str, replacement: str) -> str:
    try:
        with open(input_file, 'r') as file:
            content = file.read()
        
        # Perform the replacement
        updated_content = re.sub(pattern, replacement, content)
        
        print(f"Replaced '{pattern}' with '{replacement}'")
        return updated_content
    
    except FileNotFoundError:
        print(f"File '{input_file}' not found.")
    except IOError as e:
        print(f"An error occurred: {e}")

def copy_files(pattern, destination) -> None:
    print(f"Using pattern '{pattern}'")
    for file_path in glob.glob(pattern):
        print(f"Copying {file_path} to {destination}")
        shutil.copy(file_path, destination)
