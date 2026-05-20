# world/plant.py — растение
# Растения — основной источник энергии для травоядных и падальщиков.
# Энергия растёт каждый тик; при достижении 0 растение умирает.

import random
import pygame
from constants import CELL


class Plant:
    MAX_E = 60   # максимальный запас энергии растения

    def __init__(self, x: int, y: int, energy: float = None):
        self.x, self.y = x, y
        self.energy = energy if energy is not None else random.uniform(8, self.MAX_E)
        self.alive  = True

    def update(self, grow_rate: float):
        """Прирост энергии за тик. grow_rate < 0 зимой (растение вянет)."""
        self.energy = max(0.0, min(self.MAX_E, self.energy + grow_rate))
        if self.energy <= 0:
            self.alive = False

    def draw(self, surf: pygame.Surface):
        frac = self.energy / self.MAX_E
        r    = max(2, int(frac * 4))
        g    = int(80 + frac * 160)
        pygame.draw.circle(surf, (0, g, 0),
                           (self.x * CELL + CELL // 2,
                            self.y * CELL + CELL // 2), r)
