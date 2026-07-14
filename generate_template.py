import pandas as pd
import os

def create_template():
    data = {
        "Notebook Name": [
            "Introduction to Machine Learning",
            "Linear Regression Basics",
            "Deep Learning Deep Dive",
            "Natural Language Processing Overview"
        ],
        "Material Path": [
            "C:/path/to/your/study/material/folder_or_file1.pdf",
            "C:/path/to/your/study/material/folder_or_file2.docx",
            "C:/path/to/your/study/material/folder_or_file3.txt",
            "C:/path/to/your/study/material/folder_or_file4.pptx"
        ],
        "Video Prompt": [
            "Explain the history of ML, its main subfields (supervised, unsupervised, reinforcement), and its everyday applications.",
            "",  # Empty cells will automatically fall back to the generic prompt
            "Focus on explaining backpropagation and multi-layer perceptrons with clear, step-by-step mathematical logic.",
            ""
        ],
        "Slides Prompt": [
            "Create slides outlining ML subfields with clear definitions.",
            "",
            "Structure slides to explain forward and backward passes visually.",
            ""
        ]
    }
    
    df = pd.DataFrame(data)
    
    # Save as Excel
    excel_path = "input_template.xlsx"
    df.to_excel(excel_path, index=False)
    print(f"[SUCCESS] Created Excel template: {excel_path}")
    
    # Save as CSV as well (for users who prefer CSV)
    csv_path = "input_template.csv"
    df.to_csv(csv_path, index=False)
    print(f"[SUCCESS] Created CSV template: {csv_path}")

if __name__ == "__main__":
    create_template()
