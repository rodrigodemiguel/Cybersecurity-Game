# Cybersecurity-Game

This repository contains a minimal prototype for an educational cyber-defense strategy game inspired by _Plague Inc._. The current build visualizes a simplified global device network where a malware outbreak spreads over time.

## Features

- World map background supplied via `assets/world_map.png`, scaled beneath an on-screen navigation bar with regional labels.
- ~50 richly described device nodes sampled from weighted population hubs and validated against the background image so they remain on land.
- Each node exposes unique metadata (device class, connectivity mix, focus area) and displays it on hover.
- Infection begins from a single node and propagates across nearby, similar devices every update tick.
- Heads-up display tracks secure vs. infected counts alongside an estimated network integrity percentage.
- Top-level UI buttons open expandable panels, including an interactive upgrade skill tree with persistent unlocks.

## Requirements

- Python 3.9+
- [pygame](https://www.pygame.org/) (`pip install pygame`)
- World map background image saved as `assets/world_map.png` (add the file locally; it is not committed to the repo)

## Running the prototype

```bash
python3 main.py
```

Close the window or press `Alt+F4`/`Cmd+W` to quit the simulation.

## Next steps

Future iterations can add defensive mechanics such as patch deployment, firewalls, or player-triggered scans. The current code base is organized so that additional node states and actions can be layered onto the existing update loop.
