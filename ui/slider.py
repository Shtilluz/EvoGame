# ui/slider.py — интерактивный виджет-слайдер
# Позволяет изменять параметры симуляции в реальном времени.
# Поддерживает два режима отрисовки: полный (с меткой над дорожкой) и компактный (однострочный).
import pygame

from constants import WHITE, LIGHT_GRAY, CYAN


class Slider:
    """Горизонтальный слайдер с перетаскиваемой кнопкой."""

    def __init__(self, label: str, lo, hi, value, step=1, fmt=None, color=CYAN):
        self.label = label
        self.lo    = float(lo)
        self.hi    = float(hi)
        self.value = float(value)
        self.step  = float(step)
        self.fmt   = fmt or (lambda v: f"{int(v)}" if step >= 1 else f"{v:.2f}")
        self.color = color
        # Запоминаются при отрисовке — используются для хит-теста и перетаскивания
        self._hit_rect    = pygame.Rect(0, 0, 0, 0)
        self._track_scr_x = 0   # экранный X левого края дорожки
        self._track_scr_w = 1   # ширина дорожки в экранных пикселях

    # ── Полный режим (метка сверху, крупная кнопка) ────────────────────────────
    def draw_full(self, surf, panel_scr_x: int, x: int, y: int, w: int, font, extra: str = ""):
        """panel_scr_x — экранный X панели (панель всегда на scr_y=0)."""
        knob_r, track_h = 8, 8
        lbl = font.render(f"{self.label}: {self.fmt(self.value)}{extra}", True, WHITE)
        surf.blit(lbl, (x, y - lbl.get_height() - 2))
        self._draw_track(surf, x, y, w, track_h, knob_r)
        self._track_scr_x = panel_scr_x + x
        self._track_scr_w = w
        self._hit_rect = pygame.Rect(panel_scr_x + x - knob_r, y - knob_r,
                                     w + knob_r * 2, track_h + knob_r * 2)
        return self._hit_rect

    # ── Компактный режим (одна строка: метка | дорожка | значение) ─────────────
    def draw_compact(self, surf, panel_scr_x: int, x: int, y: int, w: int, font):
        """panel_scr_x — экранный X панели."""
        knob_r, track_h = 6, 6
        label_s = font.render(self.label + ":", True, LIGHT_GRAY)
        value_s = font.render(self.fmt(self.value), True, self.color)
        lw = label_s.get_width() + 6
        vw = value_s.get_width() + 4
        tw = max(20, w - lw - vw)
        ty = y + (label_s.get_height() - track_h) // 2
        surf.blit(label_s, (x, y))
        surf.blit(value_s, (x + lw + tw + 4, y))
        self._draw_track(surf, x + lw, ty, tw, track_h, knob_r)
        self._track_scr_x = panel_scr_x + x + lw
        self._track_scr_w = tw
        self._hit_rect = pygame.Rect(panel_scr_x + x + lw - knob_r, ty - knob_r,
                                     tw + knob_r * 2, track_h + knob_r * 2)
        return self._hit_rect

    def _draw_track(self, surf, x: int, y: int, w: int, h: int, knob_r: int):
        frac = (self.value - self.lo) / max(1e-9, self.hi - self.lo)
        fw   = int(w * frac)
        pygame.draw.rect(surf, (50, 50, 65), (x, y, w, h), border_radius=3)
        if fw > 0:
            pygame.draw.rect(surf, self.color, (x, y, fw, h), border_radius=3)
        kx, ky = x + fw, y + h // 2
        pygame.draw.circle(surf, WHITE,      (kx, ky), knob_r)
        pygame.draw.circle(surf, self.color, (kx, ky), knob_r - 2)

    def set_from_mouse(self, mouse_x: int):
        """Установить значение по экранной X-координате мыши."""
        rel   = mouse_x - self._track_scr_x
        frac  = max(0.0, min(1.0, rel / max(1, self._track_scr_w)))
        steps = round(frac * (self.hi - self.lo) / self.step)
        self.value = max(self.lo, min(self.hi, self.lo + steps * self.step))

    def hit(self, scr_pos) -> bool:
        """Проверить, попадает ли экранная позиция в зону слайдера."""
        return self._hit_rect.collidepoint(scr_pos)
