# Cybersecurity-Game

This repository contains a minimal prototype for an educational cyber-defense strategy game inspired by _Plague Inc._. The current build visualizes a simplified global device network where a malware outbreak spreads over time.

## Features

- Simplified world map with labeled regions.
- ~3,000 device nodes distributed according to rough population density.
- Each node tracks device type and infection state.
- Infection begins from a single node and propagates across nearby, similar devices every update tick.
- Heads-up display shows secure vs. infected device counts.

## Requirements

- Python 3.9+
- [pygame](https://www.pygame.org/) (`pip install pygame`)

## Running the prototype

```bash
python3 main.py
```

Close the window or press `Alt+F4`/`Cmd+W` to quit the simulation.

## Next steps

Future iterations can add defensive mechanics such as patch deployment, firewalls, or player-triggered scans. The current code base is organized so that additional node states and actions can be layered onto the existing update loop.
