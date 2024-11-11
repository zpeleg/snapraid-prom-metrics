#!/usr/bin/env python3
import subprocess
import re
import os
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional
from dataclasses import dataclass

@dataclass
class DiskMetrics:
    name: str
    files: int
    fragmented: int
    excess: int
    used_gb: float
    free_gb: float
    use_percent: float

@dataclass
class ArrayMetrics:
    total_files: int          # Changed from files to total_files
    total_fragmented: int     # Changed from fragmented to total_fragmented
    total_excess: int         # Changed from excess to total_excess
    total_used_gb: float      # Changed from used_gb to total_used_gb
    total_free_gb: float      # Changed from free_gb to total_free_gb
    total_use_percent: float  # Changed from use_percent to total_use_percent

@dataclass
class ScrubMetrics:
    oldest_days: int
    median_days: int
    newest_days: int
    coverage_ratio: float

@dataclass
class StatusMetrics:
    sync_in_progress: bool
    zero_subsecond_timestamps: bool
    rehash_needed: bool
    errors_detected: bool

def get_snapraid_output() -> str:
    """Get snapraid status output either from command or file."""
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
            result = subprocess.run(['sudo', 'snapraid', 'status'],
                                  capture_output=True,
                                  text=True,
                                  check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error running snapraid status: {e}")
            return ""

def parse_disk_line(line: str) -> Optional[DiskMetrics]:
    """Parse a single disk line from the status output."""
    parts = line.strip().split()
    if len(parts) == 8 and parts[-1] not in ['-', 'Name']:
        try:
            return DiskMetrics(
                name=parts[-1],
                files=int(parts[0]),
                fragmented=int(parts[1]),
                excess=int(parts[2]),
                used_gb=float(parts[4]),
                free_gb=float(parts[5]),
                use_percent=float(parts[6].rstrip('%'))
            )
        except (ValueError, IndexError):
            return None
    return None

def parse_array_totals(line: str) -> ArrayMetrics:
    """Parse the array totals line."""
    parts = line.strip().split()
    if len(parts) >= 8:
        try:
            return ArrayMetrics(
                total_files=int(parts[0]),
                total_fragmented=int(parts[1]),
                total_excess=int(parts[2]),
                total_used_gb=float(parts[4]),
                total_free_gb=float(parts[5]),
                total_use_percent=float(parts[6].rstrip('%'))
            )
        except (ValueError, IndexError):
            pass
    return ArrayMetrics(0, 0, 0, 0.0, 0.0, 0.0)

def parse_scrub_info(output: str) -> ScrubMetrics:
    """Parse scrub-related information from the output."""
    coverage_match = re.search(r"(\d+)% of the array is not scrubbed", output)
    coverage = 1.0 - (float(coverage_match.group(1))/100 if coverage_match else 0)

    days_match = re.search(
        r"The oldest block was scrubbed (\d+) days ago, the median (\d+), the newest (\d+)",
        output
    )
    if days_match:
        oldest, median, newest = map(int, days_match.groups())
    else:
        oldest = median = newest = 0

    return ScrubMetrics(
        oldest_days=oldest,
        median_days=median,
        newest_days=newest,
        coverage_ratio=coverage
    )

def parse_status_flags(output: str) -> StatusMetrics:
    """Parse various status flags from the output."""
    return StatusMetrics(
        sync_in_progress="No sync is in progress" not in output,
        zero_subsecond_timestamps="No file has a zero sub-second timestamp" not in output,
        rehash_needed="No rehash is in progress or needed" not in output,
        errors_detected="No error detected" not in output
    )

def parse_snapraid_output(output: str) -> tuple[List[DiskMetrics], ArrayMetrics, ScrubMetrics, StatusMetrics]:
    """Parse snapraid status output into structured data."""
    lines = output.strip().split('\n')
    disks = []
    array_totals = None

    # Find the status table
    table_start = None
    table_end = None
    for i, line in enumerate(lines):
        if "Files Fragmented" in line:
            table_start = i + 2
        elif table_start and line.startswith('----'):
            table_end = i
            break

    if table_start and table_end:
        # Parse individual disk lines
        for line in lines[table_start:table_end]:
            disk = parse_disk_line(line)
            if disk:
                disks.append(disk)

        # Parse array totals from the line after the divider
        if table_end + 1 < len(lines):
            array_totals = parse_array_totals(lines[table_end + 1])

    if not array_totals:
        array_totals = ArrayMetrics(0, 0, 0, 0.0, 0.0, 0.0)

    scrub_metrics = parse_scrub_info(output)
    status_metrics = parse_status_flags(output)

    return disks, array_totals, scrub_metrics, status_metrics

def generate_prometheus_metrics(
    disks: List[DiskMetrics],
    array: ArrayMetrics,
    scrub: ScrubMetrics,
    status: StatusMetrics
) -> str:
    """Generate Prometheus metrics in text format."""
    metrics = []

    # Per-disk metrics
    metrics.extend([
        "# HELP snapraid_disk_files_total Number of files on each disk",
        "# TYPE snapraid_disk_files_total gauge"
    ])
    for disk in disks:
        metrics.append(f'snapraid_disk_files_total{{name="{disk.name}"}} {disk.files}')

    metrics.extend([
        "\n# HELP snapraid_disk_fragmented_files Number of fragmented files on each disk",
        "# TYPE snapraid_disk_fragmented_files gauge"
    ])
    for disk in disks:
        metrics.append(f'snapraid_disk_fragmented_files{{name="{disk.name}"}} {disk.fragmented}')

    metrics.extend([
        "\n# HELP snapraid_disk_excess_fragments Number of excess fragments on each disk",
        "# TYPE snapraid_disk_excess_fragments gauge"
    ])
    for disk in disks:
        metrics.append(f'snapraid_disk_excess_fragments{{name="{disk.name}"}} {disk.excess}')

    metrics.extend([
        "\n# HELP snapraid_disk_space_bytes Disk space information in bytes",
        "# TYPE snapraid_disk_space_bytes gauge"
    ])
    for disk in disks:
        used_bytes = int(disk.used_gb * 1e9)
        free_bytes = int(disk.free_gb * 1e9)
        metrics.append(f'snapraid_disk_space_bytes{{name="{disk.name}",type="used"}} {used_bytes}')
        metrics.append(f'snapraid_disk_space_bytes{{name="{disk.name}",type="free"}} {free_bytes}')

    # Array metrics
    metrics.extend([
        "\n# HELP snapraid_array_files_total Total number of files in the array",
        "# TYPE snapraid_array_files_total gauge",
        f"snapraid_array_files_total {array.total_files}",  # Changed from array.files

        "\n# HELP snapraid_array_fragmented_files_total Total number of fragmented files in the array",
        "# TYPE snapraid_array_fragmented_files_total gauge",
        f"snapraid_array_fragmented_files_total {array.total_fragmented}",  # Changed from array.fragmented

        "\n# HELP snapraid_array_excess_fragments_total Total number of excess fragments in the array",
        "# TYPE snapraid_array_excess_fragments_total gauge",
        f"snapraid_array_excess_fragments_total {array.total_excess}",  # Changed from array.excess

        "\n# HELP snapraid_array_space_bytes Array space information in bytes",
        "# TYPE snapraid_array_space_bytes gauge"
    ])
    total_used_bytes = int(array.total_used_gb * 1e9)
    total_free_bytes = int(array.total_free_gb * 1e9)
    metrics.append(f'snapraid_array_space_bytes{{type="used"}} {total_used_bytes}')
    metrics.append(f'snapraid_array_space_bytes{{type="free"}} {total_free_bytes}')

    # Scrub metrics
    metrics.extend([
        "\n# HELP snapraid_scrub_age_days Age of blocks in days",
        "# TYPE snapraid_scrub_age_days gauge",
        f'snapraid_scrub_age_days{{type="oldest"}} {scrub.oldest_days}',
        f'snapraid_scrub_age_days{{type="median"}} {scrub.median_days}',
        f'snapraid_scrub_age_days{{type="newest"}} {scrub.newest_days}',

        "\n# HELP snapraid_scrub_coverage_ratio Ratio of array that has been scrubbed (0.0-1.0)",
        "# TYPE snapraid_scrub_coverage_ratio gauge",
        f"snapraid_scrub_coverage_ratio {scrub.coverage_ratio}"
    ])

    # Status metrics
    metrics.extend([
        "\n# HELP snapraid_status Various status indicators",
        "# TYPE snapraid_status gauge",
        f'snapraid_status{{type="sync_in_progress"}} {int(status.sync_in_progress)}',
        f'snapraid_status{{type="zero_subsecond_timestamps"}} {int(status.zero_subsecond_timestamps)}',
        f'snapraid_status{{type="rehash_needed"}} {int(status.rehash_needed)}',
        f'snapraid_status{{type="errors_detected"}} {int(status.errors_detected)}'
    ])

    return "\n".join(metrics)

def main():
    # Get output directory from environment variable or use default
    output_dir = os.getenv('TEXTFILE_DIRECTORY', '/var/lib/prometheus/node_exporter')
    output_path = Path(output_dir) / 'snapraid_status.prom'

    # Get snapraid output
    snapraid_output = get_snapraid_output()
    if not snapraid_output:
        print("No output from snapraid status command or input file")
        return

    # Parse the output
    disks, array_totals, scrub_metrics, status_metrics = parse_snapraid_output(snapraid_output)

    # Generate metrics
    metrics = generate_prometheus_metrics(disks, array_totals, scrub_metrics, status_metrics)

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
