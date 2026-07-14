import pandas as pd
import os

def create_mock():
    # Get absolute path of mock_study_guide.txt
    file_path = os.path.abspath("mock_study_guide.txt")
    
    data = {
        "Notebook Name": [
            "Quantum Physics 101",
            "Intro to Superposition",
            "Entanglement Explained",
            "IBM Quantum Devices",
            "Quantum Algorithms"
        ],
        "Material Path": [
            file_path,
            file_path,
            file_path,
            file_path,
            file_path
        ],
        "Video Prompt": [
            "",
            "Focus on the Bloch sphere explanation.",
            "",
            "",
            "Explain Shor's and Grover's algorithms in simple terms."
        ],
        "Slides Prompt": [
            "",
            "",
            "",
            "",
            ""
        ]
    }
    
    df = pd.DataFrame(data)
    df.to_excel("mock_input.xlsx", index=False)
    print("[SUCCESS] Created mock_input.xlsx referencing local mock_study_guide.txt")

if __name__ == "__main__":
    create_mock()
