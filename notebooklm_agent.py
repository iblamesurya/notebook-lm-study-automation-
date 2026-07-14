import os
import sys
import asyncio
import argparse
import time
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
    
    print(f"[SUCCESS] Completed all operations for notebook: {notebook_name}\n")


async def main_async(spreadsheet_path: str, start_account: int, dry_run: bool, output_dir: str):
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
        
    # Execute tasks profile by profile
    print("\n" + "=" * 60)
    print(" STARTING LIFECYCLE EXECUTION")
    print("=" * 60)
    
    for profile_name, tasks_list in profile_tasks.items():
        print(f"\n>>> PROCESSING PROFILE: {profile_name} ({len(tasks_list)} notebooks assigned) <<<")
        
        # We process one task at a time for safety and to avoid rate limits
        for task in tasks_list:
            try:
                # Instantiate client and open session for this profile
                async with NotebookLMClient.from_storage(profile=profile_name) as client:
                    await process_task(client, task, output_dir)
            except Exception as e:
                print(f"\n[ERROR] Task failed: '{task['notebook_name']}' under {profile_name}. Skipping to next task.")
                print(f"        Reason: {e}\n")
                
            # Sleep 10s between notebooks to let sessions cool down
            await asyncio.sleep(10)

def main():
    parser = argparse.ArgumentParser(description="NotebookLM Syllabus Automation Agent")
    parser.add_argument("spreadsheet", help="Path to input Excel (.xlsx) or CSV (.csv) file")
    parser.add_argument("--start-account", type=int, choices=range(1, 11), default=1,
                        help="Google Account number (1-10) to start processing from (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Parse Excel and show planned tasks without executing")
    parser.add_argument("--output-dir", default="outputs", help="Directory to save downloaded files (default: outputs)")
    
    args = parser.parse_args()
    
    # Run the async loop using Python 3.12+ recommended way
    asyncio.run(main_async(args.spreadsheet, args.start_account, args.dry_run, args.output_dir))

if __name__ == "__main__":
    main()
