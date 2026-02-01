# USC Campus Wireless Coverage Simulation

A wireless coverage simulation tool that demonstrates key concepts in wireless network planning using a map of the USC campus. The project includes both Python scripts for batch simulation/optimization and an interactive web application. **Both implementations produce identical results** using the same algorithms and deterministic random number generation.

## Features

- **Path loss modeling** using free-space path loss (Friis equation)
- **Log-normal shadowing** to model random signal variations
- **Line-of-sight (LOS) blocking** by buildings using 720-ray visibility maps
- **SNR-based coverage determination**
- **1/8 resolution downscaling** for fast computation
- Visual coverage map generation with color-coded base station coverage areas

## Project Structure

### Python Scripts

#### `usc_coverage.py` — Coverage Engine

The core coverage calculation engine that produces results identical to the web application. Provides a clean API for coverage optimization (e.g., simulated annealing).

```python
from usc_coverage import CoverageCalculator, SeededRNG, MAP_WIDTH_M, MAP_HEIGHT_M

# Create calculator once (loads and preprocesses building mask)
calc = CoverageCalculator("usc_map_buildings_filled.png")

# Calculate coverage for a set of base station locations (in meters)
bs_locations = [(200.0, 150.0), (400.0, 250.0), (500.0, 300.0)]
coverage_percent = calc.calculate_coverage(bs_locations)  # Returns 0-100

# Validate if a location is outdoors (for placement constraints)
is_valid = calc.is_outdoor(x_meters, y_meters)  # Returns bool

# Generate random outdoor locations (for initial population)
x, y = calc.get_random_outdoor_location()  # Returns (x_m, y_m) tuple

# Get detailed output including visualization data
result = calc.calculate_coverage_detailed(bs_locations)
# Returns: coverage_percent, max_range, image_data, bs_colors, etc.
```

**Algorithm Details:**
- Uses Mulberry32 PRNG with Box-Muller transform for deterministic shadowing
- 720-ray visibility map for O(1) line-of-sight lookup
- 1/8 resolution downscaling (300x220 grid instead of 2400x1760)
- Identical results to the web application with seed=42

**Performance:**
- Pure Python (NumPy): ~280ms per base station
- With Numba: ~30ms per base station (install with `pip install numba`)

**Run standalone simulation:**
```bash
python usc_coverage.py
```

#### `interactive_coverage_tool.py` — Interactive GUI

A PyQt5 desktop application for interactive base station placement with real-time coverage visualization.

```bash
python interactive_coverage_tool.py
```

**Features:**
- Click to place base stations
- Drag to move base stations
- Right-click to delete base stations
- Adjust RF parameters via input fields
- Export coverage map as `output.png`

### Web Application (`usc-wireless-coverage/`)

A Progressive Web App that reimplements the interactive coverage tool for the browser. Deployed at [usc-wireless-coverage.vercel.app](https://usc-wireless-coverage.vercel.app).

**Tech stack:** React, TypeScript, Vite, HTML5 Canvas 2D, Web Workers, PWA (vite-plugin-pwa)

**Features:**
- Click to place base stations, drag to move, right-click to delete
- Adjustable RF parameters with real-time recalculation (~50-200ms)
- Export coverage map as PNG
- Works offline as an installable PWA

See [`usc-wireless-coverage/README.md`](usc-wireless-coverage/README.md) for more details.

## Requirements

### Python
```bash
pip install numpy pillow matplotlib pyqt5
pip install numba  # Optional, for 10x faster performance
```

### Web Application
```bash
cd usc-wireless-coverage
npm install
npm run dev
```

## Adjustable Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| TX Power | -10.0 dBm | Transmit power |
| Noise Floor | -101.0 dBm | Noise floor (20 MHz bandwidth) |
| SNR Threshold | 10.0 dB | Minimum SNR for coverage |
| Shadowing Std Dev | 4.0 dB | Log-normal shadowing standard deviation |
| Frequency | 2.4 GHz | Carrier frequency |

## Map Dimensions

- **Physical size:** 640m x 430m
- **Image resolution:** 2400 x 1760 pixels
- **Compute resolution:** 300 x 220 pixels (1/8 scale)

## Acknowledgments

Thanks to USC student Xinwei Li for providing a clean USC campus map used in this project.

## Author

Created by Bhaskar Krishnamachari (USC), January 2025.

## License

This project is licensed under the PolyForm Noncommercial License 1.0.0 - see the [LICENSE](LICENSE) file for details.
