#!/usr/bin/env python3
"""
Minimal 2D cyber infection simulation prototype.

This script renders a simplified world map populated with thousands of device
nodes. A single node starts infected and the virus spreads across the network
according to proximity and device similarity rules.

Controls:
    • Close the window to exit.

Requirements:
    • Python 3.9+
    • pygame (``pip install pygame``)
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import pygame

# Simulation configuration --------------------------------------------------
SEED = 42
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
NODE_COUNT = 3000
CONNECTION_RADIUS = 42  # pixels
UPDATE_INTERVAL = 0.6  # seconds between infection ticks
MAX_INFECTION_ATTEMPTS = 4
BACKGROUND_COLOR = (13, 21, 34)
INFECTED_COLOR = (222, 70, 70)
SECURE_COLOR = (70, 200, 120)
VULNERABLE_COLOR = (240, 208, 96)
NODE_RADIUS = 3

NODE_TYPE_DISTRIBUTION: Dict[str, float] = {
    "phone": 0.35,
    "computer": 0.3,
    "iot": 0.2,
    "server": 0.15,
}

# Major population regions with approximate bounding boxes on the map.
# Each region gets a share of nodes proportional to its weight.
REGIONS: Sequence[Tuple[str, Tuple[int, int, int, int], float]] = (
    ("North America", (150, 120, 520, 360), 0.13),
    ("South America", (320, 360, 500, 650), 0.07),
    ("Europe", (540, 120, 720, 280), 0.12),
    ("Africa", (560, 280, 740, 600), 0.15),
    ("Middle East", (720, 240, 860, 360), 0.07),
    ("Russia", (640, 60, 1000, 220), 0.08),
    ("South Asia", (840, 300, 1080, 520), 0.16),
    ("East Asia", (980, 220, 1210, 460), 0.17),
    ("Southeast Asia", (980, 420, 1200, 640), 0.03),
    ("Oceania", (1020, 520, 1240, 700), 0.02),
)


@dataclass(slots=True)
class Node:
    """Represents a single device in the network."""

    x: float
    y: float
    device_type: str
    state: str = "secure"


def seeded_random_choice(rng: random.Random, distribution: Dict[str, float]) -> str:
    roll = rng.random()
    cumulative = 0.0
    for key, weight in distribution.items():
        cumulative += weight
        if roll <= cumulative:
            return key
    return next(reversed(distribution))


def generate_nodes(rng: random.Random) -> List[Node]:
    nodes: List[Node] = []
    total_weight = sum(weight for _, _, weight in REGIONS)

    assigned = 0
    for region_name, (x0, y0, x1, y1), weight in REGIONS:
        target = int(NODE_COUNT * (weight / total_weight))
        for _ in range(target):
            x = rng.uniform(x0, x1)
            y = rng.uniform(y0, y1)
            device_type = seeded_random_choice(rng, NODE_TYPE_DISTRIBUTION)
            nodes.append(Node(x=x, y=y, device_type=device_type))
        assigned += target

    # Distribute any remaining nodes randomly within landmass bounds.
    remaining = NODE_COUNT - assigned
    catch_all_bounds = (200, 160, 1160, 660)
    for _ in range(remaining):
        x = rng.uniform(catch_all_bounds[0], catch_all_bounds[2])
        y = rng.uniform(catch_all_bounds[1], catch_all_bounds[3])
        device_type = seeded_random_choice(rng, NODE_TYPE_DISTRIBUTION)
        nodes.append(Node(x=x, y=y, device_type=device_type))

    return nodes


def build_spatial_index(nodes: Sequence[Node], radius: float) -> Dict[Tuple[int, int], List[int]]:
    cell_size = radius
    grid: Dict[Tuple[int, int], List[int]] = {}
    for idx, node in enumerate(nodes):
        cell = int(node.x // cell_size), int(node.y // cell_size)
        grid.setdefault(cell, []).append(idx)
    return grid


def build_neighbor_lists(nodes: Sequence[Node], radius: float) -> List[List[int]]:
    grid = build_spatial_index(nodes, radius)
    cell_size = radius
    neighbor_lists: List[List[int]] = [[] for _ in nodes]

    for idx, node in enumerate(nodes):
        cx, cy = int(node.x // cell_size), int(node.y // cell_size)
        nearby: List[int] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cell = (cx + dx, cy + dy)
                nearby.extend(grid.get(cell, []))
        for neighbor_idx in nearby:
            if neighbor_idx == idx:
                continue
            neighbor = nodes[neighbor_idx]
            dist = math.hypot(node.x - neighbor.x, node.y - neighbor.y)
            if dist <= radius:
                neighbor_lists[idx].append(neighbor_idx)
        neighbor_lists[idx] = sorted(set(neighbor_lists[idx]))

    return neighbor_lists


def infection_probability(source: Node, target: Node, distance: float) -> float:
    # Base chance of infection.
    base = 0.05

    # Similar device types share vulnerabilities.
    if source.device_type == target.device_type:
        base += 0.12
    else:
        # Phones and IoT devices are both lightweight endpoints.
        light_devices = {"phone", "iot"}
        heavy_devices = {"computer", "server"}
        if (
            source.device_type in light_devices
            and target.device_type in light_devices
        ) or (
            source.device_type in heavy_devices
            and target.device_type in heavy_devices
        ):
            base += 0.05

    # Closer nodes are more likely to be connected.
    distance_factor = max(0.0, 1.0 - distance / CONNECTION_RADIUS)
    base += 0.4 * distance_factor

    return min(0.95, base)


def update_infections(
    rng: random.Random, nodes: List[Node], neighbors: Sequence[Sequence[int]]
) -> None:
    newly_infected: List[int] = []
    for idx, node in enumerate(nodes):
        if node.state != "infected":
            continue
        neighbor_indices = neighbors[idx]
        if not neighbor_indices:
            continue

        attempts = min(len(neighbor_indices), MAX_INFECTION_ATTEMPTS)
        targets = rng.sample(neighbor_indices, attempts)
        for target_idx in targets:
            target = nodes[target_idx]
            if target.state == "infected":
                continue
            distance = math.hypot(node.x - target.x, node.y - target.y)
            chance = infection_probability(node, target, distance)
            if rng.random() < chance:
                newly_infected.append(target_idx)

    for idx in set(newly_infected):
        nodes[idx].state = "infected"


def draw_background(surface: pygame.Surface) -> None:
    surface.fill(BACKGROUND_COLOR)

    # Continents drawn as simple polygons for visual context.
    continent_color = (30, 60, 96)
    pygame.draw.polygon(
        surface,
        continent_color,
        [(120, 100), (520, 100), (480, 360), (160, 360)],
    )  # North America
    pygame.draw.polygon(
        surface,
        continent_color,
        [(320, 360), (460, 340), (540, 640), (360, 700)],
    )  # South America
    pygame.draw.polygon(
        surface,
        continent_color,
        [(520, 120), (840, 120), (780, 320), (560, 320)],
    )  # Europe / Middle East
    pygame.draw.polygon(
        surface,
        continent_color,
        [(560, 320), (780, 320), (820, 640), (620, 640)],
    )  # Africa
    pygame.draw.polygon(
        surface,
        continent_color,
        [(780, 160), (1180, 180), (1200, 480), (820, 420)],
    )  # Asia
    pygame.draw.polygon(
        surface,
        continent_color,
        [(960, 480), (1200, 540), (1160, 700), (980, 660)],
    )  # Oceania


def draw_labels(surface: pygame.Surface, font: pygame.font.Font) -> None:
    label_color = (180, 200, 220)
    labels = (
        ("North America", (260, 140)),
        ("South America", (380, 460)),
        ("Europe", (620, 160)),
        ("Africa", (640, 420)),
        ("Middle East", (760, 270)),
        ("Russia", (780, 140)),
        ("South Asia", (900, 360)),
        ("East Asia", (1040, 320)),
        ("SE Asia", (1030, 500)),
        ("Oceania", (1080, 600)),
    )
    for text, position in labels:
        label_surface = font.render(text, True, label_color)
        surface.blit(label_surface, position)


def draw_nodes(surface: pygame.Surface, nodes: Sequence[Node]) -> None:
    for node in nodes:
        if node.state == "infected":
            color = INFECTED_COLOR
        elif node.state == "vulnerable":
            color = VULNERABLE_COLOR
        else:
            color = SECURE_COLOR
        pygame.draw.circle(surface, color, (int(node.x), int(node.y)), NODE_RADIUS)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Cyber Defense Prototype")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    rng = random.Random(SEED)

    nodes = generate_nodes(rng)
    neighbors = build_neighbor_lists(nodes, CONNECTION_RADIUS)

    # Infect a single random node to start the outbreak.
    patient_zero = rng.randrange(len(nodes))
    nodes[patient_zero].state = "infected"

    font = pygame.font.SysFont("arial", 18)
    hud_font = pygame.font.SysFont("arial", 22)

    time_since_update = 0.0
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        time_since_update += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if time_since_update >= UPDATE_INTERVAL:
            update_infections(rng, nodes, neighbors)
            time_since_update = 0.0

        draw_background(screen)
        draw_labels(screen, font)
        draw_nodes(screen, nodes)

        infected_count = sum(1 for node in nodes if node.state == "infected")
        secure_count = len(nodes) - infected_count
        hud_text = f"Secure: {secure_count}  Infected: {infected_count}"
        hud_surface = hud_font.render(hud_text, True, (220, 230, 240))
        screen.blit(hud_surface, (20, 20))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
