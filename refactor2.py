import os
import re

FRONTEND_DIR = "d:/Personal Project Freelance/Project 1/vyrenzo-proj1-fincore/frontend"

RULES = [
    # Leftovers from slate 700 / 600 / 500 / 400
    (r'bg-slate-[67]00', 'bg-neutral-border'),
    (r'hover:bg-slate-[67]00', 'hover:bg-neutral-border'),
    (r'border-slate-[67]00', 'border-neutral-border'),
    
    (r'text-slate-[67]00', 'text-t-muted'),
    (r'bg-slate-[45]00/10', 'bg-neutral-row'),
    (r'border-slate-[45]00/20', 'border-neutral-border'),
    (r'border-slate-[45]00/50', 'border-neutral-border'),
    (r'border-slate-[45]00', 'border-neutral-border'),
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
    print(f"Updated {modified_count} additional files.")

if __name__ == "__main__":
    main()
