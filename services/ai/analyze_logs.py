import sys
import os

try:
    try:
        with open("logs_verify_final.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open("logs_verify_final.txt", "r", encoding="utf-16", errors="replace") as f:
            lines = f.readlines()
        
    found_error = False
    
    for i, line in enumerate(lines):
        if "789abb74" in line or "update_skill" in line or "Received learning event" in line:
            found_error = True
            print(f"\n--- MATCH AT LINE {i} ---")
            start = max(0, i - 10)
            end = min(len(lines), i + 20)
            for j in range(start, end):
                print(lines[j].rstrip())
            print("--- END MATCH ---\n")
            
    if not found_error:
        print("No error keywords found. Printing last 50 lines:")
        for line in lines[-50:]:
            print(line.rstrip())

except Exception as e:
    print(f"Error reading log file: {e}")
