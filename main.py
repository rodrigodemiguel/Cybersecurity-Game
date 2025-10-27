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
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import pygame

from map_polygons import LAND_POLYGONS

# Simulation configuration --------------------------------------------------
SEED = 42
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
NODE_COUNT = 50
CONNECTION_RADIUS = 120  # pixels
UPDATE_INTERVAL = 0.6  # seconds between infection ticks
MAX_INFECTION_ATTEMPTS = 4
BACKGROUND_COLOR = (13, 21, 34)
INFECTED_COLOR = (222, 70, 70)
SECURE_COLOR = (70, 200, 120)
VULNERABLE_COLOR = (240, 208, 96)
NODE_RADIUS = 5
MENU_HEIGHT = max(24, int(WINDOW_HEIGHT * 0.03))
UPGRADE_STARTING_POINTS = 10
UPGRADE_NODE_RADIUS = 28
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


CONNECTIVITY_OPTIONS: Dict[str, Tuple[str, ...]] = {
    "phone": ("Wi-Fi", "LTE", "Bluetooth"),
    "computer": ("Ethernet", "Wi-Fi", "SSH"),
    "iot": ("Wi-Fi", "LoRa", "Bluetooth", "Zigbee"),
    "server": ("Ethernet", "SSH", "VPN"),
}

NODE_ADJECTIVES: Tuple[str, ...] = (
    "Azure",
    "Crimson",
    "Ivory",
    "Onyx",
    "Silver",
    "Golden",
    "Umber",
    "Verdant",
    "Cobalt",
    "Amber",
)

NODE_NOUNS: Tuple[str, ...] = (
    "Sentinel",
    "Relay",
    "Anchor",
    "Beacon",
    "Array",
    "Node",
    "Matrix",
    "Hub",
    "Gate",
    "Bastion",
)

NODE_TRAITS: Tuple[str, ...] = (
    "Proactive phishing detection routines",
    "Legacy firmware awaiting a vendor patch",
    "Mission-critical analytics workload",
    "External-facing services hardened against scans",
    "Remote workforce access concentrator",
    "Edge compute platform aggregating IoT telemetry",
    "High-availability cluster guarding transactional data",
    "Development sandbox with relaxed policies",
    "Customer identity and access broker",
    "Automation controller for smart infrastructure",
)


def create_land_classifier(surface: pygame.Surface) -> Callable[[float, float], bool]:
    """Return a callable that tests whether a lat/lon pair maps to land."""

    pixels = pygame.surfarray.array3d(surface)
    try:
        alpha = pygame.surfarray.array_alpha(surface)
    except ValueError:
        alpha = None

    width, height = surface.get_size()

    def is_land_image(lon: float, lat: float) -> bool:
        x = (lon + 180.0) / 360.0 * (width - 1)
        y = (1.0 - (lat + 90.0) / 180.0) * (height - 1)
        ix = int(max(0, min(width - 1, x)))
        iy = int(max(0, min(height - 1, y)))

        r, g, b = pixels[ix, iy]
        brightness = (int(r) + int(g) + int(b)) / 3.0
        dominant_blue = int(b) - max(int(r), int(g)) > 24

        if alpha is not None and int(alpha[ix, iy]) < 32:
            return False
        if dominant_blue and b > 80:
            return False
        if brightness < 32:
            return False
        return True

    def combined(lon: float, lat: float) -> bool:
        return is_land_image(lon, lat) or is_on_land(lon, lat)

    return combined


def generate_node_metadata(
    rng: random.Random, idx: int, device_type: str, region_name: str
) -> Tuple[str, Tuple[str, ...], str]:
    adjective = NODE_ADJECTIVES[idx % len(NODE_ADJECTIVES)]
    noun = NODE_NOUNS[(idx * 3) % len(NODE_NOUNS)]
    label = f"{adjective} {noun} #{idx + 1}"

    possible_connectivity = CONNECTIVITY_OPTIONS[device_type]
    max_links = min(3, len(possible_connectivity))
    sample_count = rng.randint(1, max_links)
    connections = tuple(sorted(rng.sample(possible_connectivity, k=sample_count)))

    trait_index = (idx * 5 + rng.randint(0, len(NODE_TRAITS) - 1)) % len(NODE_TRAITS)
    trait = NODE_TRAITS[trait_index]
    summary = (
        f"Type: {device_type.title()}\n"
        f"Connectivity: {', '.join(connections)}\n"
        f"Region: {region_name}\n"
        f"Focus: {trait}"
    )

    return label, connections, summary


