#!/usr/bin/env python3
"""
Build script for gRPC proto files.

Generates Python stubs from .proto definitions.
Run from services/ai directory.
"""
import os
import subprocess
import sys
from pathlib import Path


def main():
    """Generate gRPC stubs from proto files."""
    # Get paths
    script_dir = Path(__file__).parent
    proto_dir = script_dir / "proto"
    output_dir = script_dir / "proto_gen"
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Create __init__.py
    (output_dir / "__init__.py").write_text('"""Generated gRPC stubs."""\n')
    
    # Proto files to compile
    proto_files = list(proto_dir.glob("*.proto"))
    
    if not proto_files:
        print("No .proto files found in", proto_dir)
        return 1
    
    print(f"Found {len(proto_files)} proto files:")
    for p in proto_files:
        print(f"  - {p.name}")
    
    # Compile each proto file
    for proto_file in proto_files:
        print(f"\nCompiling {proto_file.name}...")
        
        cmd = [
            sys.executable, "-m", "grpc_tools.protoc",
            f"--proto_path={proto_dir}",
            f"--python_out={output_dir}",
            f"--grpc_python_out={output_dir}",
            f"--pyi_out={output_dir}",
            str(proto_file)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error compiling {proto_file.name}:")
                print(result.stderr)
                return 1
            print(f"  Generated stubs for {proto_file.stem}")
        except FileNotFoundError:
            print("Error: grpc_tools not found. Install with:")
            print("  pip install grpcio-tools")
            return 1
    
    print(f"\n✓ All proto files compiled successfully to {output_dir}/")
    print("\nGenerated files:")
    for f in output_dir.glob("*.py"):
        print(f"  - {f.name}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
