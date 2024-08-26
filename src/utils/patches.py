import os
import subprocess
import tempfile


def apply_patch(patch_content: str, target_file: str):
    # Save the patch content to a temporary file
    patch_file = tempfile.mktemp(".patch")
    with open(patch_file, 'w') as f:
        f.write(patch_content)
    
    try:
        # Apply the patch using the `patch` command
        result = subprocess.run(['patch', '--verbose', target_file, '-i', patch_file],
                                check=True, text=True, capture_output=True)
        print("Patch applied successfully.")
    except subprocess.CalledProcessError as e:
        print("Error applying patch")
        print(e.stdout) if len(str(e.stdout)) > 0 else None
        print(e.stderr) if len(str(e.stderr)) > 0 else None
        exit(-1)
    finally:
        # Clean up the temporary patch file
        os.remove(patch_file)

def extract_file_path_from_patch(patch_content: str) -> str:
    # Split the patch content into lines
    lines = patch_content.splitlines()
    
    for line in lines:
        if line.startswith('+++ '):
            return line[4:].strip().split('\t')[0]
