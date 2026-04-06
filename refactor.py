import os
import re

FRONTEND_DIR = "d:/Personal Project Freelance/Project 1/vyrenzo-proj1-fincore/frontend"

RULES = [
    # Backgrounds
    (r'bg-slate-950', 'bg-neutral-card'),
    (r'bg-slate-900', 'bg-neutral-app'),
    (r'bg-slate-800', 'bg-neutral-row'),
    
    # Borders
    (r'border-slate-[78]00', 'border-neutral-border'),
    (r'border-slate-600', 'border-neutral-border-light'),
    
    # Texts
    (r'text-slate-100', 'text-t-heading'),
    (r'text-slate-200', 'text-t-heading'),
    (r'text-slate-300', 'text-t-body'),
    (r'text-slate-400', 'text-t-muted'),
    (r'text-slate-500', 'text-t-muted'),
    (r'text-slate-600', 'text-t-muted'),
    
    # Hovers
    (r'hover:bg-slate-800', 'hover:bg-neutral-row'),
    (r'hover:bg-slate-900', 'hover:bg-neutral-card'),
    (r'hover:text-slate-200', 'hover:text-t-heading'),
    (r'hover:text-slate-300', 'hover:text-t-body'),
    
    # Primary (Brand Blue)
    (r'bg-cyan-500', 'bg-primary'),
    (r'bg-cyan-400', 'bg-primary-hover'),
    (r'text-cyan-400', 'text-primary'),
    (r'text-cyan-500', 'text-primary'),
    (r'border-cyan-500', 'border-primary'),
    (r'hover:bg-cyan-400', 'hover:bg-primary-hover'),
    
    # Specific backgrounds with opacity
    (r'bg-slate-900/50', 'bg-neutral-card'),
    (r'bg-slate-950/50', 'bg-neutral-row'),
    (r'bg-slate-900/40', 'bg-neutral-card'),
    (r'bg-slate-900/30', 'bg-neutral-card'),
    (r'bg-slate-900/20', 'bg-neutral-card'),
    (r'bg-slate-800/50', 'bg-neutral-row'),
    (r'bg-slate-800/30', 'bg-neutral-row'),
    (r'bg-slate-800/20', 'bg-neutral-row'),
    
    # Shadows
    (r'shadow-cyan-500/10', 'shadow-sm shadow-primary/10'),
    (r'shadow-cyan-500/5', 'shadow-sm shadow-primary/5'),
    
    # AI / Indigo highlights
    (r'text-indigo-400', 'text-ai-violet'),
    (r'text-indigo-500', 'text-ai-violet'),
    (r'bg-indigo-500', 'bg-ai-violet'),
    (r'bg-indigo-400', 'bg-ai-violet'),
    (r'bg-indigo-500/10', 'bg-ai-violet-light'),
    
    # Status states
    (r'text-red-400', 'text-status-critical'),
    (r'text-red-500', 'text-status-critical'),
    (r'bg-red-400/10', 'bg-status-critical-bg'),
    (r'border-red-400/20', 'border-status-critical/20'),
    
    (r'text-amber-400', 'text-status-medium'),
    (r'text-amber-500', 'text-status-medium'),
    (r'bg-amber-400/10', 'bg-status-medium-bg'),
    (r'bg-amber-500/10', 'bg-status-medium-bg'),
    (r'border-amber-400/20', 'border-status-medium/20'),
    (r'border-amber-500/30', 'border-status-medium/30'),
    
    (r'text-emerald-400', 'text-status-success'),
    (r'text-emerald-500', 'text-status-success'),
    (r'bg-emerald-400/10', 'bg-status-success-bg'),
    (r'bg-emerald-500/10', 'bg-status-success-bg'),
    (r'border-emerald-400/20', 'border-status-success/20'),
    (r'border-emerald-500/30', 'border-status-success/30'),
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
    print(f"Updated {modified_count} files.")

if __name__ == "__main__":
    main()
