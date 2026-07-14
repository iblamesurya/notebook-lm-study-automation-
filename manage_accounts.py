import subprocess
import argparse
import os
import sys

def get_profile_name(account_num):
    return f"account_{account_num}"

def get_storage_path(account_num):
    profile = get_profile_name(account_num)
    return os.path.join(
        os.path.expanduser("~"), 
        ".notebooklm", 
        "profiles", 
        profile, 
        "storage_state.json"
    )

def login(account_num):
    profile = get_profile_name(account_num)
    print("=" * 60)
    print(f" STARTING LOG IN PROCESS FOR GOOGLE AI PRO ACCOUNT #{account_num}")
    print(f" Profile name: {profile}")
    print("=" * 60)
    print("A browser window will open. Please log in to your Google Account.")
    print("Once logged in and NotebookLM loads, you can close the browser window.")
    print("Press Enter to open the browser...")
    input()
    
    try:
        # Run notebooklm login command for the specific profile
        subprocess.run(["notebooklm", "-p", profile, "login"], check=True, shell=True)
        print(f"\n[SUCCESS] Successfully logged in for Account #{account_num}!")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Failed to log in for Account #{account_num}. Details: {e}")
    except FileNotFoundError:
        print("\n[ERROR] 'notebooklm' CLI not found. Please install the requirements first.")
        print("Run: pip install notebooklm-py")

def check_accounts():
    print("=" * 60)
    print(" CHECKING AUTHENTICATION STATUS FOR GOOGLE ACCOUNTS 1 - 10")
    print("=" * 60)
    
    configured_count = 0
    for i in range(1, 11):
        profile = get_profile_name(i)
        storage_path = get_storage_path(i)
        sys.stdout.write(f"Account #{i} ({profile}): ")
        sys.stdout.flush()
        
        # Check if storage_state.json exists and is not empty
        if os.path.exists(storage_path) and os.path.getsize(storage_path) > 0:
            print("CONNECTED [OK]")
            configured_count += 1
        else:
            print("NOT CONFIGURED [MISSING]")
            
    print("=" * 60)
    print(f"[INFO] {configured_count} of 10 accounts are configured.")
    if configured_count == 10:
        print("[SUCCESS] All 10 accounts are ready to go!")
    else:
        print("[INFO] Use --login <number> to configure remaining accounts.")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="NotebookLM Account Profile Manager")
    parser.add_argument("--login", type=int, choices=range(1, 11), help="Login to a specific Google account (1-10)")
    parser.add_argument("--check", action="store_true", help="Check login status of all 10 accounts")
    
    args = parser.parse_args()
    
    if args.login:
        login(args.login)
    elif args.check:
        check_accounts()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
