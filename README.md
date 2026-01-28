# USC Campus Wireless Coverage Simulation

A wireless coverage simulation tool that demonstrates key concepts in wireless network planning using a map of the USC campus. The project includes both Python scripts for batch simulation and an interactive web application.

## Features

- **Path loss modeling** using free-space path loss (Friis equation)
- **Log-normal shadowing** to model random signal variations
- **Line-of-sight (LOS) blocking** by buildings
- **SNR-based coverage determination**
- Visual coverage map generation with color-coded base station coverage areas

## Project Structure

### Python Scripts

- `usc_coverage.py` — Batch coverage simulation that generates a static coverage map (`output.png`)
- `interactive_coverage_tool.py` — Interactive PyQt5 application for placing, moving, and deleting base stations with real-time coverage visualization

```bash
python usc_coverage.py
python interactive_coverage_tool.py
```

**Python Requirements:** Python 3.x, NumPy, Pillow (PIL), Matplotlib, PyQt5

### Web Application (`usc-wireless-coverage/`)

A Progressive Web App that reimplements the interactive coverage tool for the browser. Deployed at [usc-wireless-coverage.vercel.app](https://usc-wireless-coverage.vercel.app).

**Tech stack:** React, TypeScript, Vite, HTML5 Canvas 2D, Web Workers, PWA (vite-plugin-pwa)

- Click to place base stations, drag to move, right-click to delete
- Adjustable RF parameters with real-time recalculation
- Export coverage map as PNG
- Works offline as an installable PWA

See [`usc-wireless-coverage/README.md`](usc-wireless-coverage/README.md) for more details.

## Adjustable Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| TX Power | -10.0 dBm | Transmit power |
| Noise Floor | -101.0 dBm | Noise floor |
| SNR Threshold | 10.0 dB | Minimum SNR for coverage |
| Shadowing Std Dev | 4.0 dB | Log-normal shadowing standard deviation |
| Frequency | 2.4 GHz | Carrier frequency |

## Acknowledgments

Thanks to USC student Xinwei Li for providing a clean USC campus map used in this project.

## Author

Created by Bhaskar Krishnamachari (USC), January 2026.

## License

This project is licensed under the PolyForm Noncommercial License 1.0.0 - see the [LICENSE](LICENSE) file for details.
