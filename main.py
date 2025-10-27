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
NODE_COUNT = 10
CONNECTION_RADIUS = 120  # pixels used when weighting infection odds
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

CONNECTION_SECURE_COLOR = (96, 186, 150)
CONNECTION_COMPROMISED_COLOR = (210, 84, 84)

@dataclass(frozen=True)
class ScenarioNodeSpec:
    label: str
    device_type: str
    latitude: float
    longitude: float
    region: str
    location: str
    role: str
    connectivity: Tuple[str, ...]
    lat_jitter: float = 0.35
    lon_jitter: float = 0.45


@dataclass(frozen=True)
class ScenarioConnectionSpec:
    source: int
    target: int
    medium: str
    description: str


SCENARIO_NODE_SPECS: Tuple[ScenarioNodeSpec, ...] = (
    ScenarioNodeSpec(
        label="Madrid Civic Phones",
        device_type="phone",
        latitude=40.4168,
        longitude=-3.7038,
        region="Spain",
        location="Madrid",
        role="Commuters checking transit updates through the municipal network.",
        connectivity=("Municipal Wi-Fi", "LTE", "Bluetooth"),
        lat_jitter=0.25,
        lon_jitter=0.35,
    ),
    ScenarioNodeSpec(
        label="Barcelona Smart Home Hub",
        device_type="iot",
        latitude=41.3874,
        longitude=2.1686,
        region="Spain",
        location="Barcelona",
        role="Controls apartment climate sensors and lighting automations.",
        connectivity=("Fiber Uplink", "Zigbee", "Wi-Fi"),
        lat_jitter=0.25,
        lon_jitter=0.35,
    ),
    ScenarioNodeSpec(
        label="Valencia Remote Offices",
        device_type="computer",
        latitude=39.4699,
        longitude=-0.3763,
        region="Spain",
        location="Valencia",
        role="Analysts tunneling into headquarters through managed VPN desks.",
        connectivity=("Enterprise Wi-Fi", "Ethernet", "VPN Client"),
        lat_jitter=0.25,
        lon_jitter=0.35,
    ),
    ScenarioNodeSpec(
        label="Seville Hospital IoT",
        device_type="iot",
        latitude=37.3891,
        longitude=-5.9845,
        region="Spain",
        location="Seville",
        role="Monitors critical care vitals from connected medical devices.",
        connectivity=("Secured Wi-Fi", "Bluetooth", "Zigbee"),
        lat_jitter=0.25,
        lon_jitter=0.35,
    ),
    ScenarioNodeSpec(
        label="Bilbao Esports PCs",
        device_type="computer",
        latitude=43.2630,
        longitude=-2.9350,
        region="Spain",
        location="Bilbao",
        role="High-end rigs scrimming via low-latency competitive ladders.",
        connectivity=("Fiber LAN", "Wi-Fi 6", "Bluetooth"),
        lat_jitter=0.25,
        lon_jitter=0.35,
    ),
    ScenarioNodeSpec(
        label="Lisbon Regional Data Center",
        device_type="server",
        latitude=38.7223,
        longitude=-9.1393,
        region="Portugal",
        location="Lisbon",
        role="Hosts SaaS workloads for Iberian customers with redundancy.",
        connectivity=("Fiber Backbone", "VPN Gateway", "SSH"),
        lat_jitter=0.25,
        lon_jitter=0.35,
    ),
    ScenarioNodeSpec(
        label="Frankfurt VPN Gateway",
        device_type="server",
        latitude=50.1109,
        longitude=8.6821,
        region="Germany",
        location="Frankfurt",
        role="Aggregates secure tunnels for European enterprise tenants.",
        connectivity=("MPLS Backbone", "VPN Concentrator", "SSH"),
        lat_jitter=0.3,
        lon_jitter=0.3,
    ),
    ScenarioNodeSpec(
        label="Dublin CDN Relay",
        device_type="server",
        latitude=53.3498,
        longitude=-6.2603,
        region="Ireland",
        location="Dublin",
        role="Caches media assets before distributing to Atlantic audiences.",
        connectivity=("Peered Fiber", "HTTPS", "SSH"),
        lat_jitter=0.3,
        lon_jitter=0.3,
    ),
    ScenarioNodeSpec(
        label="New York Trading Desk",
        device_type="computer",
        latitude=40.7128,
        longitude=-74.0060,
        region="United States",
        location="New York City",
        role="Risk models syncing with European exchanges pre-market.",
        connectivity=("Private Fiber", "VPN Client", "SSH"),
        lat_jitter=0.3,
        lon_jitter=0.3,
    ),
    ScenarioNodeSpec(
        label="Tokyo Streaming Cluster",
        device_type="server",
        latitude=35.6762,
        longitude=139.6503,
        region="Japan",
        location="Tokyo",
        role="Origin streaming nodes serving Asia-Pacific subscribers.",
        connectivity=("Transpacific Fiber", "HTTPS", "SSH"),
        lat_jitter=0.3,
        lon_jitter=0.3,
    ),
)


