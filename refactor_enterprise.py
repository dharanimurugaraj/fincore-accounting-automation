import os
import re

FRONTEND_DIR = "d:/Personal Project Freelance/Project 1/vyrenzo-proj1-fincore/frontend"

# We are going to aggressively prune any dark mode leftovers or hardcoded hex colors that aren't verified Lite.
RULES = [
    # Backgrounds
    (r'bg-\[#0F172A\]', 'bg-neutral-app'),
    (r'bg-\[#020617\]', 'bg-neutral-app'),
    (r'bg-slate-900', 'bg-neutral-app'),
    (r'bg-slate-950', 'bg-neutral-app'),
    (r'bg-slate-800', 'bg-neutral-card'),
    (r'bg-slate-700', 'bg-neutral-row'),
    
    # Text
    (r'text-white', 'text-t-heading'),
    (r'text-slate-100', 'text-t-heading'),
    (r'text-slate-200', 'text-t-body'),
    (r'text-slate-300', 'text-t-body'),
    (r'text-slate-400', 'text-t-muted'),
    (r'text-slate-500', 'text-t-muted'),
    
    # Borders
    (r'border-slate-800', 'border-neutral-border'),
    (r'border-slate-700', 'border-neutral-border'),
    (r'border-white/10', 'border-neutral-border'),
    (r'border-white/5', 'border-neutral-border/50'),

    # Fonts - Clean up any weird fonts
    (r'font-black', 'font-bold'), # Tone down "black" to standard "bold" for professional look
    (r'tracking-\[0.2em\]', 'tracking-normal'),
    (r'tracking-\[0.3em\]', 'tracking-normal'),
]

# We should skip files we just manually crafted to ensure we don't break our intentional designs
EXCLUDE_FILES = ['login/page.tsx', 'globals.css', 'TopBar.tsx', 'ProtectedGuard.tsx', 'layout.tsx']

def main():
    modified_count = 0
    for root, dirs, files in os.walk(FRONTEND_DIR):
        if 'node_modules' in root or '.next' in root:
            continue
        for file in files:
            if file.endswith(('.tsx', '.ts')):
                # Simple check for exclusion
                if any(ex in os.path.join(root, file).replace('\\', '/') for ex in EXCLUDE_FILES):
                    continue
                    
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
    print(f"Final Enterprise Pass: Updated {modified_count} files for Lite professional look.")

if __name__ == "__main__":
    main()
