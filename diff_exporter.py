#!/usr/bin/env python3
import subprocess
import re
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class DiffMetrics:
    equal: int = 0
    added: int = 0
    removed: int = 0
    updated: int = 0
    moved: int = 0
    copied: int = 0
    restored: int = 0
    has_differences: bool = False

def get_snapraid_output() -> str:
    """Get snapraid diff output either from command or file."""
    input_file = os.getenv('SNAPRAID_INPUT_FILE')

    if input_file:
        try:
            with open(input_file, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading input file {input_file}: {e}")
            return ""
    else:
        try:
            result = subprocess.run(['sudo', 'snapraid', 'diff'],
                                  capture_output=True,
                                  text=True,
                                  check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error running snapraid diff: {e}")
            return ""

def parse_diff_line(line: str, metrics: DiffMetrics) -> None:
    """Parse a single line from the diff output."""
    line = line.strip()

    # Define patterns for each metric
    patterns = {
        'equal': r'(\d+)\s+equal',
        'added': r'(\d+)\s+added',
        'removed': r'(\d+)\s+removed',
        'updated': r'(\d+)\s+updated',
        'moved': r'(\d+)\s+moved',
        'copied': r'(\d+)\s+copied',
        'restored': r'(\d+)\s+restored'
    }

    # Check each pattern
    for metric_name, pattern in patterns.items():
        match = re.search(pattern, line)
        if match:
            value = int(match.group(1))
            setattr(metrics, metric_name, value)

def parse_snapraid_output(output: str) -> DiffMetrics:
    """Parse snapraid diff output into structured data."""
    metrics = DiffMetrics()

    for line in output.strip().split('\n'):
        parse_diff_line(line, metrics)

    # Check if there are any differences
    metrics.has_differences = "No differences" not in output

    return metrics

def generate_prometheus_metrics(metrics: DiffMetrics) -> str:
    """Generate Prometheus metrics in text format."""
    output = []

    # File count metrics
    output.extend([
        "# HELP snapraid_diff_files_total Number of files in each state",
        "# TYPE snapraid_diff_files_total gauge"
    ])

    # Add metrics for each state
    states = {
        'equal': 'Files unchanged since last sync',
        'added': 'Files added since last sync',
        'removed': 'Files removed since last sync',
        'updated': 'Files updated since last sync',
        'moved': 'Files moved since last sync',
        'copied': 'Files copied since last sync',
        'restored': 'Files restored since last sync'
    }

    for state, desc in states.items():
        value = getattr(metrics, state)
        output.append(f'snapraid_diff_files_total{{state="{state}"}} {value}')

    # Status metric
    output.extend([
        "\n# HELP snapraid_diff_has_differences Whether there are any differences (0=no, 1=yes)",
        "# TYPE snapraid_diff_has_differences gauge",
        f"snapraid_diff_has_differences {int(metrics.has_differences)}"
    ])

    return "\n".join(output)

def main():
    # Get output directory from environment variable or use default
    output_dir = os.getenv('TEXTFILE_DIRECTORY', '/var/lib/prometheus/node_exporter')
    output_path = Path(output_dir) / 'snapraid_diff.prom'

    # Get snapraid output
    snapraid_output = get_snapraid_output()
    if not snapraid_output:
        print("No output from snapraid diff command or input file")
        return

    # Parse the output
    diff_metrics = parse_snapraid_output(snapraid_output)

    # Generate metrics
    metrics = generate_prometheus_metrics(diff_metrics)

    # Create directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write temporary file and rename to ensure atomic writes
    temp_path = output_path.with_suffix('.prom.tmp')
    try:
        with open(temp_path, 'w') as f:
            f.write(metrics)
            f.write('\n')
        temp_path.rename(output_path)
        print(f"Successfully wrote metrics to {output_path}")
    except Exception as e:
        print(f"Error writing metrics file: {e}")
        if temp_path.exists():
            temp_path.unlink()

if __name__ == "__main__":
    main()
