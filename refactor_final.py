import os
import re

FRONTEND_DIR = "d:/Personal Project Freelance/Project 1/vyrenzo-proj1-fincore/frontend"

RULES = [
    # Global Cleanup
    (r'text-white', 'text-t-heading'),
    (r'text-slate-950', 'text-white'), # Buttons often use 950 for text
    (r'bg-slate-950', 'bg-neutral-card'),
    (r'bg-slate-900', 'bg-neutral-app'),
    (r'divide-slate-800/50', 'divide-neutral-border'),
    (r'divide-slate-800', 'divide-neutral-border'),
    (r'border-slate-800/50', 'border-neutral-border/50'),
    (r'border-slate-800', 'border-neutral-border'),
    
    # Specific color mappings
    (r'text-rose-500', 'text-status-critical'),
    (r'bg-rose-500', 'bg-status-critical'),
    (r'text-indigo-400', 'text-ai-violet'),
    (r'text-indigo-500', 'text-ai-violet'),
    (r'text-indigo-600', 'text-ai-violet'),
    (r'bg-indigo-600', 'bg-ai-violet'),
    (r'bg-indigo-500', 'bg-ai-violet'),
    (r'hover:bg-indigo-700', 'hover:bg-ai-violet/90'),
    (r'hover:bg-indigo-600', 'hover:bg-ai-violet/90'),
    (r'focus:ring-indigo-500/50', 'focus:ring-primary/50'),
    
    # Cyan mappings
    (r'text-cyan-400', 'text-primary'),
    (r'text-cyan-500', 'text-primary'),
    (r'bg-cyan-500', 'bg-primary'),
    (r'bg-cyan-600', 'bg-primary-hover'),
    (r'hover:bg-cyan-600', 'hover:bg-primary-hover'),
    (r'focus:ring-cyan-500/50', 'focus:ring-primary/50'),
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
    print(f"Final cleanup in {modified_count} files.")

if __name__ == "__main__":
    main()
