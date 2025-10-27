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
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import pygame

from map_polygons import LAND_POLYGONS

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
MAP_IMAGE_PATH = Path("assets/world_map.png")

NODE_TYPE_DISTRIBUTION: Dict[str, float] = {
    "phone": 0.35,
    "computer": 0.3,
    "iot": 0.2,
    "server": 0.15,
}

# Major population hubs used for weighted sampling when seeding devices.
@dataclass(frozen=True)
class PopulationCenter:
    name: str
    latitude: float
    longitude: float
    weight: float
    lat_spread: float = 3.0
    lon_spread: float = 5.0


# Weighted list of major population hubs used to seed device placement. The
# spreads are in degrees and keep the jitter anchored to recognizable regions.
POPULATION_CENTERS: Sequence[PopulationCenter] = (
    # North America
    PopulationCenter("US East Coast", 40.0, -74.0, 0.055, lat_spread=3.5, lon_spread=4.5),
    PopulationCenter("US West Coast", 37.5, -122.0, 0.032, lat_spread=3.0, lon_spread=4.0),
    PopulationCenter("US Midwest", 41.5, -88.0, 0.028, lat_spread=3.0, lon_spread=4.0),
    PopulationCenter("US South", 33.0, -84.0, 0.025, lat_spread=3.0, lon_spread=4.0),
    PopulationCenter("Canada East", 46.5, -71.0, 0.018, lat_spread=3.0, lon_spread=6.0),
    PopulationCenter("Canada West", 53.0, -113.0, 0.014, lat_spread=4.0, lon_spread=5.0),
    PopulationCenter("Mexico City", 19.4, -99.1, 0.022, lat_spread=2.5, lon_spread=3.5),
    PopulationCenter("Central America", 14.3, -90.5, 0.012, lat_spread=2.0, lon_spread=3.0),
    # South America
    PopulationCenter("Brazil Southeast", -23.5, -46.6, 0.04, lat_spread=3.0, lon_spread=4.0),
    PopulationCenter("Brazil Northeast", -8.0, -34.9, 0.018, lat_spread=3.0, lon_spread=4.0),
    PopulationCenter("Argentina", -34.6, -58.4, 0.017, lat_spread=3.0, lon_spread=4.0),
    PopulationCenter("Peru", -12.0, -77.0, 0.015, lat_spread=2.5, lon_spread=3.5),
    PopulationCenter("Colombia", 4.6, -74.1, 0.015, lat_spread=2.5, lon_spread=3.5),
    # Europe
    PopulationCenter("UK", 53.0, -1.5, 0.028, lat_spread=3.0, lon_spread=3.0),
    PopulationCenter("France / Benelux", 49.5, 2.0, 0.034, lat_spread=3.0, lon_spread=3.0),
    PopulationCenter("Central Europe", 48.0, 16.0, 0.034, lat_spread=3.0, lon_spread=3.0),
    PopulationCenter("Iberia", 40.0, -3.0, 0.022, lat_spread=3.0, lon_spread=3.0),
    PopulationCenter("Italy", 42.5, 12.5, 0.022, lat_spread=2.5, lon_spread=2.5),
    PopulationCenter("Eastern Europe", 52.0, 20.0, 0.03, lat_spread=3.0, lon_spread=3.0),
    PopulationCenter("Scandinavia", 59.5, 18.0, 0.015, lat_spread=4.0, lon_spread=4.0),
    PopulationCenter("European Russia", 56.0, 38.0, 0.032, lat_spread=3.5, lon_spread=6.0),
    # Africa & Middle East
    PopulationCenter("North Africa", 31.0, 31.0, 0.032, lat_spread=3.0, lon_spread=4.0),
    PopulationCenter("West Africa", 6.0, -1.5, 0.028, lat_spread=3.0, lon_spread=4.0),
    PopulationCenter("Nigeria", 9.0, 7.4, 0.026, lat_spread=3.0, lon_spread=4.0),
    PopulationCenter("East Africa", 1.0, 37.0, 0.027, lat_spread=3.5, lon_spread=4.0),
    PopulationCenter("Ethiopia", 9.0, 39.0, 0.016, lat_spread=2.5, lon_spread=3.0),
    PopulationCenter("Southern Africa", -26.0, 28.0, 0.026, lat_spread=3.5, lon_spread=4.5),
    PopulationCenter("Turkey", 39.0, 35.0, 0.019, lat_spread=2.5, lon_spread=3.0),
    PopulationCenter("Persian Gulf", 25.0, 55.0, 0.015, lat_spread=2.5, lon_spread=3.5),
    PopulationCenter("Iran", 35.7, 52.3, 0.02, lat_spread=3.0, lon_spread=3.5),
    # South & Central Asia
    PopulationCenter("Pakistan", 31.5, 74.3, 0.028, lat_spread=3.0, lon_spread=3.0),
    PopulationCenter("North India", 27.0, 77.0, 0.065, lat_spread=3.0, lon_spread=3.0),
    PopulationCenter("West India", 19.0, 73.0, 0.055, lat_spread=2.5, lon_spread=3.0),
    PopulationCenter("South India", 13.0, 80.0, 0.04, lat_spread=2.5, lon_spread=3.0),
    PopulationCenter("Bangladesh", 23.7, 90.3, 0.026, lat_spread=2.0, lon_spread=2.5),
    PopulationCenter("Sri Lanka", 7.3, 80.7, 0.006, lat_spread=1.2, lon_spread=1.2),
    PopulationCenter("Nepal", 27.7, 85.3, 0.01, lat_spread=1.8, lon_spread=2.0),
    PopulationCenter("Myanmar", 18.0, 96.0, 0.018, lat_spread=3.0, lon_spread=3.5),
    # East Asia
    PopulationCenter("Central China", 34.0, 113.0, 0.08, lat_spread=3.5, lon_spread=4.5),
    PopulationCenter("Northern China", 40.5, 116.5, 0.06, lat_spread=3.0, lon_spread=3.5),
    PopulationCenter("Southern China", 23.5, 113.0, 0.07, lat_spread=3.0, lon_spread=3.5),
    PopulationCenter("Sichuan Basin", 30.5, 104.0, 0.045, lat_spread=3.0, lon_spread=3.0),
    PopulationCenter("Northeast China", 44.0, 125.0, 0.03, lat_spread=3.0, lon_spread=3.5),
    PopulationCenter("Korean Peninsula", 37.5, 127.0, 0.028, lat_spread=2.5, lon_spread=2.5),
    PopulationCenter("Japan", 35.5, 138.5, 0.032, lat_spread=3.0, lon_spread=3.0),
    PopulationCenter("Taiwan", 24.0, 121.0, 0.01, lat_spread=1.8, lon_spread=2.0),
    PopulationCenter("Hong Kong / Pearl River", 22.8, 114.2, 0.018, lat_spread=1.8, lon_spread=2.2),
    # Southeast Asia & Oceania
    PopulationCenter("Vietnam", 16.0, 107.0, 0.022, lat_spread=3.0, lon_spread=3.0),
    PopulationCenter("Thailand", 13.5, 101.0, 0.018, lat_spread=2.5, lon_spread=2.5),
    PopulationCenter("Malaysia / Singapore", 3.0, 101.5, 0.016, lat_spread=2.0, lon_spread=2.5),
    PopulationCenter("Indonesia West", -5.0, 106.0, 0.028, lat_spread=3.0, lon_spread=4.0),
    PopulationCenter("Indonesia East", -3.0, 121.0, 0.02, lat_spread=3.0, lon_spread=4.0),
    PopulationCenter("Philippines", 14.5, 121.0, 0.022, lat_spread=2.5, lon_spread=3.0),
    PopulationCenter("New Guinea", -4.5, 144.0, 0.012, lat_spread=3.0, lon_spread=3.5),
    PopulationCenter("Australia East", -27.0, 134.0, 0.02, lat_spread=4.0, lon_spread=5.0),
    PopulationCenter("Australia West", -31.5, 118.0, 0.01, lat_spread=4.0, lon_spread=5.0),
    PopulationCenter("New Zealand", -41.0, 174.0, 0.006, lat_spread=2.5, lon_spread=3.0),
)

