import os
import sys
import asyncio
import argparse
import time
import tempfile
from notebooklm import NotebookLMClient
from notebooklm.rpc import VideoFormat, SlideDeckFormat, QuizQuantity, QuizDifficulty
from input_processor import process_input_file

# =========================================================================
# GENERIC PROMPTS - Edit these to change the default behavior
# =========================================================================
DEFAULT_VIDEO_PROMPT = (
    "Create a comprehensive educational explainer video overview. "
    "Walk through the key concepts in a logical, structured way, "
    "explaining technical terms and providing illustrative analogies suitable for learning."
)

DEFAULT_SLIDES_PROMPT = (
    "Create a detailed slide deck for presenting this lesson. "
    "Ensure each slide has a clear headline, structured bullet points, "
    "and summarizes one key concept from the source material. "
    "Include a title slide, agenda slide, core content slides, and a conclusion slide."
)

# =========================================================================
# Core Automation Logic
# =========================================================================
async def process_task(client: NotebookLMClient, task: dict, output_dir: str):
    notebook_name = task['notebook_name']
    source_files = task['source_files']
    
    # Resolve prompts (custom override from sheet or default generic)
    video_prompt = task.get('video_prompt') or DEFAULT_VIDEO_PROMPT
    slides_prompt = task.get('slides_prompt') or DEFAULT_SLIDES_PROMPT
    
    print("-" * 50)
    print(f"[START] Processing notebook: {notebook_name}")
    print(f"        Files to upload: {len(source_files)}")
    print(f"        Video prompt length: {len(video_prompt)} chars")
    print(f"        Slides prompt length: {len(slides_prompt)} chars")
    print("-" * 50)
    
    # 1. Create a new notebook
    print("[1/7] Creating notebook in NotebookLM...")
    notebook = await client.notebooks.create(notebook_name)
    notebook_id = notebook.id
    print(f"      Notebook created! ID: {notebook_id}")
    await asyncio.sleep(2)  # brief pause
    
    # 2. Upload source files
    print("[2/7] Uploading source files...")
    uploaded_source_ids = []
    for file_path in source_files:
        filename = os.path.basename(file_path)
        print(f"      Uploading '{filename}'...")
        # add_file with wait=True blocks until the source is processed and ready
        source = await client.sources.add_file(notebook_id, file_path, wait=True)
        uploaded_source_ids.append(source.id)
        print(f"      Source '{filename}' uploaded & ready! ID: {source.id}")
        await asyncio.sleep(1)
        
    print(f"      All {len(uploaded_source_ids)} files uploaded successfully.")
    await asyncio.sleep(3)
    
    # 3. Trigger generations
    print("[3/7] Triggering slide deck generation...")
    slides_status = await client.artifacts.generate_slide_deck(
        notebook_id, 
        instructions=slides_prompt,
        slide_format=SlideDeckFormat.DETAILED_DECK
    )
    print(f"      Slides task ID: {slides_status.task_id} (status: {slides_status.status})")
    await asyncio.sleep(2)
    
    print("[4/7] Triggering video overview generation...")
    video_status = await client.artifacts.generate_video(
        notebook_id, 
        instructions=video_prompt,
        video_format=VideoFormat.EXPLAINER
    )
    print(f"      Video task ID: {video_status.task_id} (status: {video_status.status})")
    await asyncio.sleep(2)
    
    print("[5/7] Triggering quiz and flashcards generation...")
    quiz_status = await client.artifacts.generate_quiz(
        notebook_id,
        quantity=QuizQuantity.STANDARD,
        difficulty=QuizDifficulty.MEDIUM
    )
    print(f"      Quiz task ID: {quiz_status.task_id} (status: {quiz_status.status})")
    await asyncio.sleep(2)
    
    flashcards_status = await client.artifacts.generate_flashcards(
        notebook_id,
        quantity=QuizQuantity.STANDARD,
        difficulty=QuizDifficulty.MEDIUM
    )
    print(f"      Flashcards task ID: {flashcards_status.task_id} (status: {flashcards_status.status})")
    
    # 4. Wait for completions and download
    notebook_output_dir = os.path.join(output_dir, notebook_name.replace(":", "_").replace("/", "_"))
    os.makedirs(notebook_output_dir, exist_ok=True)
    
    # Download Slides
    print("[6/7] Waiting for Slide Deck to complete...")
    await client.artifacts.wait_for_completion(notebook_id, slides_status.task_id)
    slides_path = os.path.join(notebook_output_dir, f"{notebook_name}_slides.pptx")
    print(f"      Downloading slides as PPTX to {slides_path}...")
    await client.artifacts.download_slide_deck(
        notebook_id, 
        slides_path, 
        slides_status.task_id, 
        output_format="pptx"
    )
    print("      Slides downloaded!")
    
    # Download Quiz and Flashcards
    print("      Waiting for Quiz and Flashcards to complete...")
    await client.artifacts.wait_for_completion(notebook_id, quiz_status.task_id)
    await client.artifacts.wait_for_completion(notebook_id, flashcards_status.task_id)
    
    quiz_path = os.path.join(notebook_output_dir, f"{notebook_name}_quiz.md")
    print(f"      Downloading quiz as Markdown to {quiz_path}...")
    await client.artifacts.download_quiz(
        notebook_id, 
        quiz_path, 
        quiz_status.task_id, 
        output_format="markdown"
    )
    
    flashcards_path = os.path.join(notebook_output_dir, f"{notebook_name}_flashcards.md")
    print(f"      Downloading flashcards as Markdown to {flashcards_path}...")
    await client.artifacts.download_flashcards(
        notebook_id, 
        flashcards_path, 
        flashcards_status.task_id, 
        output_format="markdown"
    )
    print("      Quiz and Flashcards downloaded!")
    
    # Download Explainer Video
    print("[7/7] Waiting for Explainer Video to complete (this can take 2-5 minutes)...")
    await client.artifacts.wait_for_completion(notebook_id, video_status.task_id, timeout=600.0)
    video_path = os.path.join(notebook_output_dir, f"{notebook_name}_overview.mp4")
    print(f"      Downloading explainer video to {video_path}...")
    await client.artifacts.download_video(
        notebook_id, 
        video_path, 
        video_status.task_id
    )
    print("      Video overview downloaded!")
    
    print(f"[SUCCESS] Completed NotebookLM operations for notebook: {notebook_name}\n")


