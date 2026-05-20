# world/water.py — источник воды
# Статичный объект. Животные пьют из него при низкой гидратации.
# При изменении размера окна нужно вызвать rebuild() заново.

import pygame
from constants import CELL, BLUE, LIGHT_BLUE


class WaterSource:
    def __init__(self, x: int, y: int, radius: int = 4):
        self.x, self.y  = x, y
        self.radius     = radius
        self.rects: list = []   # кэш пикселей для быстрой отрисовки

    def rebuild(self, world_w: int, world_h: int):
        """Пересчитать список прямоугольников после изменения размера окна."""
        self.rects = []
        r2 = self.radius ** 2
        for dx in range(-self.radius, self.radius + 1):
            for dy in range(-self.radius, self.radius + 1):
                if dx * dx + dy * dy <= r2:
                    px = (self.x + dx) * CELL
                    py = (self.y + dy) * CELL
                    if 0 <= px < world_w - CELL and 0 <= py < world_h - CELL:
                        self.rects.append((px, py, CELL, CELL))

    def draw(self, surf: pygame.Surface):
        for r in self.rects:
            pygame.draw.rect(surf, BLUE, r)
        pygame.draw.circle(surf, LIGHT_BLUE,
                           (self.x * CELL + CELL // 2,
                            self.y * CELL + CELL // 2), 3)
