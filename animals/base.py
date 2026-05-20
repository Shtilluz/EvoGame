# animals/base.py — базовый класс всех животных симуляции
import math
import random
import pygame

from constants import (
    SEASONS, DIET_CARN_THRESH, DIET_HERB_THRESH,
    MUTABLE_TRAITS, CELL, WHITE, GREEN, new_species_name,
)
from params import SimParams


class Animal:
    """Базовый класс для всех видов животных.

    Содержит общую логику: движение, метаболизм, размножение, отрисовка полосок.
    Конкретные виды (Herbivore, Predator, ...) наследуют и переопределяют update/spawn/draw.
    """

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
        self.fat            = 0.0
        self.MAX_FAT        = self.size * 50.0
        self.base_speed     = base_speed  or speed
        self.base_vision    = base_vision or vision
        self.base_size      = base_size   or size
        self.diet           = diet if diet is not None else self._default_diet()
        self.endurance      = endurance if endurance is not None else 0.0
        self.herd_instinct  = herd_instinct if herd_instinct is not None else random.uniform(0, 0.3)
        a = random.uniform(0, 2 * math.pi)
        self.dx, self.dy = math.cos(a), math.sin(a)
        self._recalc_costs()

    # ── Видимость / камуфляж ──────────────────────────────────────────────────
    def get_visibility(self, season_idx: int) -> float:
        """Множитель заметности животного (0.3 = хороший камуфляж, 1.2 = очень заметно)."""
        bg_color = SEASONS[season_idx][4]
        dist = sum((self.color[i] - bg_color[i]) ** 2 for i in range(3)) ** 0.5
        return max(0.3, min(1.2, dist / 160.0))

    def _default_diet(self) -> float:
        return 0.15   # переопределяется подклассом

    # ── Свойства рациона ──────────────────────────────────────────────────────
    @property
    def eats_plants(self) -> bool:
        return self.diet <= DIET_CARN_THRESH

    @property
    def eats_animals(self) -> bool:
        return self.diet >= DIET_HERB_THRESH

    @property
    def diet_label(self) -> str:
        if self.diet <= DIET_HERB_THRESH: return "травоядное"
        if self.diet >= DIET_CARN_THRESH: return "хищник"
        return "всеядное"

    # ── Метаболизм ────────────────────────────────────────────────────────────
    def _recalc_costs(self):
        """Пересчитать расходы энергии и жажды с учётом трейтов."""
        base_ecost   = self.speed ** 1.5 * 0.022 + self.size ** 1.3 * 0.018 + self.vision * 0.0012
        base_thirst  = 0.10 + self.speed * 0.04 + self.size * 0.03
        fat_ratio    = self.fat / max(1, self.MAX_FAT)
        fat_speed_penalty = fat_ratio * 0.25
        fat_cost_penalty  = fat_ratio * 0.40
        end          = getattr(self, 'endurance', 0.0)
        end_discount = end * 0.45
        self.ecost        = base_ecost  * (1.0 - end_discount) * (1.0 + fat_cost_penalty)
        self.thirst_drain = base_thirst * (1.0 - end_discount)
        self.eff_speed    = self.speed  * (1.0 - end * 0.35) * (1.0 - fat_speed_penalty)

    def _metabolism(self, season_idx: int):
        """Обмен веществ: жир накапливается при избытке, сжигается при нехватке. Зимой — холодовые потери."""
        if self.energy > self.MAX_E * 0.8:
            can_add = self.MAX_FAT - self.fat
            amount  = min(0.15, can_add)
            self.fat    += amount
            self.energy -= amount * 0.8
        elif self.energy < self.MAX_E * 0.3 and self.fat > 0:
            amount = min(0.25, self.fat)
            self.fat    -= amount
            self.energy += amount * 1.5
        if season_idx == 3:   # Зима — холод
            cold_drain = 0.04 * (1.0 - (self.fat / max(1, self.MAX_FAT)))
            self.energy -= max(0, cold_drain)
        self._recalc_costs()

    # ── Движение ──────────────────────────────────────────────────────────────
    def dist(self, o) -> float:
        return math.hypot(self.x - o.x, self.y - o.y)

    def dist_xy(self, tx: float, ty: float) -> float:
        return math.hypot(self.x - tx, self.y - ty)

    def toward(self, tx: float, ty: float):
        dx, dy = tx - self.x, ty - self.y
        m = math.hypot(dx, dy)
        if m: self.dx, self.dy = dx / m, dy / m

    def away(self, tx: float, ty: float):
        dx, dy = self.x - tx, self.y - ty
        m = math.hypot(dx, dy)
        if m: self.dx, self.dy = dx / m, dy / m

    def wander(self):
        """Случайное блуждание; высокая выносливость даёт более прямолинейный ход."""
        end   = getattr(self, 'endurance', 0.0)
        sigma = 0.6 - end * 0.35
        if random.random() < 0.04:
            a = math.atan2(self.dy, self.dx) + random.gauss(0, sigma)
            self.dx, self.dy = math.cos(a), math.sin(a)

    def step(self, cols: int, rows: int):
        sp = getattr(self, 'eff_speed', self.speed)
        self.x = max(0.0, min(cols - 1.0, self.x + self.dx * sp))
        self.y = max(0.0, min(rows - 1.0, self.y + self.dy * sp))
        if self.x <= 0 or self.x >= cols - 1: self.dx *= -1
        if self.y <= 0 or self.y >= rows - 1: self.dy *= -1

    def step_toward(self, tx: float, ty: float, cols: int, rows: int):
        """Двигаться к цели без перелёта."""
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-4: return
        sp   = getattr(self, 'eff_speed', self.speed)
        move = min(sp, dist)
        self.dx, self.dy = dx / dist, dy / dist
        self.x = max(0.0, min(cols - 1.0, self.x + self.dx * move))
        self.y = max(0.0, min(rows - 1.0, self.y + self.dy * move))
        if self.x <= 0 or self.x >= cols - 1: self.dx *= -1
        if self.y <= 0 or self.y >= rows - 1: self.dy *= -1

    # ── Поиск ────────────────────────────────────────────────────────────────
    def nearest(self, seq, max_d: float):
        """Ближайший объект из seq в радиусе max_d. Возвращает (объект, расстояние)."""
        best, bd = None, max_d
        for o in seq:
            d = self.dist(o)
            if d < bd: best, bd = o, d
        return best, bd

    def nearest_water(self, sources):
        """Ближайший источник воды."""
        best, bd = None, float("inf")
        for ws in sources:
            d = self.dist_xy(ws.x, ws.y)
            if d < bd: best, bd = ws, d
        return best, bd

    # ── Размножение ───────────────────────────────────────────────────────────
    def can_reproduce(self) -> bool:
        return (self.energy > self.MAX_E * 0.65
                and self.hydration > 45
                and self.rep_cd <= 0
                and self.age > 120)

    # ── Отрисовка ─────────────────────────────────────────────────────────────
    def _draw_bar(self, surf, cx: int, cy: int, r: int, value: float, maxi: float, color):
        w = r * 2; bx, by = cx - r, cy - r - 5
        pygame.draw.rect(surf, (40, 40, 40), (bx, by, w, 3))
        pygame.draw.rect(surf, color, (bx, by, int(w * max(0, value / maxi)), 3))

    # ── Видообразование ───────────────────────────────────────────────────────
    def _speciate_name_color(self, kind: str):
        """Сгенерировать имя и цвет для нового подвида."""
        name  = new_species_name(kind)
        color = [(self.color[i] + random.randint(0, 255)) // 2 for i in range(3)]
        return name, color
