"""
USC Campus Wireless Coverage Simulation with Line-of-Sight Blocking

This simulation demonstrates key concepts in wireless network planning:
1. Path loss modeling (free-space path loss)
2. Log-normal shadowing (random signal variation)
3. Line-of-sight (LOS) blocking by buildings
4. SNR-based coverage determination

Students can modify the parameters in the "ADJUSTABLE PARAMETERS" section
to explore how different factors affect coverage.
"""

import numpy as np
from PIL import Image

# =============================================================================
# ADJUSTABLE PARAMETERS - Students can modify these!
# =============================================================================

# Transmit power in dBm (higher = larger coverage area)
# Typical values: smartphone ~20 dBm, WiFi AP ~20 dBm, small cell ~30 dBm
TX_POWER_DBM = -10.0

# Noise floor in dBm (determined by bandwidth and noise figure)
# For 20 MHz bandwidth: approximately -101 dBm
NOISE_DBM = -101.0

# Minimum SNR required for reliable communication (in dB)
# Typical values: 10 dB for basic connectivity, 20+ dB for high data rates
SNR_THRESHOLD_DB = 10.0

# Log-normal shadowing standard deviation (in dB)
# Models random signal variations due to obstacles, reflections, etc.
# Typical values: 4-8 dB for urban environments
SHADOW_STD_DB = 4.0

# Carrier frequency in Hz (affects path loss)
# Common values: 2.4 GHz (WiFi), 3.5 GHz (5G), 28 GHz (mmWave)
FREQ_HZ = 2.4e9

# Number of base stations to simulate
NUM_BASE_STATIONS = 6

# Random seed for reproducibility (change to get different random placements)
RANDOM_SEED = 2

# =============================================================================
# FIXED MAP PARAMETERS - Do not modify
# =============================================================================

MAP_WIDTH_M = 640.0    # Map width in meters
MAP_HEIGHT_M = 430.0   # Map height in meters

# =============================================================================
# LOAD BUILDING MASK IMAGE
# =============================================================================
# The building mask is a binary image:
#   - Black pixels (value < 128) = buildings (block signals)
#   - White pixels (value >= 128) = outdoor areas (can receive signals)

BUILDING_MASK_PATH = "usc_map_buildings_filled.png"

# Load image as grayscale
img = Image.open(BUILDING_MASK_PATH).convert("L")
img_np = np.array(img)
IMG_HEIGHT, IMG_WIDTH = img_np.shape

# Create boolean masks
building_mask = img_np < 128      # True where buildings exist
outdoor_mask = ~building_mask     # True where outdoor areas exist

# =============================================================================
# COORDINATE CONVERSION FUNCTIONS
# =============================================================================

def meters_to_pixels(x_meters, y_meters):
    """
    Convert real-world coordinates (meters) to image pixel coordinates.

    Args:
        x_meters: Horizontal position in meters (0 = left edge)
        y_meters: Vertical position in meters (0 = top edge)

    Returns:
        (px, py): Pixel coordinates in the image
    """
    px = int(x_meters / MAP_WIDTH_M * IMG_WIDTH)
    py = int(y_meters / MAP_HEIGHT_M * IMG_HEIGHT)
    # Clamp to valid image bounds
    px = max(0, min(IMG_WIDTH - 1, px))
    py = max(0, min(IMG_HEIGHT - 1, py))
    return px, py


def pixels_to_meters(px, py):
    """
    Convert image pixel coordinates to real-world coordinates (meters).

    Args:
        px: Horizontal pixel position
        py: Vertical pixel position

    Returns:
        (x_meters, y_meters): Position in meters
    """
    x_meters = px / IMG_WIDTH * MAP_WIDTH_M
    y_meters = py / IMG_HEIGHT * MAP_HEIGHT_M
    return x_meters, y_meters


# =============================================================================
# LINE-OF-SIGHT CHECKING
# =============================================================================

def has_line_of_sight(x1, y1, x2, y2):
    """
    Check if there's a clear line-of-sight between two points.

    Uses Bresenham's line algorithm to walk along every pixel between
    the two points. If any pixel is a building, LOS is blocked.

    Args:
        x1, y1: Start point in meters (typically base station location)
        x2, y2: End point in meters (typically receiver location)

    Returns:
        True if line-of-sight exists (no buildings in the way)
        False if a building blocks the path
    """
    # Convert meter coordinates to pixel coordinates
    px1, py1 = meters_to_pixels(x1, y1)
    px2, py2 = meters_to_pixels(x2, y2)

    # Bresenham's line algorithm
    # This efficiently walks through all pixels along a line
    dx = abs(px2 - px1)
    dy = abs(py2 - py1)
    sx = 1 if px1 < px2 else -1  # Step direction for x
    sy = 1 if py1 < py2 else -1  # Step direction for y
    err = dx - dy

    cx, cy = px1, py1  # Current position

    while True:
        # Check if current pixel is a building
        if building_mask[cy, cx]:
            return False  # LOS blocked!

        # Check if we've reached the destination
        if cx == px2 and cy == py2:
            break

        # Move to next pixel along the line
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            cx += sx
        if e2 < dx:
            err += dx
            cy += sy

    return True  # No buildings encountered, LOS exists


