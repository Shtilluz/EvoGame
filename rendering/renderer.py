# rendering/renderer.py — отрисовка мира и информационной панели
import math
import pygame

from constants import (
    BLACK, WHITE, GRAY, LIGHT_GRAY, GREEN, RED, BLUE, BROWN, GOLD, ORANGE,
    YELLOW, CYAN, PINK, LIGHT_BLUE, PANEL_BG, PANEL_SECTION, PANEL_LINE,
    TEXT_DIM, ACCENT, SEASONS, SEASON_TICKS,
    DIET_HERB_THRESH, DIET_CARN_THRESH, CELL,
)
from params import Layout
from simulation.core import Simulation
from ui.slider import Slider


# ─── Зал славы ────────────────────────────────────────────────────────────────

def draw_hall_of_fame(screen, sim: Simulation, layout: Layout, fonts) -> pygame.Rect:
    """Экран зала славы после полного вымирания. Возвращает Rect кнопки рестарта."""
    fs, fm, fb = fonts
    sw, sh = screen.get_size()
    cx = sw // 2

    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((4, 4, 14, 245))
    screen.blit(overlay, (0, 0))

    y = 22

    title_s = fb.render("М И Р   О П У С Т Е Л", True, (210, 60, 60))
    screen.blit(title_s, (cx - title_s.get_width() // 2, y))
    y += title_s.get_height() + 8

    total_b = (sim.total_births_h + sim.total_births_p
               + sim.total_births_s + sim.total_births_o)
    sub_s = fm.render(
        f"Тик {sim.tick}   ·   Видообразований: {sim.total_speciations}"
        f"   ·   Убийств: {sim.total_kills}   ·   Рождений: {total_b}",
        True, (130, 132, 162))
    screen.blit(sub_s, (cx - sub_s.get_width() // 2, y))
    y += sub_s.get_height() + 16

    hall_s = fb.render("З А Л   С Л А В Ы", True, (200, 168, 52))
    screen.blit(hall_s, (cx - hall_s.get_width() // 2, y))
    y += hall_s.get_height() + 14

    top = sim.top_species(10)

    if not top:
        msg = fm.render("Реестр пуст — слишком быстрое вымирание.", True, GRAY)
        screen.blit(msg, (cx - msg.get_width() // 2, y + 40))
    else:
        margin = 36
        table_w = sw - margin * 2
        col_ratios = [44, 195, 108, 52, 68, 52, 68, 128, 60]
        total_r = sum(col_ratios)
        col_ws = [int(r * table_w / total_r) for r in col_ratios]
        col_xs = [margin]
        for w in col_ws[:-1]:
            col_xs.append(col_xs[-1] + w)

        headers = ["#", "ВИД", "ТИП", "Пик", "Тиков", "Пок.", "Убийств", "Ск/Зр/Рз", "Очки"]
        for hdr, hx in zip(headers, col_xs):
            screen.blit(fs.render(hdr, True, (160, 162, 205)), (hx, y))
        y += fs.get_height() + 4
        pygame.draw.line(screen, (60, 65, 98), (margin, y), (sw - margin, y))
        y += 6

        kind_colors = {'herb': GREEN, 'pred': RED, 'scav': BROWN, 'omni': GOLD}
        row_h = fs.get_height() + 7

        for rank, rec in enumerate(top, 1):
            if y + row_h > sh - 90:
                break
            if rank % 2 == 0:
                rb = pygame.Surface((table_w, row_h), pygame.SRCALPHA)
                rb.fill((255, 255, 255, 10))
                screen.blit(rb, (margin, y))

            if rank == 1:   row_col = (240, 200, 55)
            elif rank == 2: row_col = (200, 200, 205)
            elif rank == 3: row_col = (190, 138, 75)
            else:           row_col = (142, 142, 148)

            kc = kind_colors.get(rec.kind, WHITE)
            sw_r = pygame.Rect(col_xs[0], y + 2, 14, row_h - 4)
            pygame.draw.rect(screen, tuple(min(255, v) for v in rec.color[:3]), sw_r, border_radius=3)
            pygame.draw.rect(screen, (175, 175, 175), sw_r, 1, border_radius=3)

            def cell(text, xi, color):
                screen.blit(fs.render(str(text), True, color), (xi, y))

            cell(str(rank), col_xs[0] + 18, row_col)
            cell(rec.name[:24], col_xs[1], row_col)
            cell(rec.kind_label, col_xs[2], kc)
            cell(rec.peak_pop, col_xs[3], WHITE)
            cell(rec.lifespan, col_xs[4], LIGHT_GRAY)
            cell(rec.best_generation, col_xs[5], CYAN)
            cell(rec.total_kills, col_xs[6], ORANGE)
            cell(f"{rec.avg_speed:.1f} / {rec.avg_vision:.1f} / {rec.avg_size:.1f}", col_xs[7], LIGHT_GRAY)
            cell(rec.score, col_xs[8], GOLD)
            y += row_h

    btn_w, btn_h = 280, 46
    btn_x = cx - btn_w // 2
    btn_y = sh - btn_h - 28
    btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
    pulse = int(abs(math.sin(pygame.time.get_ticks() / 700)) * 30)
    btn_col = (45 + pulse, 125 + pulse // 2, 45 + pulse)
    pygame.draw.rect(screen, (14, 16, 28), btn_rect.inflate(4, 4), border_radius=11)
    pygame.draw.rect(screen, btn_col, btn_rect, border_radius=9)
    pygame.draw.rect(screen, WHITE, btn_rect, 1, border_radius=9)
    btn_lbl = fb.render("ПЕРЕЗАПУСТИТЬ", True, WHITE)
    screen.blit(btn_lbl, (cx - btn_lbl.get_width() // 2,
                           btn_y + (btn_h - btn_lbl.get_height()) // 2))
    hint_s = fs.render("или нажмите  R", True, (90, 92, 115))
    screen.blit(hint_s, (cx - hint_s.get_width() // 2, btn_y + btn_h + 6))

    return btn_rect


# ─── Главный рендер ───────────────────────────────────────────────────────────

def draw_all(screen, sim: Simulation, layout: Layout, fonts,
             speed_sl: Slider, param_sliders: list):
    """Отрисовать весь кадр. Возвращает Rect кнопки рестарта или None."""
    if sim.game_over:
        return draw_hall_of_fame(screen, sim, layout, fonts)

    fs, fm, fb = fonts
    L = layout

    # ── Мировое поле ─────────────────────────────────────────────────────────
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

    pygame.draw.rect(screen, PANEL_LINE, (0, 0, L.world_w, L.world_h), 2)

    # Сезонный баннер
    bnr = fs.render(f"  {sname}  ", True, BLACK)
    bw, bh = bnr.get_width() + 4, bnr.get_height() + 6
    bsurf = pygame.Surface((bw, bh), pygame.SRCALPHA)
    r, g, b = s_color
    pygame.draw.rect(bsurf, (r, g, b, 220), (0, 0, bw, bh), border_radius=5)
    bsurf.blit(bnr, (2, 3))
    world_surf.blit(bsurf, (6, 6))
    prog_w = int(bw * sim.season_progress)
    pygame.draw.rect(world_surf, (0, 0, 0, 80), (6, bh + 8, bw, 3), border_radius=1)
    if prog_w > 0:
        pygame.draw.rect(world_surf, s_color, (6, bh + 8, prog_w, 3), border_radius=1)

    tck_s = fs.render(f"тик {sim.tick}", True, (130, 138, 165))
    world_surf.blit(tck_s, (L.world_w - tck_s.get_width() - 8, 8))

    # ── Панель ───────────────────────────────────────────────────────────────
    panel = screen.subsurface((L.panel_x, 0, L.panel_w, L.sh))
    panel.fill(PANEL_BG)
    pygame.draw.line(panel, ACCENT, (0, 0), (0, L.sh), 3)
    px, py = 10, 0
    pw = L.panel_w - px - 8

    # ── Заголовок ────────────────────────────────────────────────────────────
    HDR_H = 50
    pygame.draw.rect(panel, PANEL_SECTION, (0, 0, L.panel_w, HDR_H))
    pygame.draw.rect(panel, PANEL_LINE,    (0, HDR_H, L.panel_w, 1))

    title_s = fb.render("ЭВОЛЮЦИЯ", True, WHITE)
    panel.blit(title_s, (px, 7))

    if sim.paused:
        st_str, st_col = f"тик {sim.tick}  ⏸ ПАУЗА", YELLOW
    else:
        st_str, st_col = f"тик {sim.tick}  ▶ {int(10 * speed_sl.value)} тик/с", (95, 215, 105)
    panel.blit(fs.render(st_str, True, st_col), (px, 7 + title_s.get_height() + 3))

    year = sim.tick // (SEASON_TICKS * 4) + 1
    yr_s = fs.render(f"Год {year}", True, TEXT_DIM)
    panel.blit(yr_s, (L.panel_w - yr_s.get_width() - 8, 18))

    py = HDR_H + 2

    # ── Вкладки ──────────────────────────────────────────────────────────────
    TABS = [("ИНФО", "INFO"), ("ВИДЫ", "SPECIES"), ("НАСТР", "SETTINGS"),
            ("ГРАФ", "GRAPH"), ("ОБЪЕКТ", "INSPECTOR")]
    TAB_H = 26
    tw = L.panel_w // len(TABS)
    for i, (name, tid) in enumerate(TABS):
        tx = i * tw
        active = (sim.ui_tab == tid)
        pygame.draw.rect(panel, PANEL_SECTION if active else PANEL_BG,
                         (tx, py, tw, TAB_H))
        if active:
            pygame.draw.rect(panel, ACCENT, (tx, py + TAB_H - 2, tw, 2))
        elif i > 0:
            pygame.draw.line(panel, PANEL_LINE, (tx, py + 4), (tx, py + TAB_H - 4))
        t_s = fs.render(name, True, WHITE if active else TEXT_DIM)
        panel.blit(t_s, (tx + (tw - t_s.get_width()) // 2,
                          py + (TAB_H - t_s.get_height()) // 2))
    py += TAB_H
    pygame.draw.line(panel, PANEL_LINE, (0, py), (L.panel_w, py))
    py += 8

    # ── Вспомогательные функции ───────────────────────────────────────────────
    def txt(s, color=LIGHT_GRAY, f=None, indent=0):
        nonlocal py
        if py > L.sh - 55: return
        surf = (f or fs).render(s, True, color)
        panel.blit(surf, (px + indent, py))
        py += surf.get_height() + 2

    def gap(n=5):
        nonlocal py
        py += n

    def section(title, color=ACCENT):
        nonlocal py
        py += 5
        if py > L.sh - 55: return
        pygame.draw.rect(panel, color, (px, py, 3, fs.get_height() + 2))
        panel.blit(fs.render(title, True, color), (px + 7, py))
        py += fs.get_height() + 2
        pygame.draw.line(panel, PANEL_LINE, (px, py), (L.panel_w - 8, py))
        py += 6

    def pop_bar(label, count, max_count, color):
        nonlocal py
        if py > L.sh - 55: return
        rh = fs.get_height() + 5
        cy = py + rh // 2
        pygame.draw.circle(panel, color, (px + 5, cy), 4)
        panel.blit(fs.render(label, True, LIGHT_GRAY), (px + 13, py + (rh - fs.get_height()) // 2))
        bar_x, bar_w, bar_h = px + 108, pw - 108 - 30, 5
        pygame.draw.rect(panel, (22, 26, 48), (bar_x, cy - 2, bar_w, bar_h), border_radius=2)
        if max_count > 0 and count > 0:
            fw = max(2, int(bar_w * min(1.0, count / max_count)))
            pygame.draw.rect(panel, color, (bar_x, cy - 2, fw, bar_h), border_radius=2)
        cs = fs.render(str(count), True, color if count else TEXT_DIM)
        panel.blit(cs, (px + pw - cs.get_width(), py + (rh - cs.get_height()) // 2))
        py += rh

    def stat2(left, lc, right, rc):
        nonlocal py
        if py > L.sh - 55: return
        ls = fs.render(left, True, lc)
        rs = fs.render(right, True, rc)
        panel.blit(ls, (px, py))
        panel.blit(rs, (px + pw // 2, py))
        py += ls.get_height() + 3

    # ── INFO ──────────────────────────────────────────────────────────────────
    if sim.ui_tab == "INFO":
        s_idx = sim.season_idx
        cell_w = pw // 4
        for i, (sn, *_, sc) in enumerate(SEASONS):
            active = (i == s_idx)
            bx = px + i * cell_w
            r2, g2, b2 = sc
            bg2 = (r2 // 3, g2 // 3, b2 // 3) if active else (r2 // 7, g2 // 7, b2 // 7)
            pygame.draw.rect(panel, bg2, (bx, py, cell_w - 2, 18), border_radius=4)
            if active:
                pygame.draw.rect(panel, sc, (bx, py, cell_w - 2, 18), 1, border_radius=4)
            sns = fs.render(sn, True, sc if active else TEXT_DIM)
            panel.blit(sns, (bx + (cell_w - sns.get_width()) // 2, py + 2))
        py += 22
        prog_w2 = int(pw * sim.season_progress)
        pygame.draw.rect(panel, PANEL_LINE, (px, py, pw, 3), border_radius=1)
        if prog_w2 > 0:
            pygame.draw.rect(panel, s_color, (px, py, prog_w2, 3), border_radius=1)
        py += 9

        section("СКОРОСТЬ")
        speed_sl.draw_compact(panel, L.panel_x, px, py, pw, fs)
        py += 22

        section("ПОПУЛЯЦИЯ")
        max_pop = max(len(sim.herbs), len(sim.preds), len(sim.scavs), len(sim.omnis), 1)
        pop_bar("Травоядные", len(sim.herbs), max_pop, GREEN)
        pop_bar("Хищники",    len(sim.preds), max_pop, RED)
        pop_bar("Падальщики", len(sim.scavs), max_pop, BROWN)
        pop_bar("Всеядные",   len(sim.omnis), max_pop, GOLD)
        gap(2)
        txt(f"Растений: {len(sim.plants)}    Трупов: {len(sim.corpses)}", TEXT_DIM)

        def avg(seq, attr):
            return sum(getattr(a, attr) for a in seq) / len(seq) if seq else 0.0

        section("СРЕДНИЕ ПОКАЗАТЕЛИ")
        for seq, color, lbl in [
            (sim.herbs, GREEN, "Трав"),
            (sim.preds, RED,   "Хищн"),
            (sim.scavs, BROWN, "Пад "),
            (sim.omnis, GOLD,  "Всеяд"),
        ]:
            if seq:
                txt(f"{lbl}  ск{avg(seq,'speed'):.2f}  зр{avg(seq,'vision'):.1f}"
                    f"  рз{avg(seq,'size'):.1f}  пок{avg(seq,'generation'):.0f}", color)

        section("СТАТИСТИКА")
        total_b = (sim.total_births_h + sim.total_births_p
                   + sim.total_births_s + sim.total_births_o)
        stat2(f"Рождений: {total_b}", (115, 220, 115),
              f"Смертей: {sim.total_deaths}", GRAY)
        stat2(f"Убийств:  {sim.total_kills}", ORANGE,
              f"Видообр.: {sim.total_speciations}", CYAN)

        section("СОБЫТИЯ")
        for ev in reversed(sim.events[-9:]):
            if py > L.sh - 100: break
            alpha = min(255, ev[2] * 3)
            c = tuple(min(255, int(ch * alpha / 255)) for ch in ev[1])
            panel.blit(fs.render("· " + ev[0][:44], True, c), (px, py))
            py += 14

        # Управление — фиксированная нижняя панель
        ctrl_y = L.sh - 78
        pygame.draw.rect(panel, PANEL_SECTION, (0, ctrl_y - 5, L.panel_w, L.sh))
        pygame.draw.line(panel, PANEL_LINE, (0, ctrl_y - 5), (L.panel_w, ctrl_y - 5))
        ctrls = [
            ("ПРОБЕЛ", "пауза"),  ("R",     "рестарт"),
            ("Н",      "+трав."), ("Х",     "+хищн."),
            ("С",      "+пад."),  ("F11",   "экран"),
            ("Q/ESC",  "выход"),
        ]
        for i, (key, desc) in enumerate(ctrls):
            bx = px + (i % 2) * (pw // 2)
            ky = ctrl_y + (i // 2) * 14
            ks = fs.render(key, True, YELLOW)
            ds = fs.render(f" {desc}", True, TEXT_DIM)
            panel.blit(ks, (bx, ky))
            panel.blit(ds, (bx + ks.get_width(), ky))

    # ── SETTINGS ─────────────────────────────────────────────────────────────
    elif sim.ui_tab == "SETTINGS":
        txt("ПАРАМЕТРЫ СИМУЛЯЦИИ", WHITE, fb)
        gap(6)
        groups = [
            ("ГЕНЕТИКА",  [0, 1],   (100, 220, 120)),
            ("ЭКОЛОГИЯ",  [2, 3, 4], (100, 175, 255)),
            ("ЭВОЛЮЦИЯ",  [5],       CYAN),
        ]
        for g_title, indices, g_color in groups:
            section(g_title, g_color)
            for i in indices:
                param_sliders[i].draw_compact(panel, L.panel_x, px, py, pw, fs)
                py += 28
        gap(8)
        txt("Изменения применяются мгновенно.", TEXT_DIM)

    # ── SPECIES ───────────────────────────────────────────────────────────────
    elif sim.ui_tab == "SPECIES":
        txt("ЖИВЫЕ ВИДЫ И ПОДВИДЫ", WHITE, fb)
        gap(4)
        thresh = int(param_sliders[5].value)

        def sp_stats(grp):
            n = len(grp)
            return (
                sum(a.speed for a in grp) / n,
                sum(a.size for a in grp) / n,
                sum(a.vision for a in grp) / n,
                sum(a.generation for a in grp) / n,
                sum(a.endurance for a in grp) / n,
            )

        def get_subgroups(entities):
            groups = {}
            for e in entities:
                key = (e.species_name, e.mutation_count)
                groups.setdefault(key, []).append(e)
            return sorted(groups.items(), key=lambda x: (x[0][0], -x[0][1]))

        def draw_species_block(active, label_color):
            nonlocal py
            for (name, mc), grp in active:
                if py > L.sh - 70: break
                if mc > 0:
                    txt(f"  · {name}  ×{len(grp)}", label_color)
                    prog = min(1.0, mc / thresh)
                    pygame.draw.rect(panel, (28, 32, 54), (px + 8, py, 100, 4))
                    pygame.draw.rect(panel, CYAN, (px + 8, py, int(100 * prog), 4))
                    mc_s = fs.render(f"мут {mc}/{thresh}", True, (75, 160, 218))
                    panel.blit(mc_s, (px + 112, py - 1))
                    py += 7
                else:
                    txt(f"  {name}  ×{len(grp)}", WHITE)
                t = sp_stats(grp)
                sp2, sz2, vs2, gn2, en2 = t
                txt(f"    ск:{sp2:.1f}  зр:{vs2:.0f}  рз:{sz2:.1f}  пок:{gn2:.0f}", GRAY)
                gap(3)

        for population, label, color in [
            (sim.herbs, "ТРАВОЯДНЫЕ", GREEN),
            (sim.preds, "ХИЩНИКИ",    RED),
            (sim.scavs, "ПАДАЛЬЩИКИ", BROWN),
            (sim.omnis, "ВСЕЯДНЫЕ",   GOLD),
        ]:
            groups = get_subgroups(population)
            if groups:
                section(f"{label}  ({len(groups)})", color)
                draw_species_block(groups, LIGHT_GRAY)

    # ── GRAPH ─────────────────────────────────────────────────────────────────
    elif sim.ui_tab == "GRAPH":
        txt("ДИНАМИКА ПОПУЛЯЦИИ", WHITE, fb)
        gap(4)
        graph_h = min(220, L.sh // 3)
        graph_w = pw
        graph_y = py
        pygame.draw.rect(panel, (7, 8, 20), (px, py, graph_w, graph_h))

        max_v = max(
            max(sim.history["h"] or [1]),
            max(sim.history["p"] or [1]),
            max(sim.history["s"] or [0]),
            max(sim.history["o"] or [0]), 1)

        for frac in (0.25, 0.5, 0.75):
            gy = graph_y + int(graph_h * (1 - frac))
            pygame.draw.line(panel, (22, 28, 50), (px, gy), (px + graph_w, gy))
            lv = fs.render(str(int(max_v * frac)), True, (48, 54, 80))
            panel.blit(lv, (px + 2, gy - lv.get_height()))

        def draw_graph(data, color):
            if len(data) < 2 or max_v == 0: return
            step = graph_w / (len(data) - 1)
            pts = []
            for i, v in enumerate(data):
                gx = px + int(i * step)
                gy = max(graph_y, min(graph_y + graph_h,
                                      graph_y + graph_h - int(v / max_v * graph_h)))
                pts.append((gx, gy))
            pygame.draw.lines(panel, color, False, pts, 2)
            if pts:
                pygame.draw.circle(panel, color, pts[-1], 4)

        draw_graph(sim.history["h"], GREEN)
        draw_graph(sim.history["p"], RED)
        draw_graph(sim.history["s"], BROWN)
        draw_graph(sim.history["o"], GOLD)
        pygame.draw.rect(panel, PANEL_LINE, (px, graph_y, graph_w, graph_h), 1)
        py += graph_h + 10

        section("ТЕКУЩИЕ ЗНАЧЕНИЯ")
        for color, name, data in [
            (GREEN, "Травоядные", sim.history["h"]),
            (RED,   "Хищники",    sim.history["p"]),
            (BROWN, "Падальщики", sim.history["s"]),
            (GOLD,  "Всеядные",   sim.history["o"]),
        ]:
            cur = data[-1] if data else 0
            stat2(f"● {name}", color, str(cur), color)
        gap(6)
        txt(f"Макс. на графике: {int(max_v)}", TEXT_DIM)

    # ── INSPECTOR ─────────────────────────────────────────────────────────────
    elif sim.ui_tab == "INSPECTOR":
        txt("ИНСПЕКТОР", WHITE, fb)
        obj = sim.selected_animal
        if not obj:
            gap(14)
            txt("Животное не выбрано", GRAY)
            gap(4)
            txt("Кликните по животному в мире", TEXT_DIM)
            txt("чтобы увидеть подробности.", TEXT_DIM)
        else:
            kind_colors = {"Herbivore": GREEN, "Predator": RED,
                           "Scavenger": BROWN, "Omnivore": GOLD}
            k_name = type(obj).__name__
            kc = kind_colors.get(k_name, WHITE)

            gap(4)
            txt(obj.species_name, kc if obj.alive else GRAY, fb)
            if not obj.alive:
                txt("† ПОГИБ", RED)
            else:
                txt(f"{k_name}  ·  {obj.diet_label}  ·  пок. {obj.generation}", TEXT_DIM)
                st_c = CYAN if obj.state == "бежит" else (
                    ORANGE if "охотится" in obj.state else kc)
                txt(f"Состояние: {obj.state}", st_c)

            section("РЕСУРСЫ")

            def stat_bar(label, val, maxi, color):
                nonlocal py
                if py > L.sh - 55: return
                pct = max(0.0, min(1.0, val / max(1, maxi)))
                panel.blit(fs.render(f"{label}: {val:.0f} / {maxi:.0f}",
                                     True, LIGHT_GRAY if obj.alive else GRAY), (px, py))
                py += fs.get_height() + 2
                pygame.draw.rect(panel, (20, 24, 46), (px, py, pw, 7), border_radius=3)
                if obj.alive and pct > 0:
                    pygame.draw.rect(panel, color, (px, py, int(pw * pct), 7), border_radius=3)
                py += 11

            stat_bar("Энергия",  obj.energy,    obj.MAX_E,   YELLOW)
            stat_bar("Жажда",    obj.hydration, obj.MAX_H,   BLUE)
            stat_bar("Жир",      obj.fat,       obj.MAX_FAT, (200, 195, 85))

            fat_r = obj.fat / max(1, obj.MAX_FAT)
            if fat_r > 0.1:
                txt(f"  Жир: -{fat_r*25:.0f}% скор  +{fat_r*40:.0f}% расход",
                    (220, 100, 100))
            txt(f"Возраст: {obj.age} / {obj.max_age}", TEXT_DIM)

            section("ГЕНЕТИКА")

            def trait_row(lab, val, base):
                nonlocal py
                if py > L.sh - 55: return
                d = val - base
                d_col = (95, 215, 95) if d >= 0 else (215, 90, 90)
                base_s = fs.render(f"  {lab}: {val:.2f}", True, LIGHT_GRAY)
                delta_s = fs.render(f" ({'+' if d >= 0 else ''}{d:.2f})", True, d_col)
                panel.blit(base_s, (px, py))
                panel.blit(delta_s, (px + base_s.get_width(), py))
                py += base_s.get_height() + 2

            trait_row("Скорость", obj.speed,  obj.base_speed)
            trait_row("Зрение",   obj.vision, obj.base_vision)
            trait_row("Размер",   obj.size,   obj.base_size)
            txt(f"  Стадность:  {obj.herd_instinct:.2f}", LIGHT_GRAY)
            txt(f"  Выносл.:    {obj.endurance:.2f}", LIGHT_GRAY)
            txt(f"  Рацион:     {obj.diet:.2f}  ({obj.diet_label})", LIGHT_GRAY)

            vis = obj.get_visibility(sim.season_idx)
            v_col = GREEN if vis < 0.6 else (YELLOW if vis < 0.9 else RED)
            txt(f"  Заметность: {int(vis*100)}%", v_col)

            section("ИСТОРИЯ")
            txt(f"Детей: {obj.children}    Убийств: {obj.kills}", LIGHT_GRAY)
            txt(f"Мутаций накоплено: {obj.mutation_count}", CYAN)

    # Подсветка выбранного животного
    if sim.selected_animal and sim.selected_animal.alive:
        obj = sim.selected_animal
        sx, sy = int(obj.x * CELL), int(obj.y * CELL)
        r = max(6, int(obj.size * 6))
        pygame.draw.circle(world_surf, WHITE, (sx, sy), r + 2, 1)
        pygame.draw.circle(world_surf, CYAN,  (sx, sy), r + 4, 1)


# ─── Легенда ──────────────────────────────────────────────────────────────────

def draw_legend(screen, layout: Layout, font):
    """Легенда символов в левом нижнем углу мирового поля."""
    items = [
        (GREEN,       "●", "Травоядное"),
        (RED,         "◆", "Хищник"),
        (BROWN,       "●", "Падальщик"),
        ((0, 160, 0), "●", "Растение"),
        (BLUE,        "■", "Вода"),
    ]
    lh = font.get_height() + 3
    bw, bh = 148, len(items) * lh + 10
    x, y0 = 8, layout.world_h - bh - 8

    bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
    bg.fill((4, 5, 16, 165))
    pygame.draw.rect(bg, (*PANEL_LINE, 200), (0, 0, bw, bh), 1, border_radius=5)
    screen.blit(bg, (x, y0))

    y = y0 + 5
    for color, sym, label in items:
        screen.blit(font.render(f"{sym} {label}", True, color), (x + 6, y))
        y += lh
