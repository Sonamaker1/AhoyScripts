from PIL import Image
import numpy as np

def edge_pad_image(input_path, output_path, iterations=8):
    img = Image.open(input_path).convert("RGBA")
    data = np.array(img)

    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]

    height, width = a.shape

    for _ in range(iterations):
        new_r, new_g, new_b, new_a = r.copy(), g.copy(), b.copy(), a.copy()

        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if a[y, x] == 0:  # only modify fully transparent pixels
                    neighbor_colors = []

                    for ny in range(y - 1, y + 2):
                        for nx in range(x - 1, x + 2):
                            if (nx, ny) == (x, y):
                                continue
                            if a[ny, nx] > 0:
                                neighbor_colors.append((r[ny, nx], g[ny, nx], b[ny, nx]))

                    if neighbor_colors:
                        avg_r = int(sum(c[0] for c in neighbor_colors) / len(neighbor_colors))
                        avg_g = int(sum(c[1] for c in neighbor_colors) / len(neighbor_colors))
                        avg_b = int(sum(c[2] for c in neighbor_colors) / len(neighbor_colors))

                        new_r[y, x] = avg_r
                        new_g[y, x] = avg_g
                        new_b[y, x] = avg_b
                        new_a[y, x] = 255  # make fully opaque

        r, g, b, a = new_r, new_g, new_b, new_a

    result = np.stack([r, g, b, a], axis=-1)
    Image.fromarray(result, mode="RGBA").save(output_path)
    print(f"Padded image saved to: {output_path}")

# Example usage
# edge_pad_image("input.png", "output_padded.png", iterations=8)
