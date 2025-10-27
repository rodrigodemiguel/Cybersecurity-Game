# Assets Directory

Place the world map background image as `world_map.png` in this folder before running the simulation. The image should be a wide, equirectangular-projection map that aligns with the coordinates used by the simulator.

For best results, keep the oceans distinctly blue (or transparent) and the continents non-blue. The simulator samples pixel colors to ensure devices spawn on land, falling back to geometric land polygons only when the bitmap check fails.