@dataclass(slots=True)
class Node:
    """Represents a single device in the network."""

    id: int
    x: float
    y: float
    device_type: str
    connectivity: Tuple[str, ...]
    label: str
    summary: str
    state: str = "secure"


@dataclass(frozen=True)
class UpgradeNode:
    id: str
    name: str
    description: str
    cost: int
    position: Tuple[int, int]
    prerequisites: Tuple[str, ...] = ()


@dataclass
class MenuButton:
    label: str
    key: str
    rect: pygame.Rect


UPGRADE_TREE: Tuple[UpgradeNode, ...] = (
    UpgradeNode(
        id="awareness",
        name="Awareness Campaigns",
        description="Launch engaging security awareness pushes to shrink phishing risk.",
        cost=1,
        position=(80, 70),
    ),
    UpgradeNode(
        id="patch_automation",
        name="Patch Automation",
        description="Automate change windows so fixes deploy quickly across fleets.",
        cost=1,
        position=(220, 70),
    ),
    UpgradeNode(
        id="segmentation",
        name="Network Segmentation",
        description="Carve defensive tiers to contain intrusions and limit lateral spread.",
        cost=2,
        position=(150, 160),
        prerequisites=("awareness", "patch_automation"),
    ),
    UpgradeNode(
        id="threat_hunting",
        name="Threat Hunting AI",
        description="Deploy adaptive analytics that surface stealthy adversary behavior.",
        cost=2,
        position=(70, 250),
        prerequisites=("segmentation",),
    ),
    UpgradeNode(
        id="deception",
        name="Deception Nets",
        description="Spin up believable decoys that waste attacker time and signal breaches.",
        cost=2,
        position=(230, 250),
        prerequisites=("segmentation",),
    ),
    UpgradeNode(
        id="resilience",
        name="Resilience Drills",
        description="Rehearse coordinated response so recovery is fast when incidents occur.",
        cost=3,
        position=(150, 340),
        prerequisites=("threat_hunting", "deception"),
    ),
)


def build_menu_buttons() -> List[MenuButton]:
    buttons: List[MenuButton] = []
    labels = (("Upgrades", "upgrades"), ("Virus Progress", "virus"), ("Settings", "settings"))
    button_width = WINDOW_WIDTH // len(labels)
    x = 0
    for index, (label, key) in enumerate(labels):
        width = button_width if index < len(labels) - 1 else WINDOW_WIDTH - x
        rect = pygame.Rect(x, 0, width, MENU_HEIGHT)
        buttons.append(MenuButton(label=label, key=key, rect=rect))
        x += width
    return buttons


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

    def to_image_pixels(self, lon: float, lat: float) -> Tuple[int, int]:
        x = (lon + 180.0) / 360.0 * (self.map_width - 1)
        y = (1.0 - (lat + 90.0) / 180.0) * (self.map_height - 1)
        return int(max(0, min(self.map_width - 1, x))), int(
            max(0, min(self.map_height - 1, y))
        )


def generate_nodes(
    rng: random.Random, projection: Projection, is_land: Callable[[float, float], bool]
) -> List[Node]:
    nodes: List[Node] = []

    attempts = 0
    while len(nodes) < NODE_COUNT:
        center = choose_population_center(rng)
        lat = rng.gauss(center.latitude, center.lat_spread)
        lon = rng.gauss(center.longitude, center.lon_spread)
        attempts += 1
        if not is_land(lon, lat):
            if attempts > NODE_COUNT * 10:
                # Fallback in case of pathological polygons.
                lon = max(-179.0, min(179.0, lon))
                lat = max(-85.0, min(85.0, lat))
                if not (is_on_land(lon, lat) or is_land(lon, lat)):
                    continue
            else:
                continue

        x, y = projection.to_screen(lon, lat)
        device_type = seeded_random_choice(rng, NODE_TYPE_DISTRIBUTION)
        label, connectivity, summary = generate_node_metadata(
            rng, len(nodes), device_type, center.name
        )
        nodes.append(
            Node(
                id=len(nodes),
                x=x,
                y=y,
                device_type=device_type,
                connectivity=connectivity,
                label=label,
                summary=summary,
            )
        )
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


def wrap_text_lines(text: str, width: int = 34) -> List[str]:
    if not text:
        return []
    return textwrap.wrap(text, width=width)


