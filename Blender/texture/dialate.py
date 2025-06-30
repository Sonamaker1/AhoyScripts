from PIL import Image
import numpy as np
import sys

def edge_pad_image(input_path, output_path, iterations=8):
    img = Image.open(input_path).convert("RGBA")
    data = np.array(img)

    # Split channels
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]

    # Create a mask of opaque pixels
    opaque_mask = a > 0

    for _ in range(iterations):
        new_r, new_g, new_b, new_a = r.copy(), g.copy(), b.copy(), a.copy()

        for y in range(1, data.shape[0] - 1):
            for x in range(1, data.shape[1] - 1):
                if a[y, x] == 0:
                    neighbors = [
                        (x-1, y), (x+1, y),
                        (x, y-1), (x, y+1),
                        (x-1, y-1), (x+1, y-1),
                        (x-1, y+1), (x+1, y+1),
                    ]
                    for nx, ny in neighbors:
                        if opaque_mask[ny, nx]:
                            new_r[y, x] = r[ny, nx]
                            new_g[y, x] = g[ny, nx]
                            new_b[y, x] = b[ny, nx]
                            new_a[y, x] = 255
                            break  # only grab one neighbor

        r, g, b, a = new_r, new_g, new_b, new_a
        opaque_mask = a > 0

    # Merge channels and save
    result = np.stack([r, g, b, a], axis=-1)
    Image.fromarray(result, mode="RGBA").save(output_path)
    print(f"Padded image saved to {output_path}")

# Example usage:
# edge_pad_image("input.png", "padded_output.png", iterations=8)