# =============================================================================
# PATH LOSS MODEL
# =============================================================================

def free_space_path_loss(distance_m):
    """
    Calculate free-space path loss (FSPL) in dB.

    The Friis transmission equation gives path loss as:
        FSPL = 20*log10(4*pi*d/wavelength)

    This represents signal attenuation in free space (no obstacles).

    Args:
        distance_m: Distance between transmitter and receiver in meters

    Returns:
        Path loss in dB (always positive - represents signal reduction)
    """
    c = 3e8  # Speed of light in m/s
    wavelength = c / FREQ_HZ

    # Friis free-space path loss formula
    fspl_db = 20 * np.log10(4 * np.pi * distance_m / wavelength)

    return fspl_db


def calculate_max_range():
    """
    Calculate the maximum possible coverage range.

    This is the distance at which SNR equals the threshold,
    accounting for potential favorable shadowing (3-sigma margin).

    Returns:
        Maximum range in meters
    """
    c = 3e8
    wavelength = c / FREQ_HZ

    # Maximum allowable path loss (with 3-sigma shadowing margin)
    # SNR = TX_POWER - PATH_LOSS - NOISE >= SNR_THRESHOLD
    # PATH_LOSS <= TX_POWER - NOISE - SNR_THRESHOLD
    max_path_loss = TX_POWER_DBM - NOISE_DBM - SNR_THRESHOLD_DB + 3 * SHADOW_STD_DB

    # Invert the FSPL formula to get distance
    # FSPL = 20*log10(4*pi*d/wavelength)
    # d = wavelength / (4*pi) * 10^(FSPL/20)
    max_range = (wavelength / (4 * np.pi)) * (10 ** (max_path_loss / 20))

    return max_range


# =============================================================================
# COVERAGE VISUALIZATION
# =============================================================================