SCENARIO_CONNECTION_SPECS: Tuple[ScenarioConnectionSpec, ...] = (
    ScenarioConnectionSpec(
        source=0,
        target=1,
        medium="Municipal Wi-Fi Mesh",
        description="Madrid transit handsets join the Barcelona smart-home mesh when riders visit family.",
    ),
    ScenarioConnectionSpec(
        source=0,
        target=2,
        medium="VPN App",
        description="Phones pivot through the Valencia remote work gateway during after-hours check-ins.",
    ),
    ScenarioConnectionSpec(
        source=1,
        target=3,
        medium="Secure Zigbee Bridge",
        description="Hospital sensors receive environment updates from Barcelona apartment automation experts.",
    ),
    ScenarioConnectionSpec(
        source=1,
        target=5,
        medium="HTTPS Telemetry",
        description="Smart home dashboards forward anonymized metrics into Lisbon's SaaS analytics stack.",
    ),
    ScenarioConnectionSpec(
        source=2,
        target=5,
        medium="Enterprise Fiber",
        description="Valencia analysts push daily reports into the Lisbon data center's staging clusters.",
    ),
    ScenarioConnectionSpec(
        source=2,
        target=6,
        medium="Managed VPN",
        description="Remote employees rely on Frankfurt's hardened concentrator for privileged access.",
    ),
    ScenarioConnectionSpec(
        source=3,
        target=4,
        medium="Arena LAN",
        description="Regional esports scrims share match telemetry between Seville and Bilbao arenas.",
    ),
    ScenarioConnectionSpec(
        source=3,
        target=5,
        medium="Clinical Sync",
        description="Seville's hospital charts replicate nightly into Lisbon's redundant data stores.",
    ),
    ScenarioConnectionSpec(
        source=4,
        target=5,
        medium="Low-Latency Fiber",
        description="Bilbao gaming rigs warm their caches from Lisbon to reduce tournament lag.",
    ),
    ScenarioConnectionSpec(
        source=5,
        target=6,
        medium="EU Backbone Peering",
        description="Lisbon and Frankfurt exchange telemetry to balance demand across EU tenants.",
    ),
    ScenarioConnectionSpec(
        source=5,
        target=7,
        medium="Content Distribution",
        description="Lisbon's cache preloads media to Dublin before North American prime-time.",
    ),
    ScenarioConnectionSpec(
        source=6,
        target=8,
        medium="Risk Tunnel",
        description="Frankfurt analytics feed New York trading desks ahead of opening bells.",
    ),
    ScenarioConnectionSpec(
        source=6,
        target=9,
        medium="Threat Intel Share",
        description="Frankfurt relays credential stuffing indicators directly to Tokyo's SOC cluster.",
    ),
    ScenarioConnectionSpec(
        source=7,
        target=8,
        medium="CDN Bridge",
        description="Dublin mirrors highlight videos into Manhattan for overnight streaming bursts.",
    ),
    ScenarioConnectionSpec(
        source=8,
        target=9,
        medium="Peered VPN",
        description="New York and Tokyo coordinate DRM keys for simultaneous content launches.",
    ),
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


@dataclass(slots=True)
class Node:
    """Represents a single device in the network."""

    id: int
    x: float
    y: float
    latitude: float
    longitude: float
    region: str
    location: str
    device_type: str
    connectivity: Tuple[str, ...]
    label: str
    summary: str
    state: str = "secure"


@dataclass(slots=True)
class Connection:
    source: int
    target: int
    medium: str
    description: str


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
    if len(SCENARIO_NODE_SPECS) != NODE_COUNT:
        raise ValueError(
            "Scenario configuration mismatch: expected "
            f"{NODE_COUNT} nodes but described {len(SCENARIO_NODE_SPECS)}"
        )

    nodes: List[Node] = []
    for idx, spec in enumerate(SCENARIO_NODE_SPECS):
        lat = spec.latitude
        lon = spec.longitude
        for _ in range(40):
            jittered_lat = rng.uniform(
                spec.latitude - spec.lat_jitter, spec.latitude + spec.lat_jitter
            )
            jittered_lon = rng.uniform(
                spec.longitude - spec.lon_jitter, spec.longitude + spec.lon_jitter
            )
            if is_land(jittered_lon, jittered_lat):
                lat, lon = jittered_lat, jittered_lon
                break
        else:
            if not is_land(lon, lat) and not is_on_land(lon, lat):
                print(f"Could not verify land for {spec.label}, forcing placement.")

                # raise RuntimeError(
                    # f"Unable to place node '{spec.label}' on land using the provided map."
                # )

        x, y = projection.to_screen(lon, lat)
        summary = (
            f"Type: {spec.device_type.title()}\n"
            f"Location: {spec.location}, {spec.region}\n"
            f"Connectivity: {', '.join(spec.connectivity)}\n"
            f"Role: {spec.role}"
        )

        nodes.append(
            Node(
                id=idx,
                x=x,
                y=y,
                latitude=lat,
                longitude=lon,
                region=spec.region,
                location=spec.location,
                device_type=spec.device_type,
                connectivity=spec.connectivity,
                label=spec.label,
                summary=summary,
            )
        )

    return nodes


def build_connections() -> List[Connection]:
    connections: List[Connection] = []
    for spec in SCENARIO_CONNECTION_SPECS:
        connections.append(
            Connection(
                source=spec.source,
                target=spec.target,
                medium=spec.medium,
                description=spec.description,
            )
        )
    return connections


def build_neighbor_lists_from_connections(
    node_count: int, connections: Sequence[Connection]
) -> List[List[int]]:
    neighbor_lists: List[List[int]] = [[] for _ in range(node_count)]
    for connection in connections:
        neighbor_lists[connection.source].append(connection.target)
        neighbor_lists[connection.target].append(connection.source)
    for idx in range(node_count):
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


def draw_connections(
    surface: pygame.Surface,
    nodes: Sequence[Node],
    connections: Sequence[Connection],
    hovered: Optional[Connection] = None,
) -> None:
    for connection in connections:
        source = nodes[connection.source]
        target = nodes[connection.target]
        compromised = source.state == "infected" or target.state == "infected"
        color = CONNECTION_COMPROMISED_COLOR if compromised else CONNECTION_SECURE_COLOR
        width = 4 if hovered is connection else 2
        pygame.draw.line(
            surface,
            color,
            (int(source.x), int(source.y)),
            (int(target.x), int(target.y)),
            width,
        )


def wrap_text_lines(text: str, width: int = 34) -> List[str]:
    if not text:
        return []
    return textwrap.wrap(text, width=width)


def _point_to_segment_distance(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    abx = bx - ax
    aby = by - ay
    if abx == 0 and aby == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * abx + (py - ay) * aby) / (abx * abx + aby * aby)
    t = max(0.0, min(1.0, t))
    closest_x = ax + t * abx
    closest_y = ay + t * aby
    return math.hypot(px - closest_x, py - closest_y)


def find_connection_under_point(
    connections: Sequence[Connection],
    nodes: Sequence[Node],
    pos: Tuple[int, int],
    threshold: float = 6.0,
) -> Optional[Connection]:
    px, py = pos
    for connection in connections:
        source = nodes[connection.source]
        target = nodes[connection.target]
        distance = _point_to_segment_distance(px, py, source.x, source.y, target.x, target.y)
        if distance <= threshold:
            return connection
    return None


def format_connection_description(
    connection: Connection, nodes: Sequence[Node]
) -> List[str]:
    source = nodes[connection.source]
    target = nodes[connection.target]
    compromised = source.state == "infected" or target.state == "infected"
    status = "Compromised" if compromised else "Secure"
    lines = [f"{source.label} ↔ {target.label}", ""]
    lines.append(f"Medium: {connection.medium}")
    lines.extend(wrap_text_lines(f"Detail: {connection.description}", width=38))
    lines.append(f"Status: {status}")
    return lines


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
    connections = build_connections()
    neighbors = build_neighbor_lists_from_connections(len(nodes), connections)

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

        mouse_pos = pygame.mouse.get_pos()
        hovered_connection = find_connection_under_point(connections, nodes, mouse_pos)
        draw_connections(screen, nodes, connections, hovered_connection)
        draw_nodes(screen, nodes)

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

        elif (
            hovered_connection
            and not (
                active_panel == "upgrades" and panel_rect.collidepoint(mouse_pos)
            )
        ):
            draw_tooltip(
                screen,
                tooltip_font,
                format_connection_description(hovered_connection, nodes),
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
