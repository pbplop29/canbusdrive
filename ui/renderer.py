#!/usr/bin/env python3
import pygame
import pygame._freetype as ftext
from PIL import Image

SCENE_PATH = "resources/scene.png"
SCENE_NATIVE_WIDTH = 1024
SCENE_NATIVE_TILE_HEIGHT = 788  
SCENE_SCALE = 0.5

ROAD_LEFT_NATIVE = 369
ROAD_RIGHT_NATIVE = 695

LANE_PANEL_WIDTH = round(SCENE_NATIVE_WIDTH * SCENE_SCALE)
SCENE_TILE_HEIGHT = round(SCENE_NATIVE_TILE_HEIGHT * SCENE_SCALE)
ROAD_LEFT = ROAD_LEFT_NATIVE * SCENE_SCALE
ROAD_RIGHT = ROAD_RIGHT_NATIVE * SCENE_SCALE
ROAD_WIDTH = ROAD_RIGHT - ROAD_LEFT
ROAD_CENTER_X = (ROAD_LEFT + ROAD_RIGHT) / 2

WINDOW_HEIGHT = 720
WINDOW_SIZE = (LANE_PANEL_WIDTH, WINDOW_HEIGHT)
FPS = 60


CAR_PATH = "resources/car.png"
CAR_WIDTH = 40
CAR_HEIGHT = round(CAR_WIDTH * 779 / 417)
CAR_Y = WINDOW_HEIGHT - 240  # raised from -180 to leave room for the stacked HUD below it

MAX_STEERING_DEG = 90.0  # matches SteeringAngle's DBC range
MAX_LATERAL_OFFSET = ROAD_WIDTH / 2 - CAR_WIDTH / 2 - 8
STEER_SMOOTH_RATE = 6.0  # higher = snappier lateral response

SCROLL_GAIN = 3.0  # px/s of scroll per km/h -- tuned by feel, not physical

MAX_SPEED_DISPLAY = 200.0  # matches Powertrain ECU's MAX_SPEED_KMH
MAX_RPM_DISPLAY = 8000.0   # matches Powertrain ECU's MAX_RPM

# --- Stacked HUD: holographic speed/RPM arcs below the car ---
HOLO_CENTER_X = ROAD_CENTER_X
HOLO_TOP_BASE_Y = 590     # speed -- closer to the car
HOLO_BOTTOM_BASE_Y = 672  # RPM -- below that
HOLO_BULGE = 34
HOLO_HALF_WIDTH = 150
HOLO_SAMPLES = 40
HOLO_TEXT_GAP = 16   # value text distance above the bulge peak
HOLO_LABEL_GAP = 2   # unit-label text distance above the bulge peak
HOLO_SPEED_COLOR = (110, 235, 225)
HOLO_RPM_COLOR = (255, 176, 92)
HOLO_TRACK_ALPHA = 55
HOLO_GLOW_ALPHA = 70
HOLO_FILL_ALPHA = 220


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def load_scene_tile():
    img = Image.open(SCENE_PATH).convert("RGB")
    tile = img.crop((0, 0, img.width, SCENE_NATIVE_TILE_HEIGHT))
    surface = pygame.image.frombuffer(tile.tobytes(), tile.size, "RGB").convert()
    return pygame.transform.scale(surface, (LANE_PANEL_WIDTH, SCENE_TILE_HEIGHT))


def load_car_sprite():
    img = Image.open(CAR_PATH).convert("RGBA")
    surface = pygame.image.frombuffer(img.tobytes(), img.size, "RGBA").convert_alpha()
    return pygame.transform.scale(surface, (CAR_WIDTH, CAR_HEIGHT))


def draw_scene(surface, scene_tile, scroll_offset):
    start = (scroll_offset % SCENE_TILE_HEIGHT) - SCENE_TILE_HEIGHT
    y = start
    while y < WINDOW_HEIGHT:
        surface.blit(scene_tile, (0, y))
        y += SCENE_TILE_HEIGHT


def draw_car(surface, car_sprite, x, y):
    rect = car_sprite.get_rect(center=(x, y))
    surface.blit(car_sprite, rect)


def _holo_curve_points(center_x, base_y, t_lo, t_hi):
    points = []
    n = max(2, round(HOLO_SAMPLES * (t_hi - t_lo) / 2))
    for i in range(n + 1):
        t = t_lo + (t_hi - t_lo) * (i / n)
        x = center_x + t * HOLO_HALF_WIDTH
        y = base_y - HOLO_BULGE * (1 - t * t)
        points.append((x, y))
    return points


