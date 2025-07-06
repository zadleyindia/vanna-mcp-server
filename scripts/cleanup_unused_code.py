#!/usr/bin/env python3
"""
Cleanup unused code references to:
- query_history table
- access_control table
- training_data table
- vannabq schema
"""

import os
import re
from pathlib import Path

def main():
    """Main cleanup function"""
    project_root = Path(__file__).parent.parent
    
    # 1. Remove _store_query_history function and its call
    vanna_ask_file = project_root / "src/tools/vanna_ask.py"
    if vanna_ask_file.exists():
        print(f"Cleaning up {vanna_ask_file}")
        with open(vanna_ask_file, 'r') as f:
            content = f.read()
        
        # Remove the function call
        content = re.sub(r'\s*_store_query_history\([^)]+\)\n?', '\n', content)
        
        # Remove the function definition
        content = re.sub(
            r'def _store_query_history.*?# Don\'t fail the main operation if history storage fails\n',
            '',
            content,
            flags=re.DOTALL
        )
        
        with open(vanna_ask_file, 'w') as f:
            f.write(content)
        print("✓ Removed _store_query_history references")
    
    # 2. Remove ACCESS_CONTROL settings that aren't used
    settings_file = project_root / "src/config/settings.py"
    if settings_file.exists():
        print(f"\nChecking {settings_file}")
        with open(settings_file, 'r') as f:
            content = f.read()
        
        # Check if ACCESS_CONTROL_MODE is actually used anywhere
        src_files = list((project_root / "src").rglob("*.py"))
        access_control_used = False
        
        for src_file in src_files:
            if src_file == settings_file:
                continue
            with open(src_file, 'r') as f:
                if 'ACCESS_CONTROL' in f.read():
                    access_control_used = True
                    print(f"  ACCESS_CONTROL is used in {src_file.relative_to(project_root)}")
                    break
        
        if not access_control_used:
            print("✓ ACCESS_CONTROL settings are not used anywhere else")
        else:
            print("⚠️  ACCESS_CONTROL settings are still in use")
    
    # 3. Remove setup_database.py references to unused tables
    setup_db_file = project_root / "scripts/setup_database.py"
    if setup_db_file.exists():
        print(f"\nChecking {setup_db_file}")
        print("⚠️  This file creates unused tables but might be kept for reference")
    
    # 4. Check for vannabq schema references
    print("\nChecking for vannabq schema references...")
    vannabq_files = []
    for src_file in project_root.rglob("*.py"):
        if '_archive' in str(src_file) or 'venv' in str(src_file):
            continue
        try:
            with open(src_file, 'r') as f:
                if 'vannabq' in f.read():
                    vannabq_files.append(src_file.relative_to(project_root))
        except:
            pass
    
    if vannabq_files:
        print(f"Found {len(vannabq_files)} files with vannabq references:")
        for f in vannabq_files[:10]:  # Show first 10
            print(f"  - {f}")
        if len(vannabq_files) > 10:
            print(f"  ... and {len(vannabq_files) - 10} more")
    
    print("\n✅ Cleanup analysis complete!")
    print("\nRecommendations:")
    print("1. The _store_query_history function has been removed from vanna_ask.py")
    print("2. ACCESS_CONTROL settings might still be needed for configuration")
    print("3. Consider keeping setup_database.py as documentation of original design")
    print("4. Update any remaining vannabq references to use public schema")

if __name__ == "__main__":
    main()