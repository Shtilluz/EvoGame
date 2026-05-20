#!/usr/bin/env python3
# main.py — точка входа в симулятор эволюции
# Запуск: python main.py
import sys
import math
import random
import pygame

from constants import FPS, BLACK, GREEN, RED, BROWN, CYAN
from params import SimParams, Layout
from simulation.core import Simulation
from animals import Herbivore, Predator, Scavenger
from ui.slider import Slider
from rendering.renderer import draw_all, draw_legend


def main():
    pygame.init()

    def load_font(size, bold=False):
        for name in ("DejaVu Sans", "FreeSans", "Liberation Sans", "Arial", None):
            try:
                if name: return pygame.font.SysFont(name, size, bold=bold)
            except Exception:
                pass
        return pygame.font.Font(None, size + 4)

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
               fmt=lambda v: f"{int(v)}%",          color=(180, 255, 100)),
        Slider("Величина мут.", 5,  80, 18, step=1,
               fmt=lambda v: f"σ={int(v)/100:.2f}", color=(180, 255, 100)),
        Slider("Голод трав.",   1,  30,  3, step=1,
               fmt=lambda v: f"{int(v)/100:.2f}",   color=GREEN),
        Slider("Голод хищн.",   1,  50,  6, step=1,
               fmt=lambda v: f"{int(v)/100:.2f}",   color=RED),
        Slider("Жажда",        20, 300, 100, step=10,
               fmt=lambda v: f"{int(v)}%",          color=(100, 180, 255)),
        Slider("Порог вида",    3,  25,  10, step=1,
               fmt=lambda v: f"{int(v)} мут.",      color=CYAN),
    ]

    all_sliders  = [speed_sl] + param_sliders
    dragging     = None
    restart_rect = None   # Rect кнопки рестарта в зале славы

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

                # Кнопка рестарта в зале славы
                if sim.game_over and restart_rect and restart_rect.collidepoint(mx, my):
                    sim = Simulation(layout)
                    restart_rect = None
                    continue

                if sim.game_over:
                    continue

                # Переключение вкладок
                if mx >= layout.panel_x and 50 <= my <= 85:
                    tab_ids = ["INFO", "SPECIES", "SETTINGS", "GRAPH", "INSPECTOR"]
                    idx = (mx - layout.panel_x) // (layout.panel_w // len(tab_ids))
                    if 0 <= idx < len(tab_ids):
                        sim.ui_tab = tab_ids[idx]
                        dragging = None

                # Выбор животного в мире
                elif mx < layout.world_w:
                    cx, cy = mx / 8, my / 8   # пиксели → ячейки (CELL=8)
                    all_anim = sim.herbs + sim.preds + sim.scavs + sim.omnis
                    best, bd = None, 2.5
                    for a in all_anim:
                        if a.alive:
                            d = math.hypot(a.x - cx, a.y - cy)
                            if d < bd: best, bd = a, d
                    if best:
                        sim.selected_animal = best
                        sim.ui_tab = "INSPECTOR"
                    else:
                        sim.selected_animal = None

                # Взаимодействие со слайдерами
                else:
                    target_sliders = []
                    if sim.ui_tab == "INFO":      target_sliders = [speed_sl]
                    elif sim.ui_tab == "SETTINGS": target_sliders = param_sliders
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
                            random.randint(3, layout.cols - 3),
                            random.randint(3, layout.rows - 3)))
                    sim._log("Добавлено 8 травоядных", GREEN)
                elif k == pygame.K_x or u == 'х':
                    for _ in range(3):
                        sim.preds.append(Predator(
                            random.randint(3, layout.cols - 3),
                            random.randint(3, layout.rows - 3)))
                    sim._log("Добавлено 3 хищника", RED)
                elif k == pygame.K_s or u == 'с':
                    for _ in range(5):
                        sim.scavs.append(Scavenger(
                            random.randint(3, layout.cols - 3),
                            random.randint(3, layout.rows - 3)))
                    sim._log("Добавлено 5 падальщиков", BROWN)
                elif k == pygame.K_r:
                    sim = Simulation(layout)
                    restart_rect = None

        dt = clock.get_time() / 1000.0
        tick_acc += dt * BASE_TPS * speed_sl.value
        n = min(int(tick_acc), 12)
        tick_acc -= int(tick_acc)
        for _ in range(n):
            sim.update(params)

        screen.fill(BLACK)
        restart_rect = draw_all(screen, sim, layout, fonts, speed_sl, param_sliders)
        if not sim.game_over:
            draw_legend(screen, layout, fonts[0])
        pygame.display.flip()


if __name__ == "__main__":
    main()
