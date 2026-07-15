import os
import sys
import zipfile

def package_profiles():
    # Path to the .notebooklm folder in the user's home directory
    profiles_dir = os.path.join(os.path.expanduser("~"), ".notebooklm")
    output_zip = "notebooklm_profiles.zip"
    
    if not os.path.exists(profiles_dir):
        print(f"[ERROR] NotebookLM profiles directory not found at: {profiles_dir}")
        print("Please log in to at least one account using 'manage_accounts.py --login <num>' first.")
        return
        
    print(f"[INFO] Packaging profiles from: {profiles_dir}...")
    print(f"[INFO] Compressing into: {output_zip}...")
    
    try:
        count = 0
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(profiles_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Create relative path inside the zip file
                    arcname = os.path.relpath(file_path, os.path.dirname(profiles_dir))
                    zipf.write(file_path, arcname)
                    count += 1
                    
        print(f"[SUCCESS] Packaged {count} profile files into '{output_zip}' successfully!")
        print("[INFO] You can now upload 'notebooklm_profiles.zip' to your Google Drive.")
        
    except Exception as e:
        print(f"[ERROR] Failed to package profiles: {e}")

if __name__ == "__main__":
    package_profiles()
