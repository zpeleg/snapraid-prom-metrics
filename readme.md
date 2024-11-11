# SnapRAID Prometheus Exporters

A collection of Python scripts that export SnapRAID metrics for Prometheus monitoring via the node_exporter textfile collector mechanism. These exporters allow you to monitor your SnapRAID array's health, status, and changes over time.

The scripts take the output of `snapraid status`, `snapraid smart`, and `snapraid diff` and convert them to node_exporter text files.

## Features

Three independent exporters are provided:

1. **SMART Metrics** (`smart_exporter.py`) - based on `snapraid smart`
   - Disk temperatures
   - Power-on days
   - Error counts
   - Failure probabilities
   - Disk sizes

2. **Status Metrics** (`status_exporter.py`) - based on `snapraid status`
   - Files per disk
   - Fragmentation stats
   - Space usage
   - Scrub status
   - Array health indicators

3. **Diff Metrics** (`diff_exporter.py`) - based on `snapraid diff` 
   - File changes (added/removed/updated)
   - Sync status
   - Difference detection

## Why These Exporters?

Monitoring snapraid requires either logging in to the server and checking periodically, or getting the mail server active. This should expose most metrics you will need for day to day monitoring.

## Installation

1. Create a directory for the exporters:
```bash
sudo mkdir -p /opt/snapraid-metrics
sudo chmod 755 /opt/snapraid-metrics
```

2. Copy the exporter scripts:
```bash
sudo cp *_exporter.py /opt/snapraid-metrics/
sudo chmod 755 /opt/snapraid-metrics/*_exporter.py
```

3. Create the textfile collector directory (if not exists):
```bash
sudo mkdir -p /var/lib/node_exporter/textfile_collector
sudo chown -R node-exporter:node-exporter /var/lib/node_exporter
```

4. Setup periodic execution via cron:
```bash
sudo crontab -e
```

Add the following lines:
```cron
# SnapRAID Metrics Collection
*/15 * * * * TEXTFILE_DIRECTORY=/my/prometheus/collectors /opt/snapraid-metrics/smart_exporter.py
*/15 * * * * TEXTFILE_DIRECTORY=/my/prometheus/collectors /opt/snapraid-metrics/status_exporter.py
*/15 * * * * TEXTFILE_DIRECTORY=/my/prometheus/collectors /opt/snapraid-metrics/diff_exporter.py
```

## Configuration

The exporters can be configured via environment variables:

- `SNAPRAID_INPUT_FILE`: Path to a file containing command output (useful for testing)
- `TEXTFILE_DIRECTORY`: Directory where metric files will be written (default: `/var/lib/node_exporter`)

## Metrics

### SMART Metrics
```
# HELP snapraid_disk_temperature_celsius Current temperature of the disk
snapraid_disk_temperature_celsius{device="/dev/sda",serial="ABC123",name="d1"} 35

# HELP snapraid_disk_power_on_days Total number of days the disk has been powered on
snapraid_disk_power_on_days{device="/dev/sda",serial="ABC123",name="d1"} 1234

# Full metric documentation in script comments
```

### Status Metrics
```
# HELP snapraid_disk_temperature_celsius Current temperature of the disk
# TYPE snapraid_disk_temperature_celsius gauge
snapraid_disk_temperature_celsius{device="/dev/sdb",serial="1EG95YSZ",name="d1"} 32
snapraid_disk_temperature_celsius{device="/dev/sdf",serial="2SG7RV8J",name="d2"} 32
snapraid_disk_temperature_celsius{device="/dev/sde",serial="JEKVBMDZ",name="d3"} 33
snapraid_disk_temperature_celsius{device="/dev/sdc",serial="VCH0HPLP",name="parity"} 37
snapraid_disk_temperature_celsius{device="/dev/sdd",serial="VCH249LP",name="2-parity"} 38

# HELP snapraid_disk_power_on_days Total number of days the disk has been powered on
# TYPE snapraid_disk_power_on_days counter
snapraid_disk_power_on_days{device="/dev/sdb",serial="1EG95YSZ",name="d1"} 1432
snapraid_disk_power_on_days{device="/dev/sdf",serial="2SG7RV8J",name="d2"} 1433
snapraid_disk_power_on_days{device="/dev/sde",serial="JEKVBMDZ",name="d3"} 1433
snapraid_disk_power_on_days{device="/dev/sdc",serial="VCH0HPLP",name="parity"} 1152
snapraid_disk_power_on_days{device="/dev/sdd",serial="VCH249LP",name="2-parity"} 1152

# HELP snapraid_disk_error_count Total number of errors detected on the disk
# TYPE snapraid_disk_error_count counter
snapraid_disk_error_count{device="/dev/sdb",serial="1EG95YSZ",name="d1"} 0
snapraid_disk_error_count{device="/dev/sdf",serial="2SG7RV8J",name="d2"} 0
snapraid_disk_error_count{device="/dev/sde",serial="JEKVBMDZ",name="d3"} 0
snapraid_disk_error_count{device="/dev/sdc",serial="VCH0HPLP",name="parity"} 0
snapraid_disk_error_count{device="/dev/sdd",serial="VCH249LP",name="2-parity"} 0

# HELP snapraid_disk_failure_probability_percent Estimated probability of disk failure in the next year
# TYPE snapraid_disk_failure_probability_percent gauge
snapraid_disk_failure_probability_percent{device="/dev/sdb",serial="1EG95YSZ",name="d1"} 35.0
snapraid_disk_failure_probability_percent{device="/dev/sdf",serial="2SG7RV8J",name="d2"} 32.0
snapraid_disk_failure_probability_percent{device="/dev/sde",serial="JEKVBMDZ",name="d3"} 35.0
snapraid_disk_failure_probability_percent{device="/dev/sdc",serial="VCH0HPLP",name="parity"} 4.0
snapraid_disk_failure_probability_percent{device="/dev/sdd",serial="VCH249LP",name="2-parity"} 4.0

# HELP snapraid_disk_size_bytes Size of the disk in bytes
# TYPE snapraid_disk_size_bytes gauge
snapraid_disk_size_bytes{device="/dev/sdb",serial="1EG95YSZ",name="d1"} 8000000000000
snapraid_disk_size_bytes{device="/dev/sdf",serial="2SG7RV8J",name="d2"} 8000000000000
snapraid_disk_size_bytes{device="/dev/sde",serial="JEKVBMDZ",name="d3"} 8000000000000
snapraid_disk_size_bytes{device="/dev/sdc",serial="VCH0HPLP",name="parity"} 10000000000000
snapraid_disk_size_bytes{device="/dev/sdd",serial="VCH249LP",name="2-parity"} 10000000000000

# HELP snapraid_array_failure_probability_percent Probability that at least one disk will fail in the next year
# TYPE snapraid_array_failure_probability_percent gauge
snapraid_array_failure_probability_percent 73.0
```

