import re
import subprocess


def get_xml_tag_content(xml_file_path: str, tag_name: str) -> str | None:
    try:
        # Grep for lines containing the tag
        grep_command = ['grep', f'<{tag_name}>', xml_file_path]
        result = subprocess.run(grep_command, capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        
        # Extract the value between the tags
        tag_pattern = re.compile(rf'<{tag_name}>(.*?)</{tag_name}>', re.DOTALL)
        
        for line in lines:
            match = tag_pattern.search(line)
            if match:
                return match.group(1)
        
        # Return None if no tag found
        return None

    except subprocess.CalledProcessError:
        print("An error occurred while running grep.")
        return None
