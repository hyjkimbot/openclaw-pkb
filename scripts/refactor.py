#!/usr/bin/env python3
import os
import sys
import argparse
import re
import shutil

def get_vault_root():
    # Assumes script is in /scripts/ and vault root is one level up
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)

def find_md_files(vault_root):
    for root, dirs, files in os.walk(vault_root):
        if '.git' in dirs:
            dirs.remove('.git')  # Skip .git
        for file in files:
            if file.endswith('.md'):
                yield os.path.join(root, file)

def update_links(vault_root, old_name, new_name, dry_run=False):
    # Regex to capture [[Old Name]] [[Old Name|Alias]] [[Old Name#Header]]
    escaped_old = re.escape(old_name)
    pattern = re.compile(r'\[\[' + escaped_old + r'([#\|].*?)?\]\]', re.IGNORECASE)

    print(f"Scanning for links to '[[{old_name}]]'...")
    
    count = 0
    for file_path in find_md_files(vault_root):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            
            def replace_callback(match):
                suffix = match.group(1) if match.group(1) else ""
                return f"[[{new_name}{suffix}]]"
            
            new_content, n = pattern.subn(replace_callback, content)
            
            if n > 0:
                print(f"  Found {n} reference(s) in: {os.path.relpath(file_path, vault_root)}")
                count += n
                if not dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                        
        except Exception as e:
            print(f"  Error reading {file_path}: {e}")

    print(f"Link update complete. Updated {count} references.")

def main():
    parser = argparse.ArgumentParser(description="Move a note and update Wikilinks.")
    parser.add_argument("src", help="Source file path (relative to vault root or absolute)")
    parser.add_argument("dest", help="Destination file path (relative to vault root or absolute)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    
    args = parser.parse_args()
    
    vault_root = get_vault_root()
    
    # Resolve paths
    src_path = args.src if os.path.isabs(args.src) else os.path.join(vault_root, args.src)
    dest_path = args.dest if os.path.isabs(args.dest) else os.path.join(vault_root, args.dest)
    
    if not os.path.exists(src_path):
        print(f"Error: Source file not found: {src_path}")
        sys.exit(1)
        
    if os.path.exists(dest_path):
        print(f"Error: Destination already exists: {dest_path}")
        sys.exit(1)

    old_filename = os.path.basename(src_path)
    new_filename = os.path.basename(dest_path)
    
    old_link_name = os.path.splitext(old_filename)[0]
    new_link_name = os.path.splitext(new_filename)[0]

    print(f"Plan:")
    print(f"  Move: {os.path.relpath(src_path, vault_root)} -> {os.path.relpath(dest_path, vault_root)}")
    print(f"  Link: [[{old_link_name}]] -> [[{new_link_name}]]")
    
    if args.dry_run:
        print("[Dry Run] Skipping file operations.")
        update_links(vault_root, old_link_name, new_link_name, dry_run=True)
    else:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.move(src_path, dest_path)
        print(f"File moved successfully.")
        update_links(vault_root, old_link_name, new_link_name, dry_run=False)

if __name__ == "__main__":
    main()
