import pygame
import random
import math
import sys

# ─── Colours ───────────────────────────────────────────────────────────────────
BLACK      = (  0,   0,   0)
WHITE      = (255, 255, 255)
DARK_BG    = ( 15,  25,  15)
PANEL_BG   = ( 10,  10,  20)
GREEN      = ( 60, 200,  60)
BLUE       = ( 30, 120, 220)
LIGHT_BLUE = (100, 180, 255)
RED        = (220,  40,  40)
ORANGE     = (255, 160,  20)
YELLOW     = (240, 210,  30)
GRAY       = (100, 100, 100)
LIGHT_GRAY = (180, 180, 180)
CYAN       = ( 40, 200, 200)
PINK       = (255, 120, 160)
BROWN      = (160, 100,  35)
GOLD       = (200, 160,  40)

CELL = 8
FPS  = 60

# ─── Seasons ───────────────────────────────────────────────────────────────────
# (name, plant_spawn_mult, max_plants_mult, plant_grow_mult, bg_tint, label_color)
SEASONS = [
    ("Весна", 1.2, 1.0,  1.0,  ( 18,  32,  18), (130, 230, 130)),
    ("Лето",  2.0, 1.35, 1.4,  ( 20,  28,   8), (230, 210,  60)),
    ("Осень", 0.55, 0.85, 0.6, ( 28,  20,   8), (210, 140,  50)),
    ("Зима",  0.08, 0.4, -0.05,( 16,  22,  36), (160, 200, 255)),
]
SEASON_TICKS = 1200   # ticks per season (4 seasons = 4800 ticks per year)

# ─── Species name pools ────────────────────────────────────────────────────────
_HERB_NAMES = [
    "Травоед","Листоед","Стеблежуй","Корнеед","Сеноед",
    "Мягкоед","Зеленец","Лугоход","Полевик","Болотник",
    "Плодоед","Веточник","Мшеед","Цветоед","Ростоед",
]
_PRED_NAMES = [
    "Клыкач","Коготник","Ловчий","Зубастый","Стремглав",
    "Хватун","Прыгун","Тенелов","Бегомор","Ночной охотник",
    "Засадник","Вихрь","Гонщик","Разрывник","Падальщик",
]
_used_herb: set = set()
_used_pred: set = set()

_SCAV_NAMES = [
    "Стервятник", "Трупоед", "Гнильщик", "Костогрыз", "Объедала",
    "Мертвоед",   "Вонючка", "Подбиральщик", "Утильщик", "Серый едок",
    "Тенеед",     "Чистильщик", "Дохлятник", "Гробокоп", "Гнилозуб",
]
_used_scav: set = set()

_OMNI_NAMES = [
    "Всеядка","Прожора","Смешанник","Двуедок","Ловкач",
    "Выживала","Приспособленец","Гибрид","Широкорот","Разноед",
    "Хитрец","Многоед","Гибкий","Умелец","Опортунист",
]
_used_omni: set = set()


def _new_species_name(kind):
    if kind == "scav":
        pool, used = _SCAV_NAMES, _used_scav
    elif kind == "omni":
        pool, used = _OMNI_NAMES, _used_omni
    elif kind == "herb":
        pool, used = _HERB_NAMES, _used_herb
    else:
        pool, used = _PRED_NAMES, _used_pred
    names = [n for n in pool if n not in used] or pool
    name  = random.choice(names)
    used.add(name)
    return name

MUTABLE_TRAITS = {"speed": (0.3, 5.0), "vision": (2.0, 20.0), "size": (0.3, 4.0), "herd_instinct": (0.0, 1.0)}
# diet trait: 0.0 = pure herbivore, 1.0 = pure carnivore, 0.5 = omnivore
# mutates at birth; affects what the animal can/will eat
DIET_TRAIT_BOUNDS = (0.0, 1.0)
DIET_HERB_THRESH  = 0.35   # diet <= this → eats plants, not animals
DIET_CARN_THRESH  = 0.65   # diet >= this → eats animals, not plants
# between thresholds → omnivore (eats both)

# endurance trait: 0.0=normal, 1.0=max endurance
# high endurance → -speed penalty, +ecost/thirst reduction, +wander range
ENDURANCE_BOUNDS = (0.0, 1.0)

CORPSE_LIFETIME   = 380    # ticks before a corpse fully rots away


# ═══════════════════════════════════════════════════════════════════════════════
# SIM PARAMS
# ═══════════════════════════════════════════════════════════════════════════════
class SimParams:
    def __init__(self):
        self.mutation_chance   = 0.40
        self.mutation_std      = 0.18
        self.herb_hunger       = 0.03
        self.pred_hunger       = 0.06
        self.thirst_mult       = 1.0
        self.speciation_thresh = 10


# ─── Dynamic layout ────────────────────────────────────────────────────────────
class Layout:
    PANEL_FRAC = 0.30

    def __init__(self, sw, sh):
        self.update(sw, sh)

    def update(self, sw, sh):
        self.sw      = sw
        self.sh      = sh
        self.panel_w = max(320, int(sw * self.PANEL_FRAC))
        self.world_w = sw - self.panel_w - 6
        self.world_h = sh
        self.panel_x = self.world_w + 3
        self.cols    = self.world_w // CELL
        self.rows    = self.world_h // CELL


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDER
# Stores track position in screen coords during draw() so hit-testing and
# value-setting always use the correct coordinates.
# ═══════════════════════════════════════════════════════════════════════════════
class Slider:
    def __init__(self, label, lo, hi, value, step=1, fmt=None, color=CYAN):
        self.label = label
        self.lo    = float(lo)
        self.hi    = float(hi)
        self.value = float(value)
        self.step  = float(step)
        self.fmt   = fmt or (lambda v: f"{int(v)}" if step >= 1 else f"{v:.2f}")
        self.color = color
        # filled in by draw_* — used for hit-test and drag
        self._hit_rect    = pygame.Rect(0, 0, 0, 0)
        self._track_scr_x = 0   # screen x of track left edge
        self._track_scr_w = 1   # screen width of track

    # ── full-size (label above, large knob) ──────────────────────────────────
    def draw_full(self, surf, panel_scr_x, x, y, w, font, extra=""):
        """panel_scr_x: x of panel surface on screen (panel always at scr_y=0)."""
        knob_r  = 8
        track_h = 8
        lbl = font.render(f"{self.label}: {self.fmt(self.value)}{extra}", True, WHITE)
        surf.blit(lbl, (x, y - lbl.get_height() - 2))
        self._draw_track(surf, x, y, w, track_h, knob_r)
        # track goes from panel_scr_x+x to panel_scr_x+x+w
        self._track_scr_x = panel_scr_x + x
        self._track_scr_w = w
        self._hit_rect = pygame.Rect(
            panel_scr_x + x - knob_r, y - knob_r,
            w + knob_r * 2, track_h + knob_r * 2)
        return self._hit_rect

    # ── compact (one-line: label | track | value) ─────────────────────────────
    def draw_compact(self, surf, panel_scr_x, x, y, w, font):
        """panel_scr_x: x of panel surface on screen."""
        knob_r  = 6
        track_h = 6
        label_s = font.render(self.label + ":", True, LIGHT_GRAY)
        value_s = font.render(self.fmt(self.value), True, self.color)
        lw = label_s.get_width() + 6
        vw = value_s.get_width() + 4
        tw = max(20, w - lw - vw)
        ty = y + (label_s.get_height() - track_h) // 2
        surf.blit(label_s, (x, y))
        surf.blit(value_s, (x + lw + tw + 4, y))
        self._draw_track(surf, x + lw, ty, tw, track_h, knob_r)
        # screen coords of track
        self._track_scr_x = panel_scr_x + x + lw
        self._track_scr_w = tw
        self._hit_rect = pygame.Rect(
            panel_scr_x + x + lw - knob_r, ty - knob_r,
            tw + knob_r * 2, track_h + knob_r * 2)
        return self._hit_rect

    def _draw_track(self, surf, x, y, w, h, knob_r):
        frac = (self.value - self.lo) / max(1e-9, self.hi - self.lo)
        fw   = int(w * frac)
        pygame.draw.rect(surf, (50, 50, 65), (x, y, w, h), border_radius=3)
        if fw > 0:
            pygame.draw.rect(surf, self.color, (x, y, fw, h), border_radius=3)
        kx, ky = x + fw, y + h // 2
        pygame.draw.circle(surf, WHITE,      (kx, ky), knob_r)
        pygame.draw.circle(surf, self.color, (kx, ky), knob_r - 2)

    def set_from_mouse(self, mouse_x):
        """Call with screen-space mouse x. Uses stored track coords."""
        rel   = mouse_x - self._track_scr_x
        frac  = max(0.0, min(1.0, rel / max(1, self._track_scr_w)))
        steps = round(frac * (self.hi - self.lo) / self.step)
        self.value = max(self.lo, min(self.hi, self.lo + steps * self.step))

    def hit(self, scr_pos):
        return self._hit_rect.collidepoint(scr_pos)