POPULATION_WEIGHT_TOTAL = sum(center.weight for center in POPULATION_CENTERS)


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


def _point_in_polygon(lon: float, lat: float, polygon: Sequence[Tuple[float, float]]) -> bool:
    inside = False
    x, y = lon, lat
    for i in range(len(polygon)):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % len(polygon)]
        if (y1 > y) == (y2 > y):
            continue
        denominator = y2 - y1
        if denominator == 0:
            continue
        slope = (x2 - x1) / denominator
        intersection_x = slope * (y - y1) + x1
        if x < intersection_x:
            inside = not inside
    return inside


def is_on_land(lon: float, lat: float) -> bool:
    for polygon in LAND_POLYGONS:
        if _point_in_polygon(lon, lat, polygon):
            return True
    return False


def choose_population_center(rng: random.Random) -> PopulationCenter:
    roll = rng.random() * POPULATION_WEIGHT_TOTAL
    cumulative = 0.0
    for center in POPULATION_CENTERS:
        cumulative += center.weight
        if roll <= cumulative:
            return center
    return POPULATION_CENTERS[-1]


@dataclass(frozen=True)
class Projection:
    map_width: float
    map_height: float
    scale: float
    offset_x: float
    offset_y: float

    def to_screen(self, lon: float, lat: float) -> Tuple[float, float]:
        x = (lon + 180.0) / 360.0 * self.map_width * self.scale + self.offset_x
        y = (1.0 - (lat + 90.0) / 180.0) * self.map_height * self.scale + self.offset_y
        return x, y


