# world/corpse.py — труп животного
# Появляется при гибели любого животного (травоядного, хищника, падальщика).
# Энергия трупа убывает со временем; падальщики находят трупы по зрению.
# По истечении CORPSE_LIFETIME тиков труп исчезает.

import math
import pygame
from constants import CELL, CORPSE_LIFETIME


class Corpse:
    def __init__(self, x: float, y: float, energy: float):
        self.x, self.y = float(x), float(y)
        self.energy    = float(max(6.0, energy))
        self.max_e     = self.energy
        self.life      = CORPSE_LIFETIME
        self.alive     = True

    # Расстояние до другого объекта с атрибутами .x, .y
    def dist(self, o) -> float:
        return math.hypot(self.x - o.x, self.y - o.y)

    def update(self):
        """Гниение: энергия убывает пропорционально оставшемуся времени жизни."""
        self.life  -= 1
        self.energy = self.max_e * (self.life / CORPSE_LIFETIME)
        if self.life <= 0 or self.energy < 1.0:
            self.alive = False

    def draw(self, surf: pygame.Surface):
        cx  = int(self.x * CELL + CELL // 2)
        cy  = int(self.y * CELL + CELL // 2)
        frac = max(0.0, self.life / CORPSE_LIFETIME)
        r    = max(2, int(3 * frac + 1))
        col  = (int(110 * frac), int(75 * frac), int(30 * frac))
        pygame.draw.line(surf, col, (cx - r, cy - r), (cx + r, cy + r), 2)
        pygame.draw.line(surf, col, (cx + r, cy - r), (cx - r, cy + r), 2)
        pygame.draw.circle(surf, col, (cx, cy), max(1, r // 2))
