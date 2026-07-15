import os
import sys
import asyncio
import zipfile
import time
from playwright.async_api import async_playwright

def get_browser_profile_dir(profile_name):
    """
    Returns the absolute path to the browser profile directory for a given account.
    """
    return os.path.join(
        os.path.expanduser("~"), 
        ".notebooklm", 
        "profiles", 
        profile_name, 
        "browser_profile"
    )

def compress_files_to_zip(files_list, output_zip_path):
    """
    Compresses a specific list of files into a single zip file.
    Runs locally and is extremely optimized.
    """
    print(f"[INFO] Creating optimized zip archive at '{output_zip_path}'...")
    try:
        # Use ZIP_DEFLATED to compress files
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_list:
                if os.path.exists(file_path):
                    # Store file inside zip with its basename (no absolute paths)
                    zipf.write(file_path, os.path.basename(file_path))
                    print(f"      Added to zip: {os.path.basename(file_path)}")
        print(f"[SUCCESS] Zip archive created successfully at: {output_zip_path}")
        return output_zip_path
    except Exception as e:
        print(f"[ERROR] Failed to create zip archive: {e}")
        return None

async def upload_to_gdrive_headless(profile_name, folder_name, files_to_upload, headless=False):
    """
    Automates Google Drive using Playwright with the user's logged-in session.
    Supports running in headless mode.
    """
    profile_dir = get_browser_profile_dir(profile_name)
    if not os.path.exists(profile_dir):
        print(f"[ERROR] Browser profile directory not found for {profile_name}: {profile_dir}")
        print("Please log in to this account first using: python manage_accounts.py --login <number>")
        return False
        
    print(f"[INFO] Launching Playwright browser (Headless={headless}) with profile: {profile_name}...")
    
    async with async_playwright() as p:
        # Launch browser context
        context = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=headless,
            no_viewport=True,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        page = await context.new_page()
        
        print("[INFO] Navigating to Google Drive...")
        await page.goto("https://drive.google.com/drive/my-drive", timeout=60000)
        
        # 1. Wait for page to load (look for the "New" button or Search input)
        print("[INFO] Waiting for Google Drive to load...")
        try:
            new_btn = page.locator('button:has-text("New")').first
            await new_btn.wait_for(state="visible", timeout=30000)
        except Exception:
            # Fallback selectors
            new_btn = page.locator('div[role="button"]:has-text("New")').first
            await new_btn.wait_for(state="visible", timeout=20000)
            
        print("[SUCCESS] Google Drive loaded successfully!")
        await asyncio.sleep(2)
        
        # 2. Create the folder on Google Drive
        print(f"[INFO] Creating new folder: '{folder_name}'...")
        await new_btn.click()
        await asyncio.sleep(1)
        
        # Click "New folder"
        new_folder_option = page.locator('span:has-text("New folder")').first
        await new_folder_option.click()
        
        # Wait for the folder name input dialog
        input_selector = 'div[role="dialog"] input[type="text"]'
        await page.wait_for_selector(input_selector, timeout=10000)
        await page.locator(input_selector).fill(folder_name)
        
        # Click "Create" button in dialog
        create_btn = page.locator('div[role="dialog"] button:has-text("Create")').first
        await create_btn.click()
        print(f"[SUCCESS] Folder '{folder_name}' created on Google Drive.")
        await asyncio.sleep(3)
        
        # 3. Enter the folder on Google Drive
        print(f"[INFO] Entering folder '{folder_name}'...")
        folder_element = page.locator(f'div[role="gridcell"] >> text="{folder_name}"').first
        try:
            await folder_element.wait_for(state="visible", timeout=10000)
            await folder_element.dblclick()
        except Exception:
            fallback_folder = page.get_by_text(folder_name).first
            await fallback_folder.dblclick()
            
        await asyncio.sleep(3)
        print(f"[INFO] Currently inside Google Drive folder: '{folder_name}'")
        
        # 4. Trigger file upload using standard File Chooser
        print(f"[INFO] Starting upload for {len(files_to_upload)} files...")
        
        async with page.expect_file_chooser() as fc_info:
            try:
                new_btn_inner = page.locator('button:has-text("New")').first
                await new_btn_inner.click()
            except Exception:
                new_btn_inner = page.locator('div[role="button"]:has-text("New")').first
                await new_btn_inner.click()
                
            await asyncio.sleep(1)
            file_upload_option = page.locator('span:has-text("File upload")').first
            await file_upload_option.click()
            
        file_chooser = fc_info.value
        # Upload all generated files
        await file_chooser.set_files(files_to_upload)
        print(f"[INFO] Upload initiated. Transferring files...")
        
        # 5. Monitor progress bar and wait for upload completion
        print("[INFO] Waiting for uploads to complete...")
        
        upload_complete = False
        start_time = time.time()
        # Max wait timeout of 10 minutes (600 seconds)
        while time.time() - start_time < 600:
            content = await page.content()
            if "uploads complete" in content.lower() or "upload complete" in content.lower():
                print("[SUCCESS] All files uploaded to Google Drive successfully!")
                upload_complete = True
                break
            await asyncio.sleep(5)
            
        if not upload_complete:
            print("[WARNING] Upload timed out or state could not be verified, closing browser anyway.")
            
        await asyncio.sleep(2)
        await context.close()
        return upload_complete

if __name__ == "__main__":
    # Test execution
    if len(sys.argv) < 4:
        print("Usage: python gdrive_uploader.py <profile_name> <folder_name> <file1> <file2> ...")
        sys.exit(1)
        
    profile = sys.argv[1]
    folder = sys.argv[2]
    files = sys.argv[3:]
    
    asyncio.run(upload_to_gdrive_headless(profile, folder, files, headless=True))