def generate_nodes(rng: random.Random, projection: Projection) -> List[Node]:
    nodes: List[Node] = []

    attempts = 0
    while len(nodes) < NODE_COUNT:
        center = choose_population_center(rng)
        lat = rng.gauss(center.latitude, center.lat_spread)
        lon = rng.gauss(center.longitude, center.lon_spread)
        attempts += 1
        if not is_on_land(lon, lat):
            if attempts > NODE_COUNT * 10:
                # Fallback in case of pathological polygons.
                lon = max(-179.0, min(179.0, lon))
                lat = max(-85.0, min(85.0, lat))
                if not is_on_land(lon, lat):
                    continue
            else:
                continue

        x, y = projection.to_screen(lon, lat)
        device_type = seeded_random_choice(rng, NODE_TYPE_DISTRIBUTION)
        nodes.append(Node(x=x, y=y, device_type=device_type))
        attempts = 0

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


LABEL_SPECS: Sequence[Tuple[str, float, float, Tuple[int, int]]] = (
    ("North America", 54.0, -110.0, (-80, -30)),
    ("South America", -20.0, -60.0, (-70, 0)),
    ("Europe", 54.0, 15.0, (-40, -40)),
    ("Africa", 10.0, 20.0, (-30, 0)),
    ("Middle East", 27.0, 45.0, (-50, -10)),
    ("Russia", 63.0, 90.0, (-40, -50)),
    ("South Asia", 22.0, 78.0, (-60, 0)),
    ("East Asia", 33.0, 113.0, (-60, -10)),
    ("SE Asia", 10.0, 104.0, (-40, 10)),
    ("Oceania", -18.0, 135.0, (-60, 10)),
)


def draw_labels(surface: pygame.Surface, font: pygame.font.Font, projection: Projection) -> None:
    label_color = (200, 220, 240)
    for text, lat, lon, (dx, dy) in LABEL_SPECS:
        x, y = projection.to_screen(lon, lat)
        label_surface = font.render(text, True, label_color)
        rect = label_surface.get_rect()
        rect.center = (int(x) + dx, int(y) + dy)
        surface.blit(label_surface, rect)


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

    if not MAP_IMAGE_PATH.exists():
        raise FileNotFoundError(
            f"World map image not found at {MAP_IMAGE_PATH.resolve()}"
        )

    background_image = pygame.image.load(str(MAP_IMAGE_PATH)).convert()
    map_width, map_height = background_image.get_size()
    scale = min(WINDOW_WIDTH / map_width, WINDOW_HEIGHT / map_height)
    scaled_size = (int(map_width * scale), int(map_height * scale))
    background_surface = pygame.transform.smoothscale(background_image, scaled_size)
    offset_x = (WINDOW_WIDTH - scaled_size[0]) / 2
    offset_y = (WINDOW_HEIGHT - scaled_size[1]) / 2
    background_rect = background_surface.get_rect()
    background_rect.topleft = (round(offset_x), round(offset_y))

    rng = random.Random(SEED)

    projection = Projection(
        map_width=map_width,
        map_height=map_height,
        scale=scale,
        offset_x=background_rect.x,
        offset_y=background_rect.y,
    )

    nodes = generate_nodes(rng, projection)
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

        screen.fill(BACKGROUND_COLOR)
        screen.blit(background_surface, background_rect)
        draw_labels(screen, font, projection)
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