async def main_async(spreadsheet_path: str, start_account: int, dry_run: bool, colab: bool, output_dir_override: str, headless: bool):
    # 1. Parse Excel/CSV to load tasks
    print(f"[INFO] Loading spreadsheet: {spreadsheet_path}")
    try:
        tasks = process_input_file(spreadsheet_path)
    except Exception as e:
        print(f"[CRITICAL ERROR] Failed to process spreadsheet: {e}")
        sys.exit(1)
        
    if not tasks:
        print("[INFO] No valid tasks found in spreadsheet. Exiting.")
        return
        
    # Filter by start account
    if start_account > 1:
        print(f"[INFO] Filtering tasks to start from Account #{start_account} onwards...")
        tasks = [t for t in tasks if t['account_num'] >= start_account]
        if not tasks:
            print("[INFO] No tasks remain after filtering. Exiting.")
            return
            
    if dry_run:
        print("\n" + "=" * 60)
        print(" DRY RUN SUMMARY (No actions taken)")
        print("=" * 60)
        for idx, task in enumerate(tasks):
            print(f"Task #{idx+1} | Account: {task['profile_name']} | Notebook: {task['notebook_name']}")
            print(f"  Files: {task['source_files']}")
            print(f"  Video Prompt: {task['video_prompt'] or 'Default Generic'}")
            print(f"  Slides Prompt: {task['slides_prompt'] or 'Default Generic'}")
        print("=" * 60)
        print("[INFO] Dry run complete. Run without --dry-run to execute.")
        return
        
    # Group tasks by profile
    profile_tasks = {}
    for task in tasks:
        profile = task['profile_name']
        profile_tasks.setdefault(profile, []).append(task)
        
    # Check if we are running in Google Colab
    is_colab = colab or spreadsheet_path.startswith('/content/') or (output_dir_override and output_dir_override.startswith('/content/'))
    
    if is_colab:
        print("[INFO] Running in Google Colab / Cloud Mode.")
        if not output_dir_override:
            output_dir_override = "/content/drive/MyDrive/NotebookLM_Syllabus/outputs"
        print(f"[INFO] All outputs will be saved directly to your Google Drive path: {output_dir_override}")
    else:
        print(f"[INFO] Running in Local Temporary Storage Mode (Headless: {headless}).")
        
    # Execute tasks profile by profile
    print("\n" + "=" * 60)
    print(" STARTING LIFECYCLE EXECUTION")
    print("=" * 60)
    
    for profile_name, tasks_list in profile_tasks.items():
        print(f"\n>>> PROCESSING PROFILE: {profile_name} ({len(tasks_list)} notebooks assigned) <<<")
        
        # We process one task at a time for safety and to avoid rate limits
        for task in tasks_list:
            notebook_name = task['notebook_name']
            
            try:
                if is_colab:
                    # In Google Colab, we write files directly to Google Drive target path
                    notebook_output_dir = os.path.join(output_dir_override, notebook_name.replace(":", "_").replace("/", "_"))
                    os.makedirs(notebook_output_dir, exist_ok=True)
                    
                    async with NotebookLMClient.from_storage(profile=profile_name) as client:
                        await process_task(client, task, output_dir_override)
                        
                    slides_path = os.path.join(notebook_output_dir, f"{notebook_name}_slides.pptx")
                    quiz_path = os.path.join(notebook_output_dir, f"{notebook_name}_quiz.md")
                    flashcards_path = os.path.join(notebook_output_dir, f"{notebook_name}_flashcards.md")
                    video_path = os.path.join(notebook_output_dir, f"{notebook_name}_overview.mp4")
                    
                    files_to_compress = [slides_path, quiz_path, flashcards_path, video_path]
                    files_to_compress = [f for f in files_to_compress if os.path.exists(f)]
                    
                    if files_to_compress:
                        zip_file_path = os.path.join(output_dir_override, f"{notebook_name}.zip")
                        import zipfile
                        print(f"[INFO] Creating zip archive locally at '{zip_file_path}'...")
                        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            for f in files_to_compress:
                                zipf.write(f, os.path.basename(f))
                        print(f"[SUCCESS] Zip archive created successfully!")
                    
                    print(f"[SUCCESS] All files for '{notebook_name}' written directly to Google Drive. Local copy is completely clean.")
                    
                else:
                    # Local mode: downloads, zips, uploads via Playwright, and deletes local temp folder
                    with tempfile.TemporaryDirectory() as temp_dir:
                        print(f"[INFO] Created local temporary download directory: {temp_dir}")
                        
                        async with NotebookLMClient.from_storage(profile=profile_name) as client:
                            await process_task(client, task, temp_dir)
                        
                        notebook_temp_dir = os.path.join(temp_dir, notebook_name.replace(":", "_").replace("/", "_"))
                        
                        slides_path = os.path.join(notebook_temp_dir, f"{notebook_name}_slides.pptx")
                        quiz_path = os.path.join(notebook_temp_dir, f"{notebook_name}_quiz.md")
                        flashcards_path = os.path.join(notebook_temp_dir, f"{notebook_name}_flashcards.md")
                        video_path = os.path.join(notebook_temp_dir, f"{notebook_name}_overview.mp4")
                        
                        files_to_upload = [slides_path, quiz_path, flashcards_path, video_path]
                        files_to_upload = [f for f in files_to_upload if os.path.exists(f)]
                        
                        if files_to_upload:
                            zip_file_path = os.path.join(temp_dir, f"{notebook_name}.zip")
                            
                            from gdrive_uploader import compress_files_to_zip, upload_to_gdrive_headless
                            compress_files_to_zip(files_to_upload, zip_file_path)
                            
                            files_to_upload.append(zip_file_path)
                            
                            print(f"[GDrive] Uploading folder files + zip for '{notebook_name}' to Google Drive...")
                            success = await upload_to_gdrive_headless(profile_name, notebook_name, files_to_upload, headless=headless)
                            if success:
                                print(f"[GDrive SUCCESS] Uploaded to Google Drive successfully!")
                            else:
                                print(f"[GDrive WARNING] Google Drive upload timed out or failed.")
                        else:
                            print(f"[WARNING] No files found in '{notebook_temp_dir}' to zip or upload.")
                            
                    print(f"[CLEANUP] Deleted temporary folder: {temp_dir}. Local disk remains completely clean!")
                    
            except Exception as e:
                print(f"\n[ERROR] Task failed: '{notebook_name}' under {profile_name}. Skipping to next task.")
                print(f"        Reason: {e}\n")
                
            # Sleep 10s between notebooks to let sessions cool down
            await asyncio.sleep(10)

def main():
    parser = argparse.ArgumentParser(description="NotebookLM Syllabus Automation Agent")
    parser.add_argument("spreadsheet", help="Path to input Excel (.xlsx) or CSV (.csv) file")
    parser.add_argument("--start-account", type=int, choices=range(1, 11), default=1,
                        help="Google Account number (1-10) to start processing from (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Parse Excel and show planned tasks without executing")
    parser.add_argument("--colab", action="store_true", help="Force Google Colab Cloud Mode")
    parser.add_argument("--output-dir", default="", help="Custom output directory (defaults to Google Drive when in Colab)")
    parser.add_argument("--headless", action="store_true", help="Run browser upload in headless mode (no window pops up)")
    
    args = parser.parse_args()
    
    # Run the async loop using Python 3.12+ recommended way
    asyncio.run(main_async(args.spreadsheet, args.start_account, args.dry_run, args.colab, args.output_dir, args.headless))

if __name__ == "__main__":
    main()
