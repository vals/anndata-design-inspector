#!/usr/bin/env python3
"""
Wrapper script to generate grammar without needing cat/echo piping.
Takes JSON as command-line argument instead of stdin.
"""
import sys
import json
from pathlib import Path

# Add parent directory to path to import design_to_grammar
sys.path.insert(0, str(Path(__file__).parent))

from design_to_grammar import convert_design_to_grammar

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_grammar.py '<json_string>'", file=sys.stderr)
        return 1

    json_str = sys.argv[1]

    try:
        design = json.loads(json_str)
        grammar = convert_design_to_grammar(design)
        print(grammar)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