def draw_tooltip(
    surface: pygame.Surface,
    font: pygame.font.Font,
    lines: Sequence[str],
    position: Tuple[int, int],
) -> None:
    if not lines:
        return

    padding_x, padding_y = 10, 6
    rendered = [font.render(line, True, (230, 238, 255)) for line in lines]
    max_line_width = max((surface_line.get_width() for surface_line in rendered), default=0)
    width = max(120, max_line_width + padding_x * 2)
    height = sum(surface_line.get_height() for surface_line in rendered) + padding_y * 2

    x, y = position
    if x + width > WINDOW_WIDTH - 10:
        x = WINDOW_WIDTH - width - 10
    if y + height > WINDOW_HEIGHT - 10:
        y = WINDOW_HEIGHT - height - 10

    rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(surface, (20, 32, 48), rect, border_radius=8)
    pygame.draw.rect(surface, (80, 110, 150), rect, 2, border_radius=8)

    cursor_y = rect.y + padding_y
    for line_surface in rendered:
        surface.blit(line_surface, (rect.x + padding_x, cursor_y))
        cursor_y += line_surface.get_height()


def format_node_description(node: Node) -> List[str]:
    lines = [node.label, ""]
    lines.extend(node.summary.splitlines())
    lines.append(f"Status: {node.state.title()}")
    return lines


def find_node_under_point(nodes: Sequence[Node], pos: Tuple[int, int]) -> Optional[Node]:
    px, py = pos
    for node in nodes:
        if math.hypot(node.x - px, node.y - py) <= NODE_RADIUS + 6:
            return node
    return None


def draw_menu(surface: pygame.Surface, buttons: Sequence[MenuButton], active: Optional[str], font: pygame.font.Font) -> None:
    for button in buttons:
        base_color = (40, 58, 80)
        active_color = (76, 112, 160)
        color = active_color if button.key == active else base_color
        pygame.draw.rect(surface, color, button.rect)
        pygame.draw.rect(surface, (90, 130, 190), button.rect, 2)
        label_surface = font.render(button.label, True, (230, 238, 255))
        label_rect = label_surface.get_rect(center=button.rect.center)
        surface.blit(label_surface, label_rect)


def compute_upgrade_centers(panel_rect: pygame.Rect) -> Dict[str, Tuple[int, int]]:
    centers: Dict[str, Tuple[int, int]] = {}
    for node in UPGRADE_TREE:
        centers[node.id] = (
            panel_rect.x + node.position[0],
            panel_rect.y + node.position[1],
        )
    return centers


def draw_upgrade_panel(
    surface: pygame.Surface,
    panel_rect: pygame.Rect,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    upgrade_state: Dict[str, bool],
    upgrade_points: int,
    mouse_pos: Tuple[int, int],
) -> Optional[UpgradeNode]:
    pygame.draw.rect(surface, (18, 28, 45), panel_rect, border_radius=12)
    pygame.draw.rect(surface, (84, 116, 168), panel_rect, 2, border_radius=12)

    title_surface = font.render("Defense Upgrade Tree", True, (230, 238, 255))
    surface.blit(title_surface, (panel_rect.x + 16, panel_rect.y + 12))

    points_surface = small_font.render(
        f"Upgrade Points: {upgrade_points}", True, (196, 212, 240)
    )
    surface.blit(points_surface, (panel_rect.x + 16, panel_rect.y + 46))

    centers = compute_upgrade_centers(panel_rect)

    # Draw connections first so nodes overlay the lines.
    for node in UPGRADE_TREE:
        node_center = centers[node.id]
        for prereq in node.prerequisites:
            prereq_center = centers.get(prereq)
            if prereq_center:
                pygame.draw.line(surface, (60, 82, 120), prereq_center, node_center, 4)

    hovered: Optional[UpgradeNode] = None
    mouse_x, mouse_y = mouse_pos
    for node in UPGRADE_TREE:
        center_x, center_y = centers[node.id]
        purchased = upgrade_state.get(node.id, False)
        prerequisites_met = all(upgrade_state.get(req, False) for req in node.prerequisites)
        affordable = upgrade_points >= node.cost
        available = prerequisites_met and not purchased and affordable

        if purchased:
            fill_color = (88, 168, 112)
        elif available:
            fill_color = (86, 126, 208)
        elif prerequisites_met and not affordable:
            fill_color = (110, 96, 150)
        else:
            fill_color = (54, 62, 82)

        pygame.draw.circle(surface, fill_color, (center_x, center_y), UPGRADE_NODE_RADIUS)
        pygame.draw.circle(surface, (18, 28, 45), (center_x, center_y), UPGRADE_NODE_RADIUS, 3)

        name_lines = wrap_text_lines(node.name, width=14)
        line_height = small_font.get_linesize()
        total_height = line_height * len(name_lines)
        for index, line in enumerate(name_lines):
            line_surface = small_font.render(line, True, (240, 244, 255))
            text_y = int(center_y - total_height / 2 + index * line_height)
            line_rect = line_surface.get_rect(center=(center_x, text_y))
            surface.blit(line_surface, line_rect)

        cost_surface = small_font.render(f"{node.cost} pt", True, (200, 210, 240))
        cost_rect = cost_surface.get_rect(
            center=(center_x, int(center_y + UPGRADE_NODE_RADIUS - 10))
        )
        surface.blit(cost_surface, cost_rect)

        if math.hypot(mouse_x - center_x, mouse_y - center_y) <= UPGRADE_NODE_RADIUS:
            hovered = node

    return hovered


