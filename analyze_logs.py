import sys

try:
    with open("logs_debug_2.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    found_error = False
    context_lines = []
    
    for i, line in enumerate(lines):
        if "Internal Server Error" in line or "Traceback" in line or "Exception" in line:
            found_error = True
            # Print 20 lines before and 20 lines after
            start = max(0, i - 20)
            end = min(len(lines), i + 20)
            print(f"--- ERROR CONTEXT AT LINE {i} ---")
            for j in range(start, end):
                print(lines[j].strip())
            print("--- END CONTEXT ---")
            
    if not found_error:
        print("No error keywords found. Printing last 50 lines:")
        for line in lines[-50:]:
            print(line.strip())

except Exception as e:
    print(f"Error reading log file: {e}")
