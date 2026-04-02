"""
gore2sft.py — Convert GORE dataset to SFT training format.

Usage:
    python gore2sft.py <input.jsonl> [--output <output.jsonl>] [--format chat|completion]
"""

import json
import sys
import argparse


def to_completion_format(example):
    """Convert to completion format: prompt + response."""
    program = example["program"].strip()
    query = example["query"]
    trace = example.get("trace", [])
    solutions = example.get("solutions", [])

    prompt = f"Execute the following GORE program and show the reasoning trace.\n\nProgram:\n```gore\n{program}\n```\n\nQuery: {query}\n\nTrace:"

    trace_str = "\n".join(trace)
    sol_str = json.dumps(solutions, default=str)
    response = f"\n{trace_str}\n\nSolutions: {sol_str}"

    return {"prompt": prompt, "response": response}


def to_chat_format(example):
    """Convert to chat format with system/user/assistant messages."""
    program = example["program"].strip()
    query = example["query"]
    trace = example.get("trace", [])
    solutions = example.get("solutions", [])

    system_msg = "You are a GORE language interpreter. Given a GORE program and query, produce the execution trace step by step, then list all solutions."

    user_msg = f"Execute this GORE program:\n\n```gore\n{program}\n```\n\nQuery: {query}"

    trace_str = "\n".join(trace)
    sol_str = json.dumps(solutions, default=str)
    assistant_msg = f"Trace:\n{trace_str}\n\nSolutions: {sol_str}"

    return {
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]
    }


def convert(input_path, output_path=None, fmt="chat"):
    if output_path is None:
        output_path = input_path.replace(".jsonl", f"_sft_{fmt}.jsonl")

    converter = to_chat_format if fmt == "chat" else to_completion_format
    count = 0

    with open(input_path) as f, open(output_path, "w") as out:
        for line in f:
            ex = json.loads(line)
            converted = converter(ex)
            out.write(json.dumps(converted) + "\n")
            count += 1

    print(f"Converted {count} examples → {output_path} (format: {fmt})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert GORE dataset to SFT format")
    parser.add_argument("input", help="Input JSONL file")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--format", "-f", choices=["chat", "completion"], default="chat")
    args = parser.parse_args()
    convert(args.input, args.output, args.format)
