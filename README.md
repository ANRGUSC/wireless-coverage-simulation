# USC Campus Wireless Coverage Simulation

A wireless coverage simulation tool that demonstrates key concepts in wireless network planning using a map of the USC campus.

## Features

- **Path loss modeling** using free-space path loss (Friis equation)
- **Log-normal shadowing** to model random signal variations
- **Line-of-sight (LOS) blocking** by buildings using Bresenham's algorithm
- **SNR-based coverage determination**
- Visual coverage map generation with color-coded base station coverage areas

## Usage

```bash
python usc_coverage.py
```

The simulation will generate a coverage visualization saved as `output.png`.

## Adjustable Parameters

Students and researchers can modify these parameters in the script:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TX_POWER_DBM` | -10.0 | Transmit power in dBm |
| `NOISE_DBM` | -101.0 | Noise floor in dBm |
| `SNR_THRESHOLD_DB` | 10.0 | Minimum SNR for coverage |
| `SHADOW_STD_DB` | 4.0 | Log-normal shadowing std dev |
| `FREQ_HZ` | 2.4e9 | Carrier frequency (2.4 GHz) |
| `NUM_BASE_STATIONS` | 6 | Number of base stations |
| `RANDOM_SEED` | 2 | Seed for reproducibility |

## Requirements

- Python 3.x
- NumPy
- Pillow (PIL)
- Matplotlib

## Author

Created by Bhaskar Krishnamachari (USC), January 2026.

## License

This project is licensed under the PolyForm Noncommercial License 1.0.0 - see the [LICENSE](LICENSE) file for details.
