import os
import subprocess

def run_test(input_file, expected_output_file, actual_output_file):
    # Run the scheduling script to generate the actual output (scheduler-gpt.py writes to the actual folder internally)
    subprocess.run(['python', 'scheduler-gpt.py', input_file])

    # Use PowerShell's Compare-Object to compare the actual and expected output
    command = f"Compare-Object (Get-Content {actual_output_file}) (Get-Content {expected_output_file})"
    result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True)

    # If there is any output from Compare-Object, the files are different
    if result.stdout.strip():
        print(f"{input_file}: Fail")
        print(result.stdout)  # Print the differences
    else:
        print(f"{input_file}: Pass")

def run_all_tests():
    input_dir = "inputs"
    expected_dir = "expected"
    actual_dir = "actual"

    # Create the 'actual' directory if it doesn't exist
    if not os.path.exists(actual_dir):
        os.makedirs(actual_dir)

    for filename in os.listdir(input_dir):
        if filename.endswith(".in"):
            input_file = os.path.join(input_dir, filename)
            expected_output_file = os.path.join(expected_dir, filename.replace(".in", ".out"))
            actual_output_file = os.path.join(actual_dir, filename.replace(".in", ".out"))

            run_test(input_file, expected_output_file, actual_output_file)

if __name__ == "__main__":
    run_all_tests()