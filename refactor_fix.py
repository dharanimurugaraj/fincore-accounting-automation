import os
import re

FRONTEND_DIR = "d:/Personal Project Freelance/Project 1/vyrenzo-proj1-fincore/frontend"

# We accidentally flipped app and card backgrounds in the previous script.
# Let's fix them. We will temporarily swap them to a placeholder to avoid overlapping replacments.
RULES = [
    (r'bg-neutral-app', 'bg-TEMP-CARD'),
    (r'bg-neutral-card', 'bg-TEMP-APP'),
    (r'bg-TEMP-CARD', 'bg-neutral-card'),
    (r'bg-TEMP-APP', 'bg-neutral-app'),
]

def main():
    modified_count = 0
    for root, dirs, files in os.walk(FRONTEND_DIR):
        if 'node_modules' in root or '.next' in root:
            continue
        for file in files:
            if file.endswith(('.tsx', '.ts')):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = content
                for pattern, replacement in RULES:
                    new_content = re.sub(pattern, replacement, new_content)
                
                if content != new_content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    modified_count += 1
    print(f"Flipped app and card backgrounds in {modified_count} files.")

if __name__ == "__main__":
    main()
