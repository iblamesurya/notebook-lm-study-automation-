import os
import pandas as pd
import sys

SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.md', '.markdown', '.docx', '.pptx', '.html', '.htm'}

def get_files_for_path(path):
    """
    Given a file or folder path, returns a list of absolute paths to supported files.
    """
    path = os.path.abspath(path)
    
    if not os.path.exists(path):
        print(f"[WARNING] Path does not exist: {path}")
        return []
        
    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            return [path]
        else:
            print(f"[WARNING] File extension '{ext}' is not supported by NotebookLM: {path}")
            return []
            
    # If it is a directory, gather all supported files inside it
    files = []
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            ext = os.path.splitext(file_path)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                files.append(file_path)
                
    if not files:
        print(f"[WARNING] No supported files found in directory: {path}")
        
    return files

def process_input_file(filepath):
    """
    Reads the input Excel/CSV file and parses the rows.
    Assigns each row to an account (4 notebooks per account).
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input file not found at: {filepath}")
        
    # Determine the file type and read
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.xlsx':
        df = pd.read_excel(filepath)
    elif ext == '.csv':
        df = pd.read_csv(filepath)
    else:
        raise ValueError("Unsupported input file format. Please use .xlsx or .csv")
        
    # Standardize column names (strip spaces, lowercase, etc.)
    df.columns = [col.strip().lower() for col in df.columns]
    
    # Map back to required columns
    notebook_col = None
    path_col = None
    video_prompt_col = None
    slides_prompt_col = None
    
    for col in df.columns:
        if 'notebook' in col or 'name' in col or 'topic' in col:
            notebook_col = col
        if 'path' in col or 'link' in col or 'material' in col:
            path_col = col
        if 'video' in col and 'prompt' in col:
            video_prompt_col = col
        if 'slide' in col and 'prompt' in col:
            slides_prompt_col = col
            
    if not notebook_col or not path_col:
        # Fallback to column indices if named matches are not found
        if len(df.columns) >= 2:
            notebook_col = df.columns[0]
            path_col = df.columns[1]
        else:
            raise KeyError("Spreadsheet must contain at least 2 columns: Notebook Name and Material Path.")
            
    print(f"[INFO] Using columns: '{notebook_col}' for Notebook Name and '{path_col}' for Material Path.")
    if video_prompt_col:
        print(f"[INFO] Using column: '{video_prompt_col}' for custom Video Prompts.")
    if slides_prompt_col:
        print(f"[INFO] Using column: '{slides_prompt_col}' for custom Slides Prompts.")
    
    tasks = []
    skipped_count = 0
    
    for idx, row in df.iterrows():
        notebook_name = str(row[notebook_col]).strip()
        material_path = str(row[path_col]).strip()
        
        if not notebook_name or notebook_name == 'nan' or not material_path or material_path == 'nan':
            continue
            
        # Get list of files
        files_to_upload = get_files_for_path(material_path)
        
        if not files_to_upload:
            print(f"[SKIPPED] Row {idx+1}: '{notebook_name}' due to missing or unsupported files at path: {material_path}")
            skipped_count += 1
            continue
            
        # Extract optional prompts
        video_prompt = ""
        if video_prompt_col and not pd.isna(row[video_prompt_col]):
            video_prompt = str(row[video_prompt_col]).strip()
            if video_prompt.lower() == 'nan':
                video_prompt = ""
                
        slides_prompt = ""
        if slides_prompt_col and not pd.isna(row[slides_prompt_col]):
            slides_prompt = str(row[slides_prompt_col]).strip()
            if slides_prompt.lower() == 'nan':
                slides_prompt = ""
            
        tasks.append({
            'notebook_name': notebook_name,
            'source_files': files_to_upload,
            'original_path': material_path,
            'video_prompt': video_prompt,
            'slides_prompt': slides_prompt
        })
        
    # Assign accounts: 4 notebooks per account
    # Account 1 gets tasks 0-3, Account 2 gets 4-7, etc.
    final_tasks = []
    for idx, task in enumerate(tasks):
        account_num = (idx // 4) + 1
        if account_num > 10:
            print(f"[WARNING] Task '{task['notebook_name']}' exceeds the 10-account limit. This task will be ignored.")
            continue
        task['account_num'] = account_num
        task['profile_name'] = f"account_{account_num}"
        final_tasks.append(task)
        
    print(f"[INFO] Loaded {len(final_tasks)} valid tasks from spreadsheet. {skipped_count} rows were skipped.")
    
    # Summarize account distribution
    for i in range(1, 11):
        count = sum(1 for t in final_tasks if t['account_num'] == i)
        if count > 0:
            print(f"  - Account #{i} (account_{i}): {count} notebooks assigned")
            
    return final_tasks

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python input_processor.py <path_to_excel_or_csv>")
        sys.exit(1)
        
    try:
        tasks = process_input_file(sys.argv[1])
        print("\nParsed tasks successfully:")
        for t in tasks:
            print(f"Account #{t['account_num']} | Notebook: {t['notebook_name']} | Files: {len(t['source_files'])} | Custom Video Prompt: {'Yes' if t['video_prompt'] else 'No'} | Custom Slides Prompt: {'Yes' if t['slides_prompt'] else 'No'}")
    except Exception as e:
        print(f"[ERROR] {e}")