def get_upgrade_under_point(
    panel_rect: pygame.Rect, mouse_pos: Tuple[int, int]
) -> Optional[UpgradeNode]:
    centers = compute_upgrade_centers(panel_rect)
    mx, my = mouse_pos
    for node in UPGRADE_TREE:
        center = centers[node.id]
        if math.hypot(mx - center[0], my - center[1]) <= UPGRADE_NODE_RADIUS:
            return node
    return None


def can_purchase_upgrade(node: UpgradeNode, state: Dict[str, bool], points: int) -> bool:
    if state.get(node.id):
        return False
    if points < node.cost:
        return False
    return all(state.get(req, False) for req in node.prerequisites)


def draw_text_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    title: str,
    lines: Sequence[str],
    title_font: pygame.font.Font,
    body_font: pygame.font.Font,
) -> None:
    pygame.draw.rect(surface, (18, 28, 45), rect, border_radius=12)
    pygame.draw.rect(surface, (84, 116, 168), rect, 2, border_radius=12)

    title_surface = title_font.render(title, True, (230, 238, 255))
    surface.blit(title_surface, (rect.x + 16, rect.y + 12))

    y = rect.y + 52
    for line in lines:
        for chunk in wrap_text_lines(line, width=40):
            text_surface = body_font.render(chunk, True, (210, 222, 245))
            surface.blit(text_surface, (rect.x + 16, y))
            y += text_surface.get_height() + 2
        y += 6


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Cyber Defense Prototype")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    if not MAP_IMAGE_PATH.exists():
        raise FileNotFoundError(
            f"World map image not found at {MAP_IMAGE_PATH.resolve()}"
        )

    background_image = pygame.image.load(str(MAP_IMAGE_PATH)).convert_alpha()
    land_classifier = create_land_classifier(background_image)

    map_width, map_height = background_image.get_size()
    usable_height = WINDOW_HEIGHT - MENU_HEIGHT - 40
    scale = min(WINDOW_WIDTH / map_width, usable_height / map_height)
    scaled_size = (int(map_width * scale), int(map_height * scale))
    background_surface = pygame.transform.smoothscale(background_image, scaled_size)
    offset_x = (WINDOW_WIDTH - scaled_size[0]) / 2
    offset_y = MENU_HEIGHT + (WINDOW_HEIGHT - MENU_HEIGHT - scaled_size[1]) / 2
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

    nodes = generate_nodes(rng, projection, land_classifier)
    neighbors = build_neighbor_lists(nodes, CONNECTION_RADIUS)

    # Infect a single random node to start the outbreak.
    patient_zero = rng.randrange(len(nodes))
    nodes[patient_zero].state = "infected"

    label_font = pygame.font.SysFont("arial", 18)
    hud_font = pygame.font.SysFont("arial", 20)
    tooltip_font = pygame.font.SysFont("arial", 16)
    menu_font = pygame.font.SysFont("arial", max(18, int(MENU_HEIGHT * 0.6)))
    panel_title_font = pygame.font.SysFont("arial", 20)
    panel_body_font = pygame.font.SysFont("arial", 16)

    menu_buttons = build_menu_buttons()
    upgrade_state: Dict[str, bool] = {node.id: False for node in UPGRADE_TREE}
    upgrade_points = UPGRADE_STARTING_POINTS
    active_panel: Optional[str] = None

    panel_margin = 24
    panel_width = 340
    panel_rect = pygame.Rect(
        WINDOW_WIDTH - panel_width - panel_margin,
        MENU_HEIGHT + panel_margin,
        panel_width,
        WINDOW_HEIGHT - MENU_HEIGHT - panel_margin * 2,
    )

    time_since_update = 0.0
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        time_since_update += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos
                clicked_button = False
                for button in menu_buttons:
                    if button.rect.collidepoint(mouse_pos):
                        active_panel = None if active_panel == button.key else button.key
                        clicked_button = True
                        break

                if clicked_button:
                    continue

                if active_panel == "upgrades" and panel_rect.collidepoint(mouse_pos):
                    selected_upgrade = get_upgrade_under_point(panel_rect, mouse_pos)
                    if selected_upgrade and can_purchase_upgrade(
                        selected_upgrade, upgrade_state, upgrade_points
                    ):
                        upgrade_state[selected_upgrade.id] = True
                        upgrade_points -= selected_upgrade.cost

        if time_since_update >= UPDATE_INTERVAL:
            update_infections(rng, nodes, neighbors)
            time_since_update = 0.0

        screen.fill(BACKGROUND_COLOR)
        screen.blit(background_surface, background_rect)
        draw_labels(screen, label_font, projection)

        draw_nodes(screen, nodes)

        mouse_pos = pygame.mouse.get_pos()
        hovered_node = find_node_under_point(nodes, mouse_pos)

        if hovered_node:
            pygame.draw.circle(
                screen,
                (250, 250, 255),
                (int(hovered_node.x), int(hovered_node.y)),
                NODE_RADIUS + 4,
                2,
            )

        infected_count = sum(1 for node in nodes if node.state == "infected")
        secure_count = len(nodes) - infected_count
        integrity_percent = 100.0 * (secure_count / len(nodes))
        hud_text = (
            f"Secure: {secure_count}  Infected: {infected_count}  "
            f"Integrity: {integrity_percent:0.1f}%"
        )
        hud_surface = hud_font.render(hud_text, True, (220, 230, 240))
        screen.blit(hud_surface, (20, MENU_HEIGHT + 12))

        pygame.draw.rect(screen, (18, 26, 38), (0, 0, WINDOW_WIDTH, MENU_HEIGHT))
        draw_menu(screen, menu_buttons, active_panel, menu_font)

        hovered_upgrade: Optional[UpgradeNode] = None
        if active_panel == "upgrades":
            hovered_upgrade = draw_upgrade_panel(
                screen,
                panel_rect,
                panel_title_font,
                panel_body_font,
                upgrade_state,
                upgrade_points,
                mouse_pos,
            )
        elif active_panel == "virus":
            draw_text_panel(
                screen,
                panel_rect,
                "Virus Progress",
                [
                    f"Active infections: {infected_count} of {len(nodes)} devices",
                    f"Network integrity holding at {integrity_percent:0.1f}%.",
                    "The malware favors close, similar devices but can leap across",
                    "dense links. Defensive upgrades will mitigate spread in future builds.",
                ],
                panel_title_font,
                panel_body_font,
            )
        elif active_panel == "settings":
            draw_text_panel(
                screen,
                panel_rect,
                "Settings",
                [
                    "Audio, pacing, and colorblind accessibility controls will live here.",
                    "For now you can adjust simulation speed and device density directly",
                    "in the configuration constants at the top of main.py.",
                ],
                panel_title_font,
                panel_body_font,
            )

        if (
            hovered_node
            and not (
                active_panel == "upgrades" and panel_rect.collidepoint(mouse_pos)
            )
        ):
            draw_tooltip(
                screen,
                tooltip_font,
                format_node_description(hovered_node),
                (mouse_pos[0] + 16, mouse_pos[1] + 16),
            )

        if (
            hovered_upgrade
            and active_panel == "upgrades"
            and panel_rect.collidepoint(mouse_pos)
        ):
            tooltip_lines = [hovered_upgrade.name, ""]
            tooltip_lines.extend(
                wrap_text_lines(hovered_upgrade.description, width=38)
            )
            tooltip_lines.append(f"Cost: {hovered_upgrade.cost} point(s)")
            unlocked = upgrade_state.get(hovered_upgrade.id, False)
            prerequisites = (
                ", ".join(hovered_upgrade.prerequisites)
                if hovered_upgrade.prerequisites
                else "None"
            )
            tooltip_lines.append(f"Unlocked: {'Yes' if unlocked else 'No'}")
            tooltip_lines.append(f"Requires: {prerequisites}")
            draw_tooltip(
                screen,
                tooltip_font,
                tooltip_lines,
                (mouse_pos[0] + 16, mouse_pos[1] + 16),
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
