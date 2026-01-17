def parse_log_line(line: str):
    line = line.strip()
    if not line:
        return None
    
    # error = ["ERROR","Error","error"]

    if "error" not in line.lower():
        return None
            
    print(f"Error Line: {line}")

    return {
        "level": "ERROR",
        "message": line,
        "service": "unknown"
    }
