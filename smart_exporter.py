#!/usr/bin/env python3
import subprocess
import re
from pathlib import Path
from typing import Dict, List, NamedTuple

class DiskMetrics(NamedTuple):
    temperature: int
    power_days: int
    error_count: int
    failure_prob: float
    size_tb: float
    serial: str
    device: str
    name: str

def parse_size_tb(size_str: str) -> float:
    """Convert size string to TB float value."""
    if not size_str or size_str == '-':
        return 0.0
    return float(size_str)

def run_snapraid_smart() -> str:
    """Run snapraid smart command and return output."""
    try:
        result = subprocess.run(['sudo', 'snapraid', 'smart'], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running snapraid smart: {e}")
        return ""

def parse_snapraid_output(output: str) -> tuple[List[DiskMetrics], float]:
    """Parse snapraid smart output and return list of disk metrics and array failure probability."""
    disks = []
    array_failure_prob = 0.0
    
    # Skip header lines
    lines = output.strip().split('\n')[3:]
    
    for line in lines:
        if line.startswith('----'):
            continue
        if line.startswith('The FP column'):
            break
            
        # Parse disk line
        parts = line.strip().split()
        if len(parts) >= 8:
            try:
                temp = int(parts[0]) if parts[0].isdigit() else 0
                power_days = int(parts[1]) if parts[1].isdigit() else 0
                error_count = int(parts[2]) if parts[2].isdigit() else 0
                failure_prob = float(parts[3].rstrip('%')) if parts[3] != '-' else 0.0
                size_tb = parse_size_tb(parts[4])
                serial = parts[5]
                device = parts[6]
                name = parts[7]
                
                if device != '-' and serial != '-':
                    disks.append(DiskMetrics(
                        temperature=temp,
                        power_days=power_days,
                        error_count=error_count,
                        failure_prob=failure_prob,
                        size_tb=size_tb,
                        serial=serial,
                        device=device,
                        name=name
                    ))
            except (ValueError, IndexError) as e:
                print(f"Error parsing line: {line}, Error: {e}")
                continue
    
    # Extract array failure probability
    for line in lines:
        if "fail in the next year is" in line:
            match = re.search(r"(\d+(?:\.\d+)?)%", line)
            if match:
                array_failure_prob = float(match.group(1))
            break
    
    return disks, array_failure_prob

def generate_prometheus_metrics(disks: List[DiskMetrics], array_failure_prob: float) -> str:
    """Generate Prometheus metrics in text format."""
    metrics = []
    
    # Temperature metrics
    metrics.append("# HELP snapraid_disk_temperature_celsius Current temperature of the disk")
    metrics.append("# TYPE snapraid_disk_temperature_celsius gauge")
    for disk in disks:
        if disk.temperature > 0:
            metrics.append(f'snapraid_disk_temperature_celsius{{device="{disk.device}",serial="{disk.serial}",name="{disk.name}"}} {disk.temperature}')
    
    # Power-on days metrics
    metrics.append("\n# HELP snapraid_disk_power_on_days Total number of days the disk has been powered on")
    metrics.append("# TYPE snapraid_disk_power_on_days counter")
    for disk in disks:
        if disk.power_days > 0:
            metrics.append(f'snapraid_disk_power_on_days{{device="{disk.device}",serial="{disk.serial}",name="{disk.name}"}} {disk.power_days}')
    
    # Error count metrics
    metrics.append("\n# HELP snapraid_disk_error_count Total number of errors detected on the disk")
    metrics.append("# TYPE snapraid_disk_error_count counter")
    for disk in disks:
        metrics.append(f'snapraid_disk_error_count{{device="{disk.device}",serial="{disk.serial}",name="{disk.name}"}} {disk.error_count}')
    
    # Failure probability metrics
    metrics.append("\n# HELP snapraid_disk_failure_probability_percent Estimated probability of disk failure in the next year")
    metrics.append("# TYPE snapraid_disk_failure_probability_percent gauge")
    for disk in disks:
        metrics.append(f'snapraid_disk_failure_probability_percent{{device="{disk.device}",serial="{disk.serial}",name="{disk.name}"}} {disk.failure_prob}')
    
    # Disk size metrics
    metrics.append("\n# HELP snapraid_disk_size_bytes Size of the disk in bytes")
    metrics.append("# TYPE snapraid_disk_size_bytes gauge")
    for disk in disks:
        size_bytes = int(disk.size_tb * 1e12)  # Convert TB to bytes
        metrics.append(f'snapraid_disk_size_bytes{{device="{disk.device}",serial="{disk.serial}",name="{disk.name}"}} {size_bytes}')
    
    # Array failure probability
    metrics.append("\n# HELP snapraid_array_failure_probability_percent Probability that at least one disk will fail in the next year")
    metrics.append("# TYPE snapraid_array_failure_probability_percent gauge")
    metrics.append(f"snapraid_array_failure_probability_percent {array_failure_prob}")
    
    return "\n".join(metrics)

def main():
    # Set the output file path
    output_dir = os.getenv('TEXTFILE_DIRECTORY', '/var/lib/prometheus/node_exporter')
    output_path = Path(output_dir) / 'snapraid_smart.prom'
    
    # Run snapraid smart and get output
    snapraid_output = run_snapraid_smart()
    if not snapraid_output:
        print("No output from snapraid smart command")
        return
    
    # Parse the output
    disks, array_failure_prob = parse_snapraid_output(snapraid_output)
    
    # Generate metrics
    metrics = generate_prometheus_metrics(disks, array_failure_prob)
    
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