# ═══════════════════════════════════════════════════════════════════════════════
# PLANT
# ═══════════════════════════════════════════════════════════════════════════════
class Plant:
    MAX_E = 60

    def __init__(self, x, y, energy=None):
        self.x, self.y = x, y
        self.energy = energy if energy else random.uniform(8, self.MAX_E)
        self.alive  = True

    def update(self, grow_rate):
        self.energy = max(0.0, min(self.MAX_E, self.energy + grow_rate))
        if self.energy <= 0:
            self.alive = False

    def draw(self, surf):
        frac = self.energy / self.MAX_E
        r    = max(2, int(frac * 4))
        g    = int(80 + frac * 160)
        pygame.draw.circle(surf, (0, g, 0),
                           (self.x * CELL + CELL // 2,
                            self.y * CELL + CELL // 2), r)


# ═══════════════════════════════════════════════════════════════════════════════
# WATER SOURCE
# ═══════════════════════════════════════════════════════════════════════════════
class WaterSource:
    def __init__(self, x, y, radius=4):
        self.x, self.y, self.radius = x, y, radius
        self.rects = []

    def rebuild(self, world_w, world_h):
        self.rects = []
        r2 = self.radius ** 2
        for dx in range(-self.radius, self.radius + 1):
            for dy in range(-self.radius, self.radius + 1):
                if dx*dx + dy*dy <= r2:
                    px, py = (self.x + dx)*CELL, (self.y + dy)*CELL
                    if 0 <= px < world_w - CELL and 0 <= py < world_h - CELL:
                        self.rects.append((px, py, CELL, CELL))

    def draw(self, surf):
        for r in self.rects:
            pygame.draw.rect(surf, BLUE, r)
        pygame.draw.circle(surf, LIGHT_BLUE,
                           (self.x*CELL + CELL//2, self.y*CELL + CELL//2), 3)


# ═══════════════════════════════════════════════════════════════════════════════
# CORPSE
# ═══════════════════════════════════════════════════════════════════════════════
class Corpse:
    def __init__(self, x, y, energy):
        self.x, self.y  = float(x), float(y)
        self.energy     = float(max(6.0, energy))
        self.max_e      = self.energy
        self.life       = CORPSE_LIFETIME
        self.alive      = True

    def dist(self, o): return math.hypot(self.x - o.x, self.y - o.y)

    def update(self):
        self.life  -= 1
        self.energy = self.max_e * (self.life / CORPSE_LIFETIME)
        if self.life <= 0 or self.energy < 1.0:
            self.alive = False

    def draw(self, surf):
        cx = int(self.x * CELL + CELL // 2)
        cy = int(self.y * CELL + CELL // 2)
        frac = max(0.0, self.life / CORPSE_LIFETIME)
        r    = max(2, int(3 * frac + 1))
        col  = (int(110 * frac), int(75 * frac), int(30 * frac))
        pygame.draw.line(surf, col, (cx - r, cy - r), (cx + r, cy + r), 2)
        pygame.draw.line(surf, col, (cx + r, cy - r), (cx - r, cy + r), 2)
        pygame.draw.circle(surf, col, (cx, cy), max(1, r // 2))


# ═══════════════════════════════════════════════════════════════════════════════
# BASE ANIMAL
# ═══════════════════════════════════════════════════════════════════════════════
class Animal:
    def __init__(self, x, y, speed, vision, size, energy, generation, color,
                 species_name, mutation_count=0,
                 base_speed=None, base_vision=None, base_size=None,
                 diet=None, endurance=None, herd_instinct=None):
        self.x, self.y      = float(x), float(y)
        self.speed          = speed
        self.vision         = vision
        self.size           = size
        self.energy         = float(energy)
        self.hydration      = 100.0
        self.MAX_E          = 200.0
        self.MAX_H          = 100.0
        self.age            = 0
        self.max_age        = random.randint(800, 1400)
        self.generation     = generation
        self.alive          = True
        self.color          = list(color)
        self.state          = "бродит"
        self.children       = 0
        self.kills          = 0
        self.rep_cd         = 0
        self.species_name   = species_name
        self.mutation_count = mutation_count
        self.fat            = 0.0   # fat storage for winter survival
        self.MAX_FAT        = self.size * 50.0 # max fat scales with size
        self.base_speed     = base_speed  or speed
        self.base_vision    = base_vision or vision
        self.base_size      = base_size   or size
        self.diet           = diet if diet is not None else self._default_diet()
        self.endurance      = endurance if endurance is not None else 0.0
        self.herd_instinct  = herd_instinct if herd_instinct is not None else random.uniform(0, 0.3)
        a = random.uniform(0, 2*math.pi)
        self.dx, self.dy = math.cos(a), math.sin(a)
        self._recalc_costs()

    def get_visibility(self, season_idx):
        """Returns multiplier for how easy this animal is to see (0.3 to 1.2)."""
        bg_color = SEASONS[season_idx][4]
        # Calculate color distance
        dist = sum((self.color[i] - bg_color[i])**2 for i in range(3))**0.5
        # normalize: 0 distance -> low visibility (camouflage), high distance -> high visibility
        # Max theoretical distance is ~441. 150 is a 'distinct' difference.
        camouflage = max(0.3, min(1.2, dist / 160.0))
        return camouflage

    def _default_diet(self):
        return 0.15   # overridden by subclass

    @property
    def eats_plants(self):
        return self.diet <= DIET_CARN_THRESH   # herbivore or omnivore

    @property
    def eats_animals(self):
        return self.diet >= DIET_HERB_THRESH   # carnivore or omnivore

    @property
    def diet_label(self):
        if self.diet <= DIET_HERB_THRESH:   return "травоядное"
        if self.diet >= DIET_CARN_THRESH:   return "хищник"
        return "всеядное"

    def _recalc_costs(self):
        # Super-linear: faster/bigger → exponentially hungrier and thirstier
        base_ecost   = self.speed**1.5 * 0.022 + self.size**1.3 * 0.018 + self.vision * 0.0012
        base_thirst  = 0.10 + self.speed * 0.04 + self.size * 0.03
        
        # Fat penalty: being fat is costly and slow
        fat_ratio = self.fat / max(1, self.MAX_FAT)
        fat_speed_penalty = fat_ratio * 0.25 # up to 25% slower
        fat_cost_penalty  = fat_ratio * 0.40 # up to 40% more energy cost
        
        # Endurance reduces hunger/thirst but also caps effective speed
        end          = getattr(self, 'endurance', 0.0)
        end_discount = end * 0.45          # up to 45% cheaper energy/thirst
        
        self.ecost        = base_ecost   * (1.0 - end_discount) * (1.0 + fat_cost_penalty)
        self.thirst_drain = base_thirst  * (1.0 - end_discount)
        # Endurance also slows the animal (trade-off)
        self.eff_speed    = self.speed * (1.0 - end * 0.35) * (1.0 - fat_speed_penalty)

    def _metabolism(self, season_idx):
        # Fat burning/accumulation logic
        # If energy is high (>80%), convert excess to fat
        if self.energy > self.MAX_E * 0.8:
            transfer = 0.15
            can_add = self.MAX_FAT - self.fat
            amount = min(transfer, can_add)
            self.fat += amount
            self.energy -= amount * 0.8 # slightly inefficient storage
        
        # If energy is low (<30%), burn fat to survive
        elif self.energy < self.MAX_E * 0.3 and self.fat > 0:
            burn = 0.25
            amount = min(burn, self.fat)
            self.fat -= amount
            self.energy += amount * 1.5 # fat is calorie dense
            
        # Seasonal thermoregulation: Winter is cold, costs more energy if not enough fat
        if season_idx == 3: # Winter
            # If low fat, energy drain is doubled due to cold
            cold_drain = 0.04 * (1.0 - (self.fat / max(1, self.MAX_FAT)))
            self.energy -= max(0, cold_drain)
        
        self._recalc_costs()

    def dist(self, o):         return math.hypot(self.x-o.x, self.y-o.y)
    def dist_xy(self, tx, ty): return math.hypot(self.x-tx,  self.y-ty)

    def toward(self, tx, ty):
        dx, dy = tx-self.x, ty-self.y
        m = math.hypot(dx, dy)
        if m: self.dx, self.dy = dx/m, dy/m

    def away(self, tx, ty):
        dx, dy = self.x-tx, self.y-ty
        m = math.hypot(dx, dy)
        if m: self.dx, self.dy = dx/m, dy/m

    def wander(self):
        # high endurance → narrower turns (straighter long-distance wandering)
        end   = getattr(self, 'endurance', 0.0)
        sigma = 0.6 - end * 0.35
        if random.random() < 0.04:
            a = math.atan2(self.dy, self.dx) + random.gauss(0, sigma)
            self.dx, self.dy = math.cos(a), math.sin(a)

    def step(self, cols, rows):
        sp = getattr(self, 'eff_speed', self.speed)
        self.x = max(0.0, min(cols-1.0, self.x + self.dx*sp))
        self.y = max(0.0, min(rows-1.0, self.y + self.dy*sp))
        if self.x <= 0 or self.x >= cols-1: self.dx *= -1
        if self.y <= 0 or self.y >= rows-1: self.dy *= -1

    def step_toward(self, tx, ty, cols, rows):
        """Move toward target without overshooting."""
        dx, dy = tx-self.x, ty-self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-4: return
        sp   = getattr(self, 'eff_speed', self.speed)
        move = min(sp, dist)
        self.dx, self.dy = dx/dist, dy/dist
        self.x = max(0.0, min(cols-1.0, self.x + self.dx*move))
        self.y = max(0.0, min(rows-1.0, self.y + self.dy*move))
        if self.x <= 0 or self.x >= cols-1: self.dx *= -1
        if self.y <= 0 or self.y >= rows-1: self.dy *= -1

    def nearest(self, seq, max_d):
        best, bd = None, max_d
        for o in seq:
            d = self.dist(o)
            if d < bd: best, bd = o, d
        return best, bd

    def nearest_water(self, sources):
        best, bd = None, float("inf")
        for ws in sources:
            d = self.dist_xy(ws.x, ws.y)
            if d < bd: best, bd = ws, d
        return best, bd

    def can_reproduce(self):
        return (self.energy > self.MAX_E * 0.65
                and self.hydration > 45
                and self.rep_cd <= 0
                and self.age > 120)

    def _draw_bar(self, surf, cx, cy, r, value, maxi, color):
        w = r*2; bx, by = cx-r, cy-r-5
        pygame.draw.rect(surf, (40, 40, 40), (bx, by, w, 3))
        pygame.draw.rect(surf, color, (bx, by, int(w*max(0, value/maxi)), 3))

    def _speciate_name_color(self, kind):
        name  = _new_species_name(kind)
        color = [(self.color[i] + random.randint(0, 255))//2 for i in range(3)]
        return name, color


# ═══════════════════════════════════════════════════════════════════════════════
# HERBIVORE
# ═══════════════════════════════════════════════════════════════════════════════
class Herbivore(Animal):
    _base_species = "Травоядное"

    def __init__(self, x, y, speed=None, vision=None, size=None,
                 energy=100, generation=1, species_name=None,
                 mutation_count=0, base_speed=None, base_vision=None,
                 base_size=None, color=None, diet=None, endurance=None,
                 herd_instinct=None):
        speed  = speed  or random.uniform(0.9, 2.2)
        vision = vision or random.uniform(5, 13)
        size   = size   or random.uniform(0.7, 1.6)
        color  = color  or [30, random.randint(160, 230), random.randint(80, 140)]
        name   = species_name or self._base_species
        super().__init__(x, y, speed, vision, size, energy, generation, color,
                         name, mutation_count, base_speed, base_vision, base_size,
                         diet=diet, endurance=endurance, herd_instinct=herd_instinct)
        self.MAX_E   = 160.0
        self.max_age = random.randint(600, 1100)

    def _default_diet(self): return 0.10   # start as herbivore

    def update(self, plants, waters, predators, cols, rows, p: SimParams, season_idx, extra_threats=None, allies=None):
        self.age    += 1
        self.rep_cd -= 1
        self._metabolism(season_idx)
        self.energy    -= self.ecost + p.herb_hunger
        self.hydration -= self.thirst_drain * p.thirst_mult

        if self.energy    <= 0: self.alive = False; return "starved"
        if self.hydration <= 0: self.alive = False; return "thirst"
        if self.age > self.max_age: self.alive = False; return "old"

        # flee from predators and large omnivores
        _all_threats = predators + (extra_threats or [])
        real_threats = []
        for pr in _all_threats:
            if pr.alive and pr.eats_animals and pr.size >= self.size * 0.65:
                # Visibility/Camouflage logic: predators must see me
                vis = self.get_visibility(season_idx)
                if self.dist(pr) < pr.vision * vis * 1.5:
                    real_threats.append(pr)
        
        threat, td = self.nearest(real_threats, self.vision * 2.5)
        if threat and td < self.vision * 2:
            self.state = "бежит"
            self.away(threat.x, threat.y)
            self.step(cols, rows)
            return None

        # drink
        if self.hydration < 45:
            ws, wd = self.nearest_water(waters)
            if ws:
                self.state = "пьёт"
                if wd < ws.radius + 1.2:
                    self.hydration = min(self.MAX_H, self.hydration + 6)
                else:
                    self.step_toward(ws.x, ws.y, cols, rows)
                return None

        # HERDING: move towards same species if instinct is high
        if self.herd_instinct > 0.15 and allies:
            if self.energy > self.MAX_E * 0.35:
                # only keep distance 4-8 units
                friends = [a for a in allies if a.alive and a != self and a.species_name == self.species_name]
                friend, fd = self.nearest(friends, self.vision * 2.5)
                if friend and fd > 5.0:
                    self.state = "в стаде"
                    if random.random() < self.herd_instinct:
                        self.step_toward(friend.x, friend.y, cols, rows)
                        return None

        # omnivore/carnivore: hunt small predators
        if self.eats_animals and self.energy < self.MAX_E * 0.5:
            prey_list = [pr for pr in predators
                         if pr.alive and self.size >= pr.size * 0.65]
            prey, pd = self.nearest(prey_list, self.vision)
            if prey:
                self.state = "охотится"
                if pd < 1.4:
                    prey.alive = False
                    self.energy = min(self.MAX_E, self.energy + 55)
                    self.kills += 1
                else:
                    self.step_toward(prey.x, prey.y, cols, rows)
                return None

        # eat plants
        if self.eats_plants:
            # Satiety: only eat if energy < 90% or fat storage not full
            if self.energy < self.MAX_E * 0.9 or self.fat < self.MAX_FAT * 0.95:
                food = [pl for pl in plants
                        if pl.alive and pl.energy > 5 and self.dist(pl) < self.vision]
                if food:
                    food.sort(key=lambda pl: self.dist(pl))
                    tgt = food[0]
                    self.state = "ест"
                    if self.dist(tgt) < 1.4:
                        bite = min(tgt.energy, 18)
                        self.energy = min(self.MAX_E, self.energy + bite)
                        tgt.energy -= bite
                        if tgt.energy <= 0: tgt.alive = False
                    else:
                        self.step_toward(tgt.x, tgt.y, cols, rows)
                    return None

        self.state = "бродит"
        self.wander()
        self.step(cols, rows)
        return None

    def spawn(self, p: SimParams):
        if not self.can_reproduce():
            return None, None, None
        self.rep_cd = 350
        self.energy *= 0.58
        self.children += 1

        mutations = []
        new_speed, new_vision, new_size = self.speed, self.vision, self.size
        new_diet       = self.diet
        new_endurance  = self.endurance
        new_herd       = self.herd_instinct
        new_color      = list(self.color)

        for trait, (lo, hi) in MUTABLE_TRAITS.items():
            if random.random() < p.mutation_chance:
                delta = random.gauss(0, p.mutation_std)
                new   = max(lo, min(hi, getattr(self, trait) + delta))
                if trait == "speed":  new_speed  = new
                if trait == "vision": new_vision = new
                if trait == "size":   new_size   = new
                if trait == "herd_instinct": new_herd = new
                mutations.append((trait, delta))
                
                # COLOR DRIFT: color now mutates slowly to allow camouflage evolution
                c_idx = random.randint(0, 2)
                new_color[c_idx] = max(0, min(255, new_color[c_idx] + random.randint(-20, 20)))

        # diet mutation (slow drift)
        if random.random() < p.mutation_chance * 0.5:
            diet_delta = random.gauss(0, 0.08)
            new_diet   = max(0.0, min(1.0, self.diet + diet_delta))
            mutations.append(("diet", diet_delta))

        # endurance mutation (slow drift)
        if random.random() < p.mutation_chance * 0.4:
            end_delta     = random.gauss(0, 0.07)
            new_endurance = max(0.0, min(1.0, self.endurance + end_delta))
            mutations.append(("выносл", end_delta))

        new_mc = self.mutation_count + len(mutations)
        new_name, speciated = self.species_name, False
        thresh = int(p.speciation_thresh)
        if new_mc >= thresh and self.mutation_count < thresh:
            # Predator: rare mutation
            if new_diet > 0.65 and random.random() < 0.06:
                pr_c = [random.randint(160, 240), random.randint(15, 55), random.randint(15, 55)]
                child_pred = Predator(
                    self.x + random.uniform(-2, 2), self.y + random.uniform(-2, 2),
                    speed=max(1.0, new_speed * 1.25),
                    vision=min(20.0, new_vision),
                    size=new_size, energy=90, generation=self.generation + 1,
                    species_name=_new_species_name("pred"),
                    mutation_count=0, base_speed=self.base_speed,
                    base_vision=self.base_vision, base_size=self.base_size,
                    color=pr_c, diet=max(0.70, new_diet), endurance=new_endurance,
                    herd_instinct=new_herd)
                return child_pred, True, None
            # Scavenger mutation
            if new_diet > 0.35 and random.random() < 0.22:
                sc = [random.randint(120, 165), random.randint(65, 110), random.randint(15, 55)]
                scav = Scavenger(
                    self.x + random.uniform(-2, 2), self.y + random.uniform(-2, 2),
                    speed=max(0.3, new_speed * 0.82),
                    vision=min(20.0, new_vision * 1.2),
                    size=new_size, energy=55, generation=self.generation + 1,
                    species_name=_new_species_name("scav"),
                    mutation_count=0, base_speed=self.base_speed,
                    base_vision=self.base_vision, base_size=self.base_size,
                    color=sc, diet=0.18, endurance=new_endurance,
                    herd_instinct=new_herd)
                return scav, True, None
            # Omnivore mutation
            if new_diet > 0.20 and random.random() < 0.22:
                om_c = [random.randint(170, 215), random.randint(140, 190), random.randint(20, 65)]
                omni = Omnivore(
                    self.x + random.uniform(-2, 2), self.y + random.uniform(-2, 2),
                    speed=max(0.3, new_speed * 0.60),
                    vision=min(18.0, new_vision),
                    size=new_size, energy=70, generation=self.generation + 1,
                    species_name=_new_species_name("omni"),
                    mutation_count=0, base_speed=self.base_speed,
                    base_vision=self.base_vision, base_size=self.base_size,
                    color=om_c, diet=max(0.30, min(0.70, new_diet)),
                    endurance=new_endurance, herd_instinct=new_herd)
                return omni, True, None
            new_name, new_color = self._speciate_name_color("herb")
            new_mc, speciated = 0, True

        child = Herbivore(
            self.x + random.uniform(-2, 2), self.y + random.uniform(-2, 2),
            speed=new_speed, vision=new_vision, size=new_size, energy=65,
            generation=self.generation+1, species_name=new_name,
            mutation_count=new_mc, base_speed=self.base_speed,
            base_vision=self.base_vision, base_size=self.base_size,
            color=new_color, diet=new_diet, endurance=new_endurance,
            herd_instinct=new_herd)
        mut_desc = None
        if mutations and not speciated:
            parts = ", ".join(
                f"{t}({'+'if d>0 else''}{d:.2f})" if t not in ("diet", "выносл", "herd_instinct")
                else (f"рацион→{child.diet_label}" if t == "diet"
                      else (f"выносл→{child.endurance:.2f}" if t == "выносл"
                            else f"стадность→{child.herd_instinct:.2f}"))
                for t, d in mutations)
            mut_desc = f"{child.species_name}: {parts} [{new_mc}]"
        return child, speciated, mut_desc

    def draw(self, surf):
        cx, cy = int(self.x*CELL), int(self.y*CELL)
        r = max(3, int(self.size*4))
        pygame.draw.circle(surf, tuple(self.color), (cx, cy), r)
        pygame.draw.circle(surf, WHITE, (cx, cy), r, 1)
        self._draw_bar(surf, cx, cy, r, self.energy, self.MAX_E, GREEN)


# ═══════════════════════════════════════════════════════════════════════════════
# PREDATOR
# ═══════════════════════════════════════════════════════════════════════════════
class Predator(Animal):
    _base_species = "Хищник"

    def __init__(self, x, y, speed=None, vision=None, size=None,
                 energy=160, generation=1, species_name=None,
                 mutation_count=0, base_speed=None, base_vision=None,
                 base_size=None, color=None, diet=None, endurance=None,
                 herd_instinct=None):
        speed  = speed  or random.uniform(1.6, 3.2)
        vision = vision or random.uniform(8, 16)
        size   = size   or random.uniform(1.3, 2.8)
        color  = color  or [random.randint(180,255), random.randint(20,70), random.randint(20,70)]
        name   = species_name or self._base_species
        super().__init__(x, y, speed, vision, size, energy, generation, color,
                         name, mutation_count, base_speed, base_vision, base_size,
                         diet=diet, endurance=endurance, herd_instinct=herd_instinct)
        self.MAX_E   = 250.0
        self.max_age = random.randint(900, 1600)

    def _default_diet(self): return 0.90   # start as carnivore

    def update(self, herbivores, waters, cols, rows, p: SimParams, season_idx, plants=None):
        self.age    += 1
        self.rep_cd -= 1
        self._metabolism(season_idx)
        self.energy    -= self.ecost + p.pred_hunger
        self.hydration -= self.thirst_drain * p.thirst_mult

        if self.energy    <= 0: self.alive = False; return "starved"
        if self.hydration <= 0: self.alive = False; return "thirst"
        if self.age > self.max_age: self.alive = False; return "old"

        # drink
        if self.hydration < 30:
            ws, wd = self.nearest_water(waters)
            if ws:
                self.state = "пьёт"
                if wd < ws.radius + 1.2:
                    self.hydration = min(self.MAX_H, self.hydration + 7)
                else:
                    self.step_toward(ws.x, ws.y, cols, rows)
                return None

        # hunt animals (if diet allows)
        if self.eats_animals:
            # Satiety: only hunt if energy < 85% or fat storage not full
            if self.energy < self.MAX_E * 0.85 or self.fat < self.MAX_FAT * 0.95:
                # CAMOUFLAGE: check visibility of prey
                prey_list = []
                for h in herbivores:
                    if h.alive and self.size >= h.size * 0.65:
                        vis = h.get_visibility(season_idx)
                        if self.dist(h) < self.vision * vis:
                            prey_list.append(h)
                
                prey, pd = self.nearest(prey_list, self.vision)
                if prey:
                    self.state = "охотится"
                    if pd < 1.5:
                        prey.alive = False
                        self.energy = min(self.MAX_E, self.energy + 70)
                        self.kills += 1
                        self.step(cols, rows)
                        return "kill"
                    else:
                        self.step_toward(prey.x, prey.y, cols, rows)
                    return None

        # eat plants (omnivore / herbivore-shifted predator)
        if self.eats_plants and plants:
            # Satiety for plants: only eat if energy < 70% (it's inefficient for predators)
            if self.energy < self.MAX_E * 0.70:
                food = [pl for pl in plants
                        if pl.alive and pl.energy > 5 and self.dist(pl) < self.vision]
                if food:
                    food.sort(key=lambda pl: self.dist(pl))
                    tgt = food[0]
                    self.state = "пасётся"
                    if self.dist(tgt) < 1.4:
                        bite = min(tgt.energy, 14)
                        self.energy = min(self.MAX_E, self.energy + bite)
                        tgt.energy -= bite
                        if tgt.energy <= 0: tgt.alive = False
                    else:
                        self.step_toward(tgt.x, tgt.y, cols, rows)
                    return None

        self.state = "бродит"
        self.wander()
        self.step(cols, rows)
        return None

    def spawn(self, p: SimParams):
        if not self.can_reproduce():
            return None, None, None
        self.rep_cd = 550
        self.energy *= 0.52
        self.children += 1

        mutations = []
        new_speed, new_vision, new_size = self.speed, self.vision, self.size
        new_diet      = self.diet
        new_endurance = self.endurance
        new_color     = list(self.color)

        for trait, (lo, hi) in MUTABLE_TRAITS.items():
            if random.random() < p.mutation_chance:
                delta = random.gauss(0, p.mutation_std)
                new   = max(lo, min(hi, getattr(self, trait) + delta))
                if trait == "speed":  new_speed  = new
                if trait == "vision": new_vision = new
                if trait == "size":   new_size   = new
                mutations.append((trait, delta))
                if delta > 0: new_color[0] = min(255, new_color[0]+10)
                else:         new_color[0] = max(100, new_color[0]-8); new_color[1] = min(80, new_color[1]+6)

        if random.random() < p.mutation_chance * 0.5:
            diet_delta = random.gauss(0, 0.08)
            new_diet   = max(0.0, min(1.0, self.diet + diet_delta))
            mutations.append(("diet", diet_delta))
            if diet_delta < 0: new_color[1] = min(120, new_color[1]+20)
            else:              new_color[0] = min(255, new_color[0]+10)

        if random.random() < p.mutation_chance * 0.4:
            end_delta     = random.gauss(0, 0.07)
            new_endurance = max(0.0, min(1.0, self.endurance + end_delta))
            mutations.append(("выносл", end_delta))
            if end_delta > 0: new_color[2] = min(180, new_color[2] + 12)
            else:              new_color[2] = max(0,   new_color[2] - 8)

        new_mc = self.mutation_count + len(mutations)
        new_name, speciated = self.species_name, False
        thresh = int(p.speciation_thresh)
        if new_mc >= thresh and self.mutation_count < thresh:
            new_name, new_color = self._speciate_name_color("pred")
            new_mc, speciated = 0, True

        child = Predator(
            self.x + random.uniform(-2, 2), self.y + random.uniform(-2, 2),
            speed=new_speed, vision=new_vision, size=new_size, energy=90,
            generation=self.generation+1, species_name=new_name,
            mutation_count=new_mc, base_speed=self.base_speed,
            base_vision=self.base_vision, base_size=self.base_size,
            color=new_color, diet=new_diet, endurance=new_endurance,
            herd_instinct=new_herd)
        mut_desc = None
        if mutations and not speciated:
            parts = ", ".join(
                f"{t}({'+'if d>0 else''}{d:.2f})" if t not in ("diet", "выносл", "herd_instinct")
                else (f"рацион→{child.diet_label}" if t == "diet"
                      else (f"выносл→{child.endurance:.2f}" if t == "выносл"
                            else f"стадность→{child.herd_instinct:.2f}"))
                for t, d in mutations)
            mut_desc = f"{child.species_name}: {parts} [{new_mc}]"
        return child, speciated, mut_desc

    def draw(self, surf):
        cx, cy = int(self.x*CELL), int(self.y*CELL)
        r = max(4, int(self.size*5))
        pts = [(cx, cy-r), (cx+r, cy+r//2), (cx, cy+r//2-1), (cx-r, cy+r//2)]
        pygame.draw.polygon(surf, tuple(self.color), pts)
        pygame.draw.polygon(surf, WHITE, pts, 1)
        self._draw_bar(surf, cx, cy, r, self.energy, self.MAX_E, RED)


# ═══════════════════════════════════════════════════════════════════════════════
# SCAVENGER  —  eats corpses (+ plants poorly); slower, hungrير, better vision
# Emerges only via mutation from Herbivore — never placed at sim start.
# Trade-offs vs herbivore:
#   + good energy from corpses          + higher vision range
#   - 1.35× hunger rate                 - 0.82× speed cap
#   - half energy from plants           - cannot hunt live animals
# ═══════════════════════════════════════════════════════════════════════════════
class Scavenger(Animal):
    _base_species = "Падальщик"

    def __init__(self, x, y, speed=None, vision=None, size=None,
                 energy=80, generation=1, species_name=None,
                 mutation_count=0, base_speed=None, base_vision=None,
                 base_size=None, color=None, diet=None, endurance=None,
                 herd_instinct=None):
        speed  = speed  or random.uniform(0.6, 1.5)
        vision = vision or random.uniform(10, 18)
        size   = size   or random.uniform(0.8, 2.0)
        color  = color  or [random.randint(120, 165),
                             random.randint(65, 110),
                             random.randint(15, 55)]
        name   = species_name or self._base_species
        super().__init__(x, y, speed, vision, size, energy, generation, color,
                         name, mutation_count, base_speed, base_vision, base_size,
                         diet=diet, endurance=endurance, herd_instinct=herd_instinct)
        self.MAX_E   = 150.0
        self.max_age = random.randint(500, 1000)

    def _default_diet(self): return 0.18

    def update(self, corpses, plants, waters, predators, cols, rows, p: SimParams,
               season_idx, extra_threats=None, allies=None):
        self.age    += 1
        self.rep_cd -= 1
        self._metabolism(season_idx)
        self.energy    -= self.ecost + p.herb_hunger * 1.35   # hungrier trade-off
        self.hydration -= self.thirst_drain * p.thirst_mult

        if self.energy    <= 0: self.alive = False; return "starved"
        if self.hydration <= 0: self.alive = False; return "thirst"
        if self.age > self.max_age: self.alive = False; return "old"

        # flee from predators and large omnivores
        _all_threats = predators + (extra_threats or [])
        threats = []
        for pr in _all_threats:
            if pr.alive and pr.eats_animals and pr.size >= self.size * 0.65:
                vis = self.get_visibility(season_idx)
                if self.dist(pr) < pr.vision * vis * 1.5:
                    threats.append(pr)
        
        threat, td = self.nearest(threats, self.vision * 2.5)
        if threat and td < self.vision * 2:
            self.state = "бежит"
            self.away(threat.x, threat.y)
            self.step(cols, rows)
            return None

        # drink
        if self.hydration < 45:
            ws, wd = self.nearest_water(waters)
            if ws:
                self.state = "пьёт"
                if wd < ws.radius + 1.2:
                    self.hydration = min(self.MAX_H, self.hydration + 6)
                else:
                    self.step_toward(ws.x, ws.y, cols, rows)
                return None

        # HERDING
        if self.herd_instinct > 0.15 and allies:
            if self.energy > self.MAX_E * 0.4:
                friends = [a for a in allies if a.alive and a != self and a.species_name == self.species_name]
                friend, fd = self.nearest(friends, self.vision * 2.5)
                if friend and fd > 5.0:
                    self.state = "в стае"
                    if random.random() < self.herd_instinct:
                        self.step_toward(friend.x, friend.y, cols, rows)
                        return None

        # eat corpse — primary food, good energy payoff
        # Satiety: only eat if energy < 90% or fat storage not full
        if self.energy < self.MAX_E * 0.9 or self.fat < self.MAX_FAT * 0.95:
            live_corpses = [c for c in corpses
                            if c.alive and c.energy > 1.5 and self.dist(c) < self.vision]
            if live_corpses:
                live_corpses.sort(key=lambda c: self.dist(c))
                tgt = live_corpses[0]
                self.state = "ест труп"
                if self.dist(tgt) < 1.4:
                    bite = min(tgt.energy, 24)
                    self.energy  = min(self.MAX_E, self.energy + bite)
                    tgt.energy  -= bite
                    if tgt.energy < 1.5:
                        tgt.alive = False
                else:
                    self.step_toward(tgt.x, tgt.y, cols, rows)
                return None

        # eat plants — secondary, half efficiency
        if self.energy < self.MAX_E * 0.75:
            food = [pl for pl in plants
                    if pl.alive and pl.energy > 5 and self.dist(pl) < self.vision]
            if food:
                food.sort(key=lambda pl: self.dist(pl))
                tgt = food[0]
                self.state = "жует траву"
                if self.dist(tgt) < 1.4:
                    bite = min(tgt.energy, 9)   # half vs herbivore's 18
                    self.energy = min(self.MAX_E, self.energy + bite)
                    tgt.energy -= bite
                    if tgt.energy <= 0: tgt.alive = False
                else:
                    self.step_toward(tgt.x, tgt.y, cols, rows)
                return None

        self.state = "рыщет"
        self.wander()
        self.step(cols, rows)
        return None

    def spawn(self, p: SimParams):
        if not self.can_reproduce():
            return None, None, None
        self.rep_cd = 420
        self.energy *= 0.55
        self.children += 1

        mutations = []
        new_speed, new_vision, new_size = self.speed, self.vision, self.size
        new_diet      = self.diet
        new_endurance = self.endurance
        new_color     = list(self.color)

        for trait, (lo, hi) in MUTABLE_TRAITS.items():
            if random.random() < p.mutation_chance:
                delta = random.gauss(0, p.mutation_std)
                new   = max(lo, min(hi, getattr(self, trait) + delta))
                if trait == "speed":  new_speed  = new
                if trait == "vision": new_vision = new
                if trait == "size":   new_size   = new
                mutations.append((trait, delta))
                if delta > 0: new_color[0] = min(200, new_color[0] + 8)
                else:         new_color[1] = max(0,   new_color[1] - 5)

        if random.random() < p.mutation_chance * 0.3:
            diet_delta = random.gauss(0, 0.06)
            new_diet   = max(0.0, min(1.0, self.diet + diet_delta))
            mutations.append(("diet", diet_delta))

        if random.random() < p.mutation_chance * 0.4:
            end_delta     = random.gauss(0, 0.07)
            new_endurance = max(0.0, min(1.0, self.endurance + end_delta))
            mutations.append(("выносл", end_delta))
            if end_delta > 0: new_color[2] = min(160, new_color[2] + 12)
            else:              new_color[2] = max(0,   new_color[2] - 8)

        new_mc = self.mutation_count + len(mutations)
        new_name, speciated = self.species_name, False
        thresh = int(p.speciation_thresh)
        if new_mc >= thresh and self.mutation_count < thresh:
            new_name  = _new_species_name("scav")
            new_color = [(self.color[i] + random.randint(0, 200)) // 2 for i in range(3)]
            new_mc, speciated = 0, True

        child = Scavenger(
            self.x + random.uniform(-2, 2), self.y + random.uniform(-2, 2),
            speed=new_speed, vision=new_vision, size=new_size, energy=55,
            generation=self.generation + 1, species_name=new_name,
            mutation_count=new_mc, base_speed=self.base_speed,
            base_vision=self.base_vision, base_size=self.base_size,
            color=new_color, diet=new_diet, endurance=new_endurance,
            herd_instinct=new_herd)
        mut_desc = None
        if mutations and not speciated:
            parts = ", ".join(
                f"{t}({'+'if d>0 else''}{d:.2f})" if t not in ("diet", "выносл", "herd_instinct")
                else (f"рацион→{child.diet_label}" if t == "diet"
                      else (f"выносл→{child.endurance:.2f}" if t == "выносл"
                            else f"стадность→{child.herd_instinct:.2f}"))
                for t, d in mutations)
            mut_desc = f"{child.species_name}: {parts} [{new_mc}]"
        return child, speciated, mut_desc

    def draw(self, surf):
        cx, cy = int(self.x * CELL), int(self.y * CELL)
        r = max(3, int(self.size * 4))
        pygame.draw.circle(surf, tuple(self.color), (cx, cy), r)
        d = max(2, r - 1)
        pygame.draw.line(surf, (210, 160, 70), (cx - d, cy - d), (cx + d, cy + d), 1)
        pygame.draw.line(surf, (210, 160, 70), (cx + d, cy - d), (cx - d, cy + d), 1)
        pygame.draw.circle(surf, WHITE, (cx, cy), r, 1)
        self._draw_bar(surf, cx, cy, r, self.energy, self.MAX_E, ORANGE)


# ═══════════════════════════════════════════════════════════════════════════════
# OMNIVORE — eats plants AND live prey; slowest class, best food flexibility
# Emerges only via mutation from Herbivore at speciation (diet drifted to 0.20+).
# Trade-offs:
#   + eats plants and live animals      + survives food scarcity well
#   - 0.60× speed cap (slowest ever)    - slightly more hungry than herbivore
#   - less kill energy than predator    - easy prey for preds due to low speed
# ═══════════════════════════════════════════════════════════════════════════════
class Omnivore(Animal):
    _base_species = "Всеядное"

    def __init__(self, x, y, speed=None, vision=None, size=None,
                 energy=90, generation=1, species_name=None,
                 mutation_count=0, base_speed=None, base_vision=None,
                 base_size=None, color=None, diet=None, endurance=None,
                 herd_instinct=None):
        speed  = speed  or random.uniform(0.4, 1.0)
        vision = vision or random.uniform(7, 14)
        size   = size   or random.uniform(0.8, 2.2)
        color  = color  or [random.randint(170, 215),
                             random.randint(140, 190),
                             random.randint(20, 65)]
        name   = species_name or self._base_species
        super().__init__(x, y, speed, vision, size, energy, generation, color,
                         name, mutation_count, base_speed, base_vision, base_size,
                         diet=diet, endurance=endurance, herd_instinct=herd_instinct)
        self.MAX_E   = 170.0
        self.max_age = random.randint(700, 1200)

    def _default_diet(self): return 0.50   # true omnivore

    def update(self, plants, prey_pool, waters, predators, cols, rows, p: SimParams, season_idx, allies=None):
        self.age    += 1
        self.rep_cd -= 1
        self._metabolism(season_idx)
        self.energy    -= self.ecost + p.herb_hunger * 1.10
        self.hydration -= self.thirst_drain * p.thirst_mult

        if self.energy    <= 0: self.alive = False; return "starved"
        if self.hydration <= 0: self.alive = False; return "thirst"
        if self.age > self.max_age: self.alive = False; return "old"

        # flee from predators
        real_threats = []
        for pr in predators:
            if pr.alive and pr.eats_animals and pr.size >= self.size * 0.65:
                vis = self.get_visibility(season_idx)
                if self.dist(pr) < pr.vision * vis * 1.5:
                    real_threats.append(pr)

        threat, td = self.nearest(real_threats, self.vision * 2.5)
        if threat and td < self.vision * 2:
            self.state = "бежит"
            self.away(threat.x, threat.y)
            self.step(cols, rows)
            return None

        # drink
        if self.hydration < 45:
            ws, wd = self.nearest_water(waters)
            if ws:
                self.state = "пьёт"
                if wd < ws.radius + 1.2:
                    self.hydration = min(self.MAX_H, self.hydration + 6)
                else:
                    self.step_toward(ws.x, ws.y, cols, rows)
                return None

        # HERDING
        if self.herd_instinct > 0.15 and allies:
            if self.energy > self.MAX_E * 0.4:
                friends = [a for a in allies if a.alive and a != self and a.species_name == self.species_name]
                friend, fd = self.nearest(friends, self.vision * 2.5)
                if friend and fd > 5.0:
                    self.state = "в стае"
                    if random.random() < self.herd_instinct:
                        self.step_toward(friend.x, friend.y, cols, rows)
                        return None

        # hunt live prey (herbs + scavs) when hungry — slower than predator
        if self.eats_animals:
            # Satiety: only hunt if energy < 85% or fat storage not full
            if self.energy < self.MAX_E * 0.85 or self.fat < self.MAX_FAT * 0.95:
                huntable = [a for a in prey_pool if a.alive and self.size >= a.size * 0.80]
                prey, pd = self.nearest(huntable, self.vision)
                if prey:
                    self.state = "охотится"
                    if pd < 1.4:
                        prey.alive = False
                        self.energy = min(self.MAX_E, self.energy + 45)
                        self.kills += 1
                    else:
                        self.step_toward(prey.x, prey.y, cols, rows)
                    return None

        # eat plants
        if self.eats_plants:
            # Satiety: only eat if energy < 90% or fat storage not full
            if self.energy < self.MAX_E * 0.9 or self.fat < self.MAX_FAT * 0.95:
                food = [pl for pl in plants
                        if pl.alive and pl.energy > 5 and self.dist(pl) < self.vision]
                if food:
                    food.sort(key=lambda pl: self.dist(pl))
                    tgt = food[0]
                    self.state = "ест"
                    if self.dist(tgt) < 1.4:
                        bite = min(tgt.energy, 16)
                        self.energy = min(self.MAX_E, self.energy + bite)
                        tgt.energy -= bite
                        if tgt.energy <= 0: tgt.alive = False
                    else:
                        self.step_toward(tgt.x, tgt.y, cols, rows)
                    return None

        self.state = "бродит"
        self.wander()
        self.step(cols, rows)
        return None

    def spawn(self, p: SimParams):
        if not self.can_reproduce():
            return None, None, None
        self.rep_cd = 400
        self.energy *= 0.56
        self.children += 1

        mutations = []
        new_speed, new_vision, new_size = self.speed, self.vision, self.size
        new_diet      = self.diet
        new_endurance = self.endurance
        new_color     = list(self.color)

        for trait, (lo, hi) in MUTABLE_TRAITS.items():
            if random.random() < p.mutation_chance:
                delta = random.gauss(0, p.mutation_std)
                new   = max(lo, min(hi, getattr(self, trait) + delta))
                if trait == "speed":  new_speed  = new
                if trait == "vision": new_vision = new
                if trait == "size":   new_size   = new
                mutations.append((trait, delta))
                if delta > 0: new_color[0] = min(230, new_color[0] + 8)
                else:         new_color[1] = max(80, new_color[1] - 6)

        if random.random() < p.mutation_chance * 0.4:
            diet_delta = random.gauss(0, 0.07)
            new_diet   = max(0.0, min(1.0, self.diet + diet_delta))
            mutations.append(("diet", diet_delta))

        if random.random() < p.mutation_chance * 0.4:
            end_delta     = random.gauss(0, 0.07)
            new_endurance = max(0.0, min(1.0, self.endurance + end_delta))
            mutations.append(("выносл", end_delta))
            if end_delta > 0: new_color[2] = min(180, new_color[2] + 12)
            else:              new_color[2] = max(0,   new_color[2] - 8)

        new_mc = self.mutation_count + len(mutations)
        new_name, speciated = self.species_name, False
        thresh = int(p.speciation_thresh)
        if new_mc >= thresh and self.mutation_count < thresh:
            new_name  = _new_species_name("omni")
            new_color = [(self.color[i] + random.randint(0, 180)) // 2 for i in range(3)]
            new_mc, speciated = 0, True

        child = Omnivore(
            self.x + random.uniform(-2, 2), self.y + random.uniform(-2, 2),
            speed=new_speed, vision=new_vision, size=new_size, energy=60,
            generation=self.generation + 1, species_name=new_name,
            mutation_count=new_mc, base_speed=self.base_speed,
            base_vision=self.base_vision, base_size=self.base_size,
            color=new_color, diet=new_diet, endurance=new_endurance,
            herd_instinct=new_herd)
        mut_desc = None
        if mutations and not speciated:
            parts = ", ".join(
                f"{t}({'+'if d>0 else''}{d:.2f})" if t not in ("diet", "выносл", "herd_instinct")
                else (f"рацион→{child.diet_label}" if t == "diet"
                      else (f"выносл→{child.endurance:.2f}" if t == "выносл"
                            else f"стадность→{child.herd_instinct:.2f}"))
                for t, d in mutations)
            mut_desc = f"{child.species_name}: {parts} [{new_mc}]"
        return child, speciated, mut_desc

    def draw(self, surf):
        cx, cy = int(self.x * CELL), int(self.y * CELL)
        r = max(3, int(self.size * 4))
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        pygame.draw.polygon(surf, tuple(self.color), pts)
        pygame.draw.polygon(surf, WHITE, pts, 1)
        self._draw_bar(surf, cx, cy, r, self.energy, self.MAX_E, YELLOW)


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════
class Simulation:
    BASE_MAX_PLANTS = 350
    BASE_PLANT_RATE = 0.35
    BASE_PLANT_GROW = 0.08

    def __init__(self, layout: Layout):
        self.layout            = layout
        self.tick              = 0
        self.plants:  list     = []
        self.waters:  list     = []
        self.herbs:   list     = []
        self.preds:   list     = []
        self.scavs:   list     = []
        self.omnis:   list     = []
        self.corpses: list     = []
        self.events:  list     = []
        self.history           = {"h": [], "p": [], "s": [], "o": [], "pl": []}
        self.paused            = False
        self.total_births_h    = 0
        self.total_births_p    = 0
        self.total_births_s    = 0
        self.total_births_o    = 0
        self.total_deaths      = 0
        self.total_kills       = 0
        self.total_speciations = 0
        self.species_list      = {"herb": set(), "pred": set(), "scav": set(), "omni": set()}
        self.ui_tab            = "INFO"  # "INFO", "SPECIES", "SETTINGS", "GRAPH", "INSPECTOR"
        self.selected_animal   = None
        self._init()

    @property
    def cols(self): return self.layout.cols
    @property
    def rows(self): return self.layout.rows

    # ── season helpers ────────────────────────────────────────────────────────
    @property
    def season_idx(self):
        return (self.tick // SEASON_TICKS) % 4

    @property
    def season_info(self):
        return SEASONS[self.season_idx]

    @property
    def season_progress(self):
        return (self.tick % SEASON_TICKS) / SEASON_TICKS

    # ── init ──────────────────────────────────────────────────────────────────
    def _init(self):
        for _ in range(5):
            ws = WaterSource(
                random.randint(6, self.cols-6),
                random.randint(6, self.rows-6),
                radius=random.randint(3, 6))
            ws.rebuild(self.layout.world_w, self.layout.world_h)
            self.waters.append(ws)
        for _ in range(180):
            self.plants.append(Plant(
                random.randint(0, self.cols-1),
                random.randint(0, self.rows-1)))
        for _ in range(30):
            h = Herbivore(random.randint(3, self.cols-3),
                          random.randint(3, self.rows-3))
            self.herbs.append(h)
            self.species_list["herb"].add(h.species_name)
        for _ in range(6):
            pr = Predator(random.randint(3, self.cols-3),
                          random.randint(3, self.rows-3))
            self.preds.append(pr)
            self.species_list["pred"].add(pr.species_name)
        self._log("Симуляция запущена", CYAN)

    def on_resize(self):
        for ws in self.waters:
            ws.rebuild(self.layout.world_w, self.layout.world_h)

    def _log(self, text, color=LIGHT_GRAY):
        self.events.append([text, color, 320])
        if len(self.events) > 20: self.events.pop(0)

    def update(self, p: SimParams):
        if self.paused: return
        self.tick += 1
        cols, rows = self.cols, self.rows

        sname, spawn_m, max_m, grow_m, _, _ = self.season_info
        effective_max  = int(self.BASE_MAX_PLANTS * max_m)
        effective_rate = self.BASE_PLANT_RATE * spawn_m
        effective_grow = self.BASE_PLANT_GROW * grow_m

        # announce season change
        if self.tick % SEASON_TICKS == 1 and self.tick > 1:
            self._log(f"Наступил(а) {sname}!", SEASONS[self.season_idx][5])

        # plants
        alive_pl = [pl for pl in self.plants if pl.alive]
        deficit  = effective_max - len(alive_pl)
        if deficit > 0 and random.random() < effective_rate:
            for _ in range(random.randint(1, min(4, max(1, deficit)))):
                if alive_pl and random.random() < 0.7:
                    ref = random.choice(alive_pl)
                    x = max(0, min(cols-1, ref.x + random.randint(-6, 6)))
                    y = max(0, min(rows-1, ref.y + random.randint(-6, 6)))
                else:
                    x, y = random.randint(0, cols-1), random.randint(0, rows-1)
                self.plants.append(Plant(x, y, random.uniform(5, 25)))
        for pl in self.plants:
            pl.update(effective_grow)
        self.plants = [pl for pl in self.plants if pl.alive]

        # corpses decay
        for c in self.corpses:
            c.update()
        self.corpses = [c for c in self.corpses if c.alive]

        # herbivores
        new_h = []
        for h in self.herbs:
            res = h.update(self.plants, self.waters, self.preds, cols, rows, p, self.season_idx, self.omnis, self.herbs)
            if not h.alive:
                self.total_deaths += 1
                ce = max(6.0, h.size * 20 + h.energy * 0.3)
                self.corpses.append(Corpse(h.x, h.y, ce))
                msgs = {"starved": ("умерло от голода", YELLOW),
                        "thirst":  ("умерло от жажды",  LIGHT_BLUE),
                        "old":     ("умерло от старости", GRAY)}
                if res in msgs: self._log(f"{h.species_name} {msgs[res][0]}", msgs[res][1])
            else:
                child, spec, mut_desc = h.spawn(p)
                if child:
                    if isinstance(child, Omnivore):
                        self.omnis.append(child)
                        self.total_births_o   += 1
                        self.total_speciations += 1
                        self.species_list["omni"].add(child.species_name)
                        self._log(f"МУТАЦИЯ → ВСЕЯДНЫЙ: «{child.species_name}»!", GOLD)
                    elif isinstance(child, Predator):
                        self.preds.append(child)
                        self.total_births_p   += 1
                        self.total_speciations += 1
                        self.species_list["pred"].add(child.species_name)
                        self._log(f"МУТАЦИЯ → ХИЩНИК: «{child.species_name}»!", RED)
                    elif isinstance(child, Scavenger):
                        self.scavs.append(child)
                        self.total_births_s   += 1
                        self.total_speciations += 1
                        self.species_list["scav"].add(child.species_name)
                        self._log(f"МУТАЦИЯ → ПАДАЛЬЩИК: «{child.species_name}»!", BROWN)
                    else:
                        new_h.append(child)
                        self.total_births_h += 1
                        self.species_list["herb"].add(child.species_name)
                        if spec:
                            self.total_speciations += 1
                            self._log(f"НОВЫЙ ВИД: «{child.species_name}»!", CYAN)
                        elif mut_desc:
                            self._log(mut_desc, (120, 255, 120))
                        else:
                            self._log(f"Рождение {child.species_name} пок.{child.generation}", GREEN)
        self.herbs = [h for h in self.herbs if h.alive] + new_h

        # predators hunt herbs + scavengers + omnivores
        all_prey = self.herbs + self.scavs + self.omnis
        new_p = []
        for pred in self.preds:
            res = pred.update(all_prey, self.waters, cols, rows, p, self.season_idx, self.plants)
            if not pred.alive:
                self.total_deaths += 1
                ce = max(10.0, pred.size * 28 + pred.energy * 0.3)
                self.corpses.append(Corpse(pred.x, pred.y, ce))
                msgs = {"starved": ("умер от голода",   ORANGE),
                        "thirst":  ("умер от жажды",    LIGHT_BLUE),
                        "old":     ("умер от старости", GRAY)}
                if res in msgs: self._log(f"{pred.species_name} {msgs[res][0]}", msgs[res][1])
            else:
                if res == "kill":
                    self.total_kills += 1
                    self._log(f"{pred.species_name} схватил добычу! ({self.total_kills})", RED)
                child, spec, mut_desc = pred.spawn(p)
                if child:
                    new_p.append(child)
                    self.total_births_p += 1
                    self.species_list["pred"].add(child.species_name)
                    if spec:
                        self.total_speciations += 1
                        self._log(f"НОВЫЙ ВИД ХИЩНИКА: «{child.species_name}»!", ORANGE)
                    elif mut_desc:
                        self._log(mut_desc, PINK)
                    else:
                        self._log(f"Рождение {child.species_name} пок.{child.generation}", PINK)
        self.preds = [pr for pr in self.preds if pr.alive] + new_p

        # scavengers
        new_s = []
        for scav in self.scavs:
            res = scav.update(self.corpses, self.plants, self.waters, self.preds,
                              cols, rows, p, self.season_idx, self.omnis, self.scavs)
            if not scav.alive:
                self.total_deaths += 1
                ce = max(5.0, scav.size * 14 + scav.energy * 0.2)
                self.corpses.append(Corpse(scav.x, scav.y, ce))
                msgs = {"starved": ("пал от голода", ORANGE),
                        "thirst":  ("пал от жажды",  LIGHT_BLUE),
                        "old":     ("пал от старости", GRAY)}
                if res in msgs: self._log(f"{scav.species_name} {msgs[res][0]}", msgs[res][1])
            else:
                child, spec, mut_desc = scav.spawn(p)
                if child:
                    new_s.append(child)
                    self.total_births_s += 1
                    self.species_list["scav"].add(child.species_name)
                    if spec:
                        self.total_speciations += 1
                        self._log(f"НОВЫЙ ВИД ПАДАЛЬЩИКА: «{child.species_name}»!", BROWN)
                    elif mut_desc:
                        self._log(mut_desc, (200, 140, 60))
                    else:
                        self._log(f"Рождение {child.species_name} пок.{child.generation}",
                                  (200, 140, 60))
        self.scavs = [s for s in self.scavs if s.alive] + new_s

        # omnivores (hunt herbs + scavs; slowest class)
        new_o = []
        omni_prey = self.herbs + self.scavs
        for omni in self.omnis:
            res = omni.update(self.plants, omni_prey, self.waters, self.preds,
                              cols, rows, p, self.season_idx, self.omnis)
            if not omni.alive:
                self.total_deaths += 1
                ce = max(6.0, omni.size * 18 + omni.energy * 0.25)
                self.corpses.append(Corpse(omni.x, omni.y, ce))
                msgs = {"starved": ("пал от голода", GOLD),
                        "thirst":  ("пал от жажды",  LIGHT_BLUE),
                        "old":     ("пал от старости", GRAY)}
                if res in msgs: self._log(f"{omni.species_name} {msgs[res][0]}", msgs[res][1])
            else:
                if res == "kill":
                    self.total_kills += 1
                child, spec, mut_desc = omni.spawn(p)
                if child:
                    new_o.append(child)
                    self.total_births_o += 1
                    self.species_list["omni"].add(child.species_name)
                    if spec:
                        self.total_speciations += 1
                        self._log(f"НОВЫЙ ВИД ВСЕЯДНОГО: «{child.species_name}»!", GOLD)
                    elif mut_desc:
                        self._log(mut_desc, (200, 180, 60))
                    else:
                        self._log(f"Рождение {child.species_name} пок.{child.generation}",
                                  (200, 180, 60))
        self.omnis = [o for o in self.omnis if o.alive] + new_o

        if self.tick % 90 == 0:
            self.history["h"].append(len(self.herbs))
            self.history["p"].append(len(self.preds))
            self.history["s"].append(len(self.scavs))
            self.history["o"].append(len(self.omnis))
            self.history["pl"].append(len(self.plants))
            for k in self.history:
                if len(self.history[k]) > 120: self.history[k].pop(0)

        for e in self.events: e[2] -= 1
        self.events = [e for e in self.events if e[2] > 0]

        # log extinctions
        if len(self.herbs) == 0 and self.tick % 300 == 0:
            self._log("Травоядные вымерли.", RED)
        if len(self.preds) == 0 and self.tick % 300 == 0:
            self._log("Хищники вымерли.", ORANGE)
        if len(self.scavs) == 0 and self.tick % 600 == 0 and self.total_births_s > 0:
            self._log("Падальщики вымерли.", BROWN)
        if len(self.omnis) == 0 and self.tick % 600 == 0 and self.total_births_o > 0:
            self._log("Всеядные вымерли.", GOLD)


# ═══════════════════════════════════════════════════════════════════════════════
# RENDERER
# ═══════════════════════════════════════════════════════════════════════════════
def draw_all(screen, sim: Simulation, layout: Layout, fonts,
             speed_sl: Slider, param_sliders: list):
    fs, fm, fb = fonts
    L = layout

    # world background — tinted by season
    sname, _, _, _, bg_tint, s_color = sim.season_info
    world_surf = screen.subsurface((0, 0, L.world_w, L.world_h))
    world_surf.fill(bg_tint)

    for ws in sim.waters:  ws.draw(world_surf)
    for pl in sim.plants:  pl.draw(world_surf)
    for c  in sim.corpses: c.draw(world_surf)
    for h  in sim.herbs:   h.draw(world_surf)
    for sc in sim.scavs:   sc.draw(world_surf)
    for om in sim.omnis:   om.draw(world_surf)
    for pr in sim.preds:   pr.draw(world_surf)
    pygame.draw.rect(screen, GRAY, (0, 0, L.world_w, L.world_h), 2)

    # season banner (top-left of world)
    banner = fs.render(f"  {sname}  ", True, BLACK)
    bw, bh = banner.get_width() + 4, banner.get_height() + 2
    pygame.draw.rect(world_surf, s_color, (4, 4, bw, bh), border_radius=4)
    world_surf.blit(banner, (6, 5))
    # season progress bar
    prog_w = int(bw * sim.season_progress)
    pygame.draw.rect(world_surf, (0, 0, 0, 120), (4, bh+6, bw, 4), border_radius=2)
    if prog_w > 0:
        pygame.draw.rect(world_surf, s_color, (4, bh+6, prog_w, 4), border_radius=2)

    # panel
    panel = screen.subsurface((L.panel_x, 0, L.panel_w, L.sh))
    panel.fill(PANEL_BG)
    px, py = 8, 8
    pw     = L.panel_w - px*2

    def txt(s, color, f=None, indent=0):
        nonlocal py
        surf = (f or fs).render(s, True, color)
        panel.blit(surf, (px + indent, py))
        py += surf.get_height() + 2

    def hline(gap=3):
        nonlocal py
        py += gap
        pygame.draw.line(panel, GRAY, (px, py), (L.panel_w-px, py))
        py += gap + 2

    txt("СИМУЛЯТОР ЭВОЛЮЦИИ", WHITE, fb)
    txt(f"Тик: {sim.tick}  {'⏸ ПАУЗА' if sim.paused else '▶ работает'}", LIGHT_GRAY)
    hline(4)

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tabs = [("ИНФО", "INFO"), ("ВИДЫ", "SPECIES"), ("НАСТР", "SETTINGS"), ("ГРАФ", "GRAPH"), ("ОБЪЕКТ", "INSPECTOR")]
    tab_h = 28
    tw = L.panel_w // len(tabs)
    for i, (name, tid) in enumerate(tabs):
        tx = i * tw
        rect = pygame.Rect(tx, py, tw, tab_h)
        active = (sim.ui_tab == tid)
        pygame.draw.rect(panel, (40, 45, 70) if active else (20, 22, 35), rect)
        pygame.draw.rect(panel, GRAY if active else (50, 50, 60), rect, 1)
        t_surf = fs.render(name, True, WHITE if active else LIGHT_GRAY)
        panel.blit(t_surf, (tx + (tw - t_surf.get_width())//2, py + (tab_h - t_surf.get_height())//2))
    
    py += tab_h + 10

    if sim.ui_tab == "INFO":
        # season in panel
        year  = sim.tick // (SEASON_TICKS * 4) + 1
        s_idx = sim.season_idx
        season_row = f"Год {year}  |  "
        for i, (sn, *_rest) in enumerate(SEASONS):
            season_row += f"[{sn}]" if i == s_idx else f" {sn} "
        txt(season_row, s_color)
        hline()

        # speed slider
        py += 10
        tps = int(10 * speed_sl.value)
        speed_sl.draw_full(panel, L.panel_x, px, py, pw-4, fs,
                           extra=f"  ({tps} тик/с)")
        py += 18
        hline()

        # counts
        txt(f"Травоядные: {len(sim.herbs):>4}", GREEN)
        txt(f"Хищники:    {len(sim.preds):>4}", RED)
        txt(f"Падальщики: {len(sim.scavs):>4}", BROWN)
        txt(f"Всеядные:   {len(sim.omnis):>4}", GOLD)
        txt(f"Трупы:      {len(sim.corpses):>4}", GRAY)
        txt(f"Растения:   {len(sim.plants):>4}", (80, 200, 80))
        hline(2)

        def avg(seq, attr):
            return sum(getattr(a, attr) for a in seq)/len(seq) if seq else 0.0

        txt("СРЕДНИЕ ПОКАЗАТЕЛИ:", WHITE)
        txt(f"Трав: ск.{avg(sim.herbs,'speed'):.2f} зр.{avg(sim.herbs,'vision'):.1f} пок.{avg(sim.herbs,'generation'):.1f}", GREEN)
        txt(f"Хищн: ск.{avg(sim.preds,'speed'):.2f} зр.{avg(sim.preds,'vision'):.1f} пок.{avg(sim.preds,'generation'):.1f}", RED)
        if sim.scavs:
            txt(f"Пад:  ск.{avg(sim.scavs,'speed'):.2f} зр.{avg(sim.scavs,'vision'):.1f} пок.{avg(sim.scavs,'generation'):.1f}", BROWN)
        if sim.omnis:
            txt(f"Всеяд: ск.{avg(sim.omnis,'speed'):.2f} зр.{avg(sim.omnis,'vision'):.1f} пок.{avg(sim.omnis,'generation'):.1f}", GOLD)
        hline(2)

        txt(f"Рождений трав.: {sim.total_births_h}", (80, 220, 80))
        txt(f"Рождений хищн.: {sim.total_births_p}", PINK)
        txt(f"Рождений пад.:  {sim.total_births_s}", BROWN)
        txt(f"Рождений всеяд: {sim.total_births_o}", GOLD)
        txt(f"Смертей:        {sim.total_deaths}",   GRAY)
        txt(f"Убийств:        {sim.total_kills}",    ORANGE)
        txt(f"Видообраз.:     {sim.total_speciations}", CYAN)
        hline(2)

        # events
        txt("ПОСЛЕДНИЕ СОБЫТИЯ:", WHITE)
        for ev in reversed(sim.events[-12:]):
            if py > L.sh - 110: break
            alpha = min(255, ev[2]*2)
            c = tuple(min(255, int(ch*alpha/255)) for ch in ev[1])
            panel.blit(fs.render(ev[0][:46], True, c), (px, py))
            py += 15
        
        # controls at bottom
        py = L.sh - 100
        hline(2)
        for key, desc in [
            ("ПРОБЕЛ","пауза"), ("F11","полный экран"),
            ("Н","+трав."),      ("Х","+хищн."),
            ("С","+пад."),       ("R","рестарт"),
            ("Q","выход"),
        ]:
            sk = fs.render(key, True, YELLOW)
            sd = fs.render(f"  {desc}", True, GRAY)
            panel.blit(sk, (px, py)); panel.blit(sd, (px+sk.get_width(), py))
            py += 14

    elif sim.ui_tab == "SETTINGS":
        txt("НАСТРОЙКИ СИМУЛЯЦИИ:", WHITE)
        py += 10
        for sl in param_sliders:
            sl.draw_compact(panel, L.panel_x, px, py, pw, fs)
            py += 30
        hline()
        txt("Настройки применяются мгновенно.", GRAY)

    elif sim.ui_tab == "SPECIES":
        txt("СПИСОК ЖИВЫХ ВИДОВ И ПОДВИДОВ:", WHITE)
        txt("(группировка по названию и уровню мутаций)", GRAY)
        hline()

        def sp_stats(grp):
            if not grp: return None
            n  = len(grp)
            sp = sum(a.speed     for a in grp) / n
            sz = sum(a.size      for a in grp) / n
            vs = sum(a.vision    for a in grp) / n
            ec = sum(a.ecost     for a in grp) / n
            en = sum(a.endurance for a in grp) / n
            dt = sum(a.diet      for a in grp) / n
            gn = sum(a.generation for a in grp) / n
            dl = "трав" if dt <= DIET_HERB_THRESH else ("хищн" if dt >= DIET_CARN_THRESH else "всеяд")
            return sp, sz, vs, ec, en, dl, gn

        def get_subgroups(entities):
            groups = {}
            for e in entities:
                key = (e.species_name, e.mutation_count)
                if key not in groups: groups[key] = []
                groups[key].append(e)
            return sorted(groups.items(), key=lambda x: (x[0][0], -x[0][1]))

        h_active  = get_subgroups(sim.herbs)
        p_active  = get_subgroups(sim.preds)
        sc_active = get_subgroups(sim.scavs)
        om_active = get_subgroups(sim.omnis)
        all_sp    = h_active + p_active + sc_active + om_active

        def prey_labels(grp):
            if not grp: return ""
            n, asiz, adt = len(grp), sum(a.size for a in grp)/len(grp), sum(a.diet for a in grp)/len(grp)
            targets = []
            if adt <= DIET_CARN_THRESH: targets.append("Растения")
            if adt >= DIET_HERB_THRESH:
                for (name, mc), sg in all_sp:
                    if not sg or name == grp[0].species_name: continue
                    if asiz >= (sum(a.size for a in sg)/len(sg)) * 0.65:
                        if name not in targets: targets.append(name)
            return ("→ " + ", ".join(targets[:4])) if targets else ""

        def draw_species_block(active, label_color):
            nonlocal py
            thresh = int(params.speciation_thresh)
            for (name, mc), grp in active:
                if py > L.sh - 60: break
                t = sp_stats(grp)
                prey_str = prey_labels(grp)
                
                # Subspecies header
                if mc > 0:
                    txt(f"  ПОДВИД {name}: {len(grp)}", label_color)
                    # Speciation progress bar
                    prog = min(1.0, mc / thresh)
                    bar_w = 120
                    pygame.draw.rect(panel, (30, 30, 45), (px + 10, py + 2, bar_w, 4))
                    pygame.draw.rect(panel, CYAN, (px + 10, py + 2, int(bar_w * prog), 4))
                    txt(f"    Прогресс вида: {mc}/{thresh}", (100, 200, 255), f=fs, indent=120)
                else:
                    txt(f"  ВИД {name}: {len(grp)}", (255, 255, 255))
                
                if t:
                    sp2, sz2, vs2, ec2, en2, dl2, gn2 = t
                    en_str = f" вын:{en2:.2f}" if en2 > 0.05 else ""
                    
                    # Show trait deviation from base animal class defaults if possible
                    # We'll use the average of the first animal in group as a hint
                    first = grp[0]
                    def dev(val, base):
                        d = val - base
                        return f"{'+' if d>0 else ''}{d:.2f}"
                    
                    txt(f"    ск:{sp2:.1f}({dev(sp2, first.base_speed)}) "
                        f"рз:{sz2:.1f}({dev(sz2, first.base_size)}) "
                        f"зр:{vs2:.0f}({dev(vs2, first.base_vision)})", GRAY)
                    
                    txt(f"    тип:{dl2} пок:{gn2:.0f} е:{ec2:.2f}{en_str}", GRAY)
                
                if prey_str:
                    txt(f"    {prey_str}", (120, 120, 120))
                py += 6

        if h_active:
            txt(f"ТРАВОЯДНЫЕ ({len(h_active)} групп):", GREEN)
            draw_species_block(h_active, LIGHT_GRAY)
        if p_active:
            txt(f"ХИЩНИКИ ({len(p_active)} групп):", RED)
            draw_species_block(p_active, LIGHT_GRAY)
        if sc_active:
            txt(f"ПАДАЛЬЩИКИ ({len(sc_active)} групп):", BROWN)
            draw_species_block(sc_active, LIGHT_GRAY)
        if om_active:
            txt(f"ВСЕЯДНЫЕ ({len(om_active)} групп):", GOLD)
            draw_species_block(om_active, LIGHT_GRAY)

    elif sim.ui_tab == "GRAPH":
        txt("ДИНАМИКА ПОПУЛЯЦИИ:", WHITE)
        hline()
        py += 20
        graph_h = 240
        graph_w = pw
        graph_y = py
        pygame.draw.rect(panel, (8, 8, 18), (px, py, graph_w, graph_h))

        def draw_graph(data, color, max_v):
            if len(data) < 2 or max_v == 0: return
            step = graph_w / (len(data)-1)
            pts  = []
            for i, v in enumerate(data):
                gx = px + int(i*step)
                gy = max(graph_y, min(graph_y+graph_h, graph_y+graph_h - int(v/max_v*graph_h)))
                pts.append((gx, gy))
            pygame.draw.lines(panel, color, False, pts, 3)

        max_v = max(max(sim.history["h"] or [1]), max(sim.history["p"] or [1]),
                    max(sim.history["s"] or [0]), max(sim.history["o"] or [0]), 1)
        draw_graph(sim.history["h"], GREEN, max_v)
        draw_graph(sim.history["p"], RED,   max_v)
        draw_graph(sim.history["s"], BROWN, max_v)
        draw_graph(sim.history["o"], GOLD,  max_v)
        pygame.draw.rect(panel, GRAY, (px, graph_y, graph_w, graph_h), 1)
        
        py += graph_h + 10
        txt("Легенда:", WHITE)
        txt(" ● Зеленый: Травоядные", GREEN)
        txt(" ● Красный: Хищники", RED)
        txt(" ● Коричневый: Падальщики", BROWN)
        txt(" ● Золотой: Всеядные", GOLD)
        py += 20
        txt(f"Макс. популяция на графике: {int(max_v)}", LIGHT_GRAY)

    elif sim.ui_tab == "INSPECTOR":
        txt("ИНСПЕКТОР ОБЪЕКТА:", WHITE)
        hline()
        obj = sim.selected_animal
        if not obj:
            txt("Никто не выбран", GRAY)
            txt("Кликните по животному в мире,", GRAY)
            txt("чтобы увидеть его статы.", GRAY)
        else:
            # Species and Kind
            kind_colors = {"Herbivore": GREEN, "Predator": RED, "Scavenger": BROWN, "Omnivore": GOLD}
            k_name = type(obj).__name__
            
            alive_color = WHITE if obj.alive else GRAY
            txt(f"ВИД: {obj.species_name}", kind_colors.get(k_name, WHITE) if obj.alive else GRAY, fb)
            if not obj.alive:
                txt("СТАТУС: ПОГИБ", RED, fb)
            
            txt(f"Тип: {k_name} ({obj.diet_label})", LIGHT_GRAY)
            txt(f"Поколение: {obj.generation}", alive_color)
            hline()
            
            # State and Vitals
            if obj.alive:
                st_color = CYAN if obj.state == "бежит" else (ORANGE if obj.state == "охотится" else WHITE)
                txt(f"Состояние: {obj.state}", st_color)
            
            def draw_stat_bar(label, val, maxi, color):
                nonlocal py
                txt(f"{label}: {val:.1f}/{maxi:.0f}", WHITE if obj.alive else GRAY)
                pygame.draw.rect(panel, (30, 30, 40), (px, py, pw, 6))
                if obj.alive:
                    pygame.draw.rect(panel, color, (px, py, int(pw * max(0, min(1, val/maxi))), 6))
                py += 10
            
            draw_stat_bar("Энергия", obj.energy, obj.MAX_E, YELLOW)
            draw_stat_bar("Жажда", obj.hydration, obj.MAX_H, BLUE)
            draw_stat_bar("Жир (запас)", obj.fat, obj.MAX_FAT, (200, 200, 100))
            
            fat_ratio = obj.fat / max(1, obj.MAX_FAT)
            if fat_ratio > 0.1:
                txt(f"  Эффект: -{fat_ratio*25:.0f}% скор, +{fat_ratio*40:.0f}% расход", (255, 100, 100))
            
            py += 5
            txt(f"Возраст: {obj.age}/{obj.max_age} тик", LIGHT_GRAY)
            hline()
            
            # Traits
            txt("ГЕНЕТИЧЕСКИЕ ТРЕЙТЫ:", WHITE)
            def trait_row(lab, val, base):
                d = val - base
                d_str = f"({'+' if d>=0 else ''}{d:.2f})"
                txt(f"  {lab}: {val:.2f} {d_str}", LIGHT_GRAY)
            
            trait_row("Скорость", obj.speed, obj.base_speed)
            trait_row("Зрение", obj.vision, obj.base_vision)
            trait_row("Размер", obj.size, obj.base_size)
            txt(f"  Стадность: {obj.herd_instinct:.2f}", LIGHT_GRAY)
            
            # Visibility display
            vis = obj.get_visibility(sim.season_idx)
            vis_p = int(vis * 100)
            v_col = GREEN if vis < 0.6 else (YELLOW if vis < 0.9 else RED)
            txt(f"  Заметность: {vis_p}%", v_col)
            
            txt(f"  Выносливость: {obj.endurance:.2f}", LIGHT_GRAY)
            txt(f"  Рацион (0-1):  {obj.diet:.2f}", LIGHT_GRAY)
            hline()
            
            # Stats
            txt(f"Детей: {obj.children}  Убийств: {obj.kills}", WHITE)
            txt(f"Накоплено мутаций: {obj.mutation_count}", CYAN)

    # Highlight selected animal in world
    if sim.selected_animal and sim.selected_animal.alive:
        obj = sim.selected_animal
        sx, sy = int(obj.x * CELL), int(obj.y * CELL)
        r = max(6, int(obj.size * 6))
        pygame.draw.circle(world_surf, WHITE, (sx, sy), r + 2, 1)
        pygame.draw.circle(world_surf, CYAN, (sx, sy), r + 4, 1)


def draw_legend(screen, layout: Layout, font):
    items = [
        (GREEN,       "●", "Травоядное"),
        (RED,         "◆", "Хищник"),
        (BROWN,       "●", "Падальщик (×=труп)"),
        ((0, 160, 0), "●", "Растение"),
        (BLUE,        "■", "Вода"),
    ]
    x, y = 6, layout.world_h - len(items)*14 - 8
    bg = pygame.Surface((170, len(items)*14+8), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 150))
    screen.blit(bg, (x-2, y-2))
    for color, sym, label in items:
        screen.blit(font.render(f"{sym} {label}", True, color), (x, y))
        y += 14


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    pygame.init()

    def load_font(size, bold=False):
        for name in ("DejaVu Sans","FreeSans","Liberation Sans","Arial",None):
            try:
                if name: return pygame.font.SysFont(name, size, bold=bold)
            except Exception: pass
        return pygame.font.Font(None, size+4)

    fonts = (load_font(13), load_font(17), load_font(18, bold=True))

    INIT_W, INIT_H = 1380, 760
    screen = pygame.display.set_mode((INIT_W, INIT_H), pygame.RESIZABLE)
    pygame.display.set_caption("Симулятор Эволюции")
    clock = pygame.time.Clock()

    layout     = Layout(INIT_W, INIT_H)
    fullscreen = False
    params     = SimParams()
    sim        = Simulation(layout)

    BASE_TPS = 10.0
    tick_acc = 0.0

    speed_sl = Slider("Скорость", 1, 15, 1, step=1,
                      fmt=lambda v: f"{int(v)}×", color=CYAN)

    param_sliders = [
        Slider("Шанс мутации",  0, 100, 40, step=5,
               fmt=lambda v: f"{int(v)}%",         color=(180, 255, 100)),
        Slider("Величина мут.", 5,  80, 18, step=1,
               fmt=lambda v: f"σ={int(v)/100:.2f}", color=(180, 255, 100)),
        Slider("Голод трав.",   1,  30,  3, step=1,
               fmt=lambda v: f"{int(v)/100:.2f}",   color=GREEN),
        Slider("Голод хищн.",   1,  50,  6, step=1,
               fmt=lambda v: f"{int(v)/100:.2f}",   color=RED),
        Slider("Жажда",        20, 300,100, step=10,
               fmt=lambda v: f"{int(v)}%",          color=LIGHT_BLUE),
        Slider("Порог вида",    3,  25, 10, step=1,
               fmt=lambda v: f"{int(v)} мут.",      color=CYAN),
    ]

    all_sliders = [speed_sl] + param_sliders
    dragging    = None

    def apply_params():
        params.mutation_chance   = param_sliders[0].value / 100.0
        params.mutation_std      = param_sliders[1].value / 100.0
        params.herb_hunger       = param_sliders[2].value / 100.0
        params.pred_hunger       = param_sliders[3].value / 100.0
        params.thirst_mult       = param_sliders[4].value / 100.0
        params.speciation_thresh = param_sliders[5].value

    def toggle_fullscreen():
        nonlocal screen, fullscreen
        fullscreen = not fullscreen
        if fullscreen:
            info   = pygame.display.Info()
            screen = pygame.display.set_mode(
                (info.current_w, info.current_h), pygame.FULLSCREEN)
        else:
            screen = pygame.display.set_mode((INIT_W, INIT_H), pygame.RESIZABLE)
        layout.update(*screen.get_size())
        sim.on_resize()

    while True:
        clock.tick(FPS)
        apply_params()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            elif ev.type == pygame.VIDEORESIZE and not fullscreen:
                screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
                layout.update(ev.w, ev.h)
                sim.on_resize()

            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = ev.pos
                # Tab switching
                if mx >= layout.panel_x and 50 <= my <= 85:
                    tabs = ["INFO", "SPECIES", "SETTINGS", "GRAPH", "INSPECTOR"]
                    idx = (mx - layout.panel_x) // (layout.panel_w // len(tabs))
                    if 0 <= idx < len(tabs):
                        sim.ui_tab = tabs[idx]
                        dragging = None 
                
                # World interaction (Animal Selection)
                elif mx < layout.world_w:
                    # Convert pixel to cell coords
                    cx, cy = mx / CELL, my / CELL
                    all_anim = sim.herbs + sim.preds + sim.scavs + sim.omnis
                    best, bd = None, 2.5 # selection radius in cells
                    for a in all_anim:
                        if a.alive:
                            d = math.hypot(a.x - cx, a.y - cy)
                            if d < bd: best, bd = a, d
                    
                    if best:
                        sim.selected_animal = best
                        sim.ui_tab = "INSPECTOR"
                    else:
                        sim.selected_animal = None
                
                # Slider interaction (tab-specific)
                else:
                    target_sliders = []
                    if sim.ui_tab == "INFO":
                        target_sliders = [speed_sl]
                    elif sim.ui_tab == "SETTINGS":
                        target_sliders = param_sliders
                    
                    for sl in target_sliders:
                        if sl.hit(ev.pos):
                            dragging = sl
                            sl.set_from_mouse(ev.pos[0])
                            break

            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                dragging = None

            elif ev.type == pygame.MOUSEMOTION:
                if dragging:
                    dragging.set_from_mouse(ev.pos[0])

            elif ev.type == pygame.KEYDOWN:
                k = ev.key
                u = ev.unicode.lower() if ev.unicode else ''
                if   k in (pygame.K_q, pygame.K_ESCAPE): pygame.quit(); sys.exit()
                elif k == pygame.K_F11:   toggle_fullscreen()
                elif k == pygame.K_SPACE: sim.paused = not sim.paused
                elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    speed_sl.value = min(speed_sl.hi, speed_sl.value + 1)
                elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    speed_sl.value = max(speed_sl.lo, speed_sl.value - 1)
                elif k == pygame.K_n or u == 'н':
                    for _ in range(8):
                        sim.herbs.append(Herbivore(
                            random.randint(3, layout.cols-3),
                            random.randint(3, layout.rows-3)))
                    sim._log("Добавлено 8 травоядных", GREEN)
                elif k == pygame.K_x or u == 'х':
                    for _ in range(3):
                        sim.preds.append(Predator(
                            random.randint(3, layout.cols-3),
                            random.randint(3, layout.rows-3)))
                    sim._log("Добавлено 3 хищника", RED)
                elif k == pygame.K_s or u == 'с':
                    for _ in range(5):
                        sim.scavs.append(Scavenger(
                            random.randint(3, layout.cols-3),
                            random.randint(3, layout.rows-3)))
                    sim._log("Добавлено 5 падальщиков", BROWN)
                elif k == pygame.K_r:
                    sim = Simulation(layout)

        dt = clock.get_time() / 1000.0
        tick_acc += dt * BASE_TPS * speed_sl.value
        n = min(int(tick_acc), 12)
        tick_acc -= int(tick_acc)
        for _ in range(n):
            sim.update(params)

        screen.fill(BLACK)
        draw_all(screen, sim, layout, fonts, speed_sl, param_sliders)
        draw_legend(screen, layout, fonts[0])
        pygame.display.flip()


if __name__ == "__main__":
    main()