### Diff Metrics
```
# HELP snapraid_diff_files_total Number of files in each state
# TYPE snapraid_diff_files_total gauge
snapraid_diff_files_total{state="equal"} 147732
snapraid_diff_files_total{state="added"} 0
snapraid_diff_files_total{state="removed"} 0
snapraid_diff_files_total{state="updated"} 0
snapraid_diff_files_total{state="moved"} 0
snapraid_diff_files_total{state="copied"} 0
snapraid_diff_files_total{state="restored"} 0

# HELP snapraid_diff_has_differences Whether there are any differences (0=no, 1=yes)
# TYPE snapraid_diff_has_differences gauge
snapraid_diff_has_differences 0
```

### Status Metrics
```
# HELP snapraid_disk_files_total Number of files on each disk
# TYPE snapraid_disk_files_total gauge

# HELP snapraid_disk_fragmented_files Number of fragmented files on each disk
# TYPE snapraid_disk_fragmented_files gauge

# HELP snapraid_disk_excess_fragments Number of excess fragments on each disk
# TYPE snapraid_disk_excess_fragments gauge

# HELP snapraid_disk_space_bytes Disk space information in bytes
# TYPE snapraid_disk_space_bytes gauge

# HELP snapraid_array_files_total Total number of files in the array
# TYPE snapraid_array_files_total gauge
snapraid_array_files_total 0

# HELP snapraid_array_fragmented_files_total Total number of fragmented files in the array
# TYPE snapraid_array_fragmented_files_total gauge
snapraid_array_fragmented_files_total 0

# HELP snapraid_array_excess_fragments_total Total number of excess fragments in the array
# TYPE snapraid_array_excess_fragments_total gauge
snapraid_array_excess_fragments_total 0

# HELP snapraid_array_space_bytes Array space information in bytes
# TYPE snapraid_array_space_bytes gauge
snapraid_array_space_bytes{type="used"} 0
snapraid_array_space_bytes{type="free"} 0

# HELP snapraid_scrub_age_days Age of blocks in days
# TYPE snapraid_scrub_age_days gauge
snapraid_scrub_age_days{type="oldest"} 129
snapraid_scrub_age_days{type="median"} 3
snapraid_scrub_age_days{type="newest"} 0

# HELP snapraid_scrub_coverage_ratio Ratio of array that has been scrubbed (0.0-1.0)
# TYPE snapraid_scrub_coverage_ratio gauge
snapraid_scrub_coverage_ratio 0.65

# HELP snapraid_status Various status indicators
# TYPE snapraid_status gauge
snapraid_status{type="sync_in_progress"} 0
snapraid_status{type="zero_subsecond_timestamps"} 0
snapraid_status{type="rehash_needed"} 0
snapraid_status{type="errors_detected"} 0
```

## Testing

You can test the exporters without running SnapRAID by providing sample output:

```bash
SNAPRAID_INPUT_FILE=./tests/sample_smart.txt ./smart_exporter.py
SNAPRAID_INPUT_FILE=./tests/sample_status.txt ./status_exporter.py
SNAPRAID_INPUT_FILE=./tests/sample_diff.txt ./diff_exporter.py
```

## Contributing

Contributions are welcome! Please submit pull requests with any improvements.

## Important caveats

This entire thing was thrown together in an hour with the help of Claude, it is far from tested beyond the outputs that I had on hand, please open an issue/pull request with any input that you have that caused the script to fail.