def draw_hologram(surface, font, center_x, base_y, value, max_value, color, label, unit=""):
    fraction = clamp(value / max_value, 0.0, 1.0)
    fill_t_end = -1.0 + 2.0 * fraction

    track_color = (*color, HOLO_TRACK_ALPHA)
    glow_color = (*color, HOLO_GLOW_ALPHA)
    fill_color = (*color, HOLO_FILL_ALPHA)

    # Dim background track spanning the full range.
    track_points = _holo_curve_points(center_x, base_y, -1.0, 1.0)
    pygame.draw.lines(surface, track_color, False, track_points, 2)

    if fraction > 0.01:
        fill_points = _holo_curve_points(center_x, base_y, -1.0, fill_t_end)
        # Soft glow underneath (thicker, dimmer), crisp line on top.
        pygame.draw.lines(surface, glow_color, False, fill_points, 7)
        pygame.draw.lines(surface, fill_color, False, fill_points, 2)

    # End caps, purely decorative HUD detail.
    for t in (-1.0, 1.0):
        cx, cy = _holo_curve_points(center_x, base_y, t, t)[0]
        pygame.draw.line(surface, track_color, (cx, cy - 6), (cx, cy + 6), 2)

    value_text = f"{value:03.0f}"
    value_surf, value_rect = font.render(value_text, (*color, 255), size=26)
    value_rect.center = (center_x, base_y - HOLO_BULGE - HOLO_TEXT_GAP)
    surface.blit(value_surf, value_rect)

    label_text = f"{label} · {unit}" if unit else label
    label_surf, label_rect = font.render(label_text, (*color, 200), size=12)
    label_rect.center = (center_x, base_y - HOLO_BULGE - HOLO_LABEL_GAP)
    surface.blit(label_surf, label_rect)


class GameRenderer:
    """Owns the pygame window and draws one frame per `render()` call.

    Callers (e.g. DashboardECU) just hand in the latest SteeringAngle,
    Speed and RPM values each tick -- this class owns all lateral-offset
    smoothing, road scrolling and HUD drawing state.
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("World / Lane Viz + Cockpit HUD")
        self.clock = pygame.time.Clock()

        ftext.init()
        self.font = ftext.Font(None, 16)  # base size; per-render `size=` overrides it

        # A separate SRCALPHA surface is required for real transparency -- the
        # main display surface ignores alpha on draw calls, it's always opaque.
        self.hud = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)

        self.scene_tile = load_scene_tile()
        self.car_sprite = load_car_sprite()

        self.lateral_offset = 0.0
        self.scroll_offset = 0.0

    def poll_events(self):
        """Process the pygame event queue. Returns False on window close."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True

    def tick(self):
        """Advance the frame clock. Returns dt in seconds."""
        return self.clock.tick(FPS) / 1000.0

    def render(self, steering_deg, speed_kmh, rpm, dt):
        target_offset = clamp(
            (steering_deg / MAX_STEERING_DEG) * MAX_LATERAL_OFFSET,
            -MAX_LATERAL_OFFSET, MAX_LATERAL_OFFSET,
        )
        self.lateral_offset += (target_offset - self.lateral_offset) * clamp(STEER_SMOOTH_RATE * dt, 0.0, 1.0)
        self.scroll_offset = (self.scroll_offset + speed_kmh * SCROLL_GAIN * dt) % 1_000_000

        # --- Lane panel ---
        draw_scene(self.screen, self.scene_tile, self.scroll_offset)
        draw_car(self.screen, self.car_sprite, ROAD_CENTER_X + self.lateral_offset, CAR_Y)

        # --- Stacked HUD: holographic overlay below the car ---
        self.hud.fill((0, 0, 0, 0))
        draw_hologram(self.hud, self.font, HOLO_CENTER_X, HOLO_TOP_BASE_Y, speed_kmh, MAX_SPEED_DISPLAY, HOLO_SPEED_COLOR, "SPEED", "KM/H")
        draw_hologram(self.hud, self.font, HOLO_CENTER_X, HOLO_BOTTOM_BASE_Y, rpm, MAX_RPM_DISPLAY, HOLO_RPM_COLOR, "RPM")
        self.screen.blit(self.hud, (0, 0))

        pygame.display.flip()

    def close(self):
        ftext.quit()
        pygame.quit()