def run_coverage_simulation():
    """
    Main simulation function.

    1. Places base stations randomly in outdoor locations
    2. For each outdoor pixel, checks if it's covered by any base station
    3. A pixel is "covered" if:
       - It has line-of-sight to the base station
       - The received SNR meets the threshold
    4. Generates a color-coded visualization showing coverage areas
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    print("=" * 60)
    print("USC Campus Coverage Simulation")
    print("=" * 60)

    # Set random seed for reproducibility
    np.random.seed(RANDOM_SEED)

    # Print simulation parameters
    print(f"\nSimulation Parameters:")
    print(f"  Transmit Power:     {TX_POWER_DBM} dBm")
    print(f"  Noise Floor:        {NOISE_DBM} dBm")
    print(f"  SNR Threshold:      {SNR_THRESHOLD_DB} dB")
    print(f"  Shadowing Std Dev:  {SHADOW_STD_DB} dB")
    print(f"  Carrier Frequency:  {FREQ_HZ/1e9} GHz")
    print(f"  Number of BSs:      {NUM_BASE_STATIONS}")

    # Calculate maximum coverage range
    max_range = calculate_max_range()
    print(f"\nMax Coverage Range:   {max_range:.1f} meters")

    # -------------------------------------------------------------------------
    # STEP 1: Find all outdoor pixels and place base stations
    # -------------------------------------------------------------------------

    # Get coordinates of all outdoor pixels
    outdoor_pixels = np.argwhere(outdoor_mask)  # Returns (py, px) pairs
    print(f"\nTotal outdoor pixels: {len(outdoor_pixels)}")

    # Randomly select outdoor locations for base stations
    bs_indices = np.random.choice(len(outdoor_pixels), NUM_BASE_STATIONS, replace=False)

    # Convert pixel locations to meter coordinates
    base_stations = []
    for idx in bs_indices:
        py, px = outdoor_pixels[idx]
        x_m, y_m = pixels_to_meters(px, py)
        base_stations.append((x_m, y_m))
    base_stations = np.array(base_stations)

    print(f"\nBase Station Locations:")
    for i, (x, y) in enumerate(base_stations):
        print(f"  BS {i+1}: ({x:.1f}, {y:.1f}) meters")

    # -------------------------------------------------------------------------
    # STEP 2: Generate random shadowing maps
    # -------------------------------------------------------------------------
    # Each base station has its own independent shadowing realization.
    # This models the fact that different paths experience different
    # random obstacles and reflections.

    print(f"\nGenerating shadowing maps...")
    shadowing_maps = []
    for i in range(NUM_BASE_STATIONS):
        # Normal distribution with mean=0 and std=SHADOW_STD_DB
        shadow = np.random.normal(0, SHADOW_STD_DB, (IMG_HEIGHT, IMG_WIDTH))
        shadowing_maps.append(shadow)

    # -------------------------------------------------------------------------
    # STEP 3: Calculate coverage for each base station
    # -------------------------------------------------------------------------

    # Create a boolean mask for each BS's coverage area
    coverage_masks = [np.zeros((IMG_HEIGHT, IMG_WIDTH), dtype=bool)
                      for _ in range(NUM_BASE_STATIONS)]

    print(f"\nCalculating coverage (this may take a moment)...")

    for bs_idx, (bs_x, bs_y) in enumerate(base_stations):
        covered_count = 0

        # Check every outdoor pixel
        for py, px in outdoor_pixels:
            # Convert pixel to meters
            pt_x, pt_y = pixels_to_meters(px, py)

            # Calculate distance from base station to this point
            distance = np.sqrt((pt_x - bs_x)**2 + (pt_y - bs_y)**2)
            distance = max(distance, 1.0)  # Avoid log(0) at BS location

            # Quick check: skip if definitely out of range
            if distance > max_range:
                continue

            # Calculate received signal strength
            # Path Loss = Free Space Path Loss + Random Shadowing
            fspl = free_space_path_loss(distance)
            shadowing = shadowing_maps[bs_idx][py, px]
            total_path_loss = fspl + shadowing

            # Received power = Transmit power - Path loss
            received_power_dbm = TX_POWER_DBM - total_path_loss

            # SNR = Received power - Noise floor
            snr_db = received_power_dbm - NOISE_DBM

            # Check if SNR meets threshold
            if snr_db < SNR_THRESHOLD_DB:
                continue

            # Check line-of-sight (most expensive check, do last)
            if has_line_of_sight(bs_x, bs_y, pt_x, pt_y):
                coverage_masks[bs_idx][py, px] = True
                covered_count += 1

        print(f"  BS {bs_idx+1}: covers {covered_count} pixels")

    # -------------------------------------------------------------------------
    # STEP 4: Create visualization
    # -------------------------------------------------------------------------

    print(f"\nGenerating visualization...")

    # Colors for each base station (RGB values)
    colors_rgb = [
        (1.0, 0.0, 0.0),    # BS 1: Red
        (0.0, 1.0, 0.0),    # BS 2: Green
        (0.0, 0.0, 1.0),    # BS 3: Blue
        (0.0, 1.0, 1.0),    # BS 4: Cyan
        (1.0, 0.0, 1.0),    # BS 5: Magenta
        (1.0, 1.0, 0.0),    # BS 6: Yellow
    ]

    # Start with white background, gray buildings
    output_img = np.ones((IMG_HEIGHT, IMG_WIDTH, 3))
    output_img[building_mask] = [0.3, 0.3, 0.3]

    # Transparency for color blending (lower = more transparent)
    alpha = 0.35

    # Blend coverage colors onto the image
    # Where multiple BSs overlap, colors will mix
    for py, px in outdoor_pixels:
        # Find all BSs that cover this pixel
        covering_bs = [i for i in range(NUM_BASE_STATIONS) if coverage_masks[i][py, px]]

        if len(covering_bs) == 0:
            continue  # No coverage, keep white

        # Blend colors from all covering BSs
        blended = np.array([1.0, 1.0, 1.0])  # Start with white
        for bs_idx in covering_bs:
            color = np.array(colors_rgb[bs_idx])
            blended = alpha * color + (1 - alpha) * blended

        output_img[py, px] = np.clip(blended, 0, 1)

    # Draw base station markers
    for bs_idx, (bs_x, bs_y) in enumerate(base_stations):
        px, py = meters_to_pixels(bs_x, bs_y)

        # Draw colored square
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                if 0 <= py+dy < IMG_HEIGHT and 0 <= px+dx < IMG_WIDTH:
                    output_img[py+dy, px+dx] = colors_rgb[bs_idx]

        # Draw black border
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                if abs(dy) == 4 or abs(dx) == 4:
                    if 0 <= py+dy < IMG_HEIGHT and 0 <= px+dx < IMG_WIDTH:
                        output_img[py+dy, px+dx] = [0, 0, 0]

    # -------------------------------------------------------------------------
    # STEP 5: Display and save results
    # -------------------------------------------------------------------------

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(output_img)

    # Create legend
    legend_patches = [mpatches.Patch(color=colors_rgb[i], label=f'BS {i+1}')
                      for i in range(NUM_BASE_STATIONS)]
    ax.legend(handles=legend_patches, loc='upper right')

    ax.set_xlabel('X (pixels)')
    ax.set_ylabel('Y (pixels)')
    ax.set_title(f'USC Campus Coverage with Line-of-Sight Blocking\n'
                 f'(Tx={TX_POWER_DBM} dBm, Shadowing={SHADOW_STD_DB} dB)')

    plt.tight_layout()
    plt.savefig('output.png', dpi=150)
    print(f"\nSaved visualization to: output.png")
    plt.show()

    # Calculate and print total coverage statistics
    any_coverage = np.zeros((IMG_HEIGHT, IMG_WIDTH), dtype=bool)
    for mask in coverage_masks:
        any_coverage |= mask

    total_covered = np.sum(any_coverage & outdoor_mask)
    total_outdoor = len(outdoor_pixels)
    coverage_percent = 100 * total_covered / total_outdoor

    print(f"\n" + "=" * 60)
    print(f"RESULTS")
    print(f"=" * 60)
    print(f"Total outdoor pixels:  {total_outdoor}")
    print(f"Covered pixels:        {total_covered}")
    print(f"Coverage percentage:   {coverage_percent:.1f}%")
    print(f"=" * 60)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    run_coverage_simulation()
