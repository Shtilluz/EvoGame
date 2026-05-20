# rendering/renderer.py — отрисовка мира и информационной панели
import pygame

from constants import (
    BLACK, WHITE, GRAY, LIGHT_GRAY, GREEN, RED, BLUE, BROWN, GOLD, ORANGE,
    YELLOW, CYAN, PINK, LIGHT_BLUE, PANEL_BG, SEASONS, SEASON_TICKS,
    DIET_HERB_THRESH, DIET_CARN_THRESH, CELL,
)
from params import Layout
from simulation.core import Simulation
from ui.slider import Slider


def draw_all(screen, sim: Simulation, layout: Layout, fonts,
             speed_sl: Slider, param_sliders: list):
    """Отрисовать весь кадр: мировое поле + информационная панель."""
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
    pygame.draw.rect(screen, GRAY, (0, 0, L.world_w, L.world_h), 2)

    # Сезонный баннер и прогресс-бар
    banner = fs.render(f"  {sname}  ", True, BLACK)
    bw, bh = banner.get_width() + 4, banner.get_height() + 2
    pygame.draw.rect(world_surf, s_color, (4, 4, bw, bh), border_radius=4)
    world_surf.blit(banner, (6, 5))
    prog_w = int(bw * sim.season_progress)
    pygame.draw.rect(world_surf, (0, 0, 0, 120), (4, bh + 6, bw, 4), border_radius=2)
    if prog_w > 0:
        pygame.draw.rect(world_surf, s_color, (4, bh + 6, prog_w, 4), border_radius=2)

    # ── Панель ───────────────────────────────────────────────────────────────
    panel = screen.subsurface((L.panel_x, 0, L.panel_w, L.sh))
    panel.fill(PANEL_BG)
    px, py = 8, 8
    pw = L.panel_w - px * 2

    def txt(s, color, f=None, indent=0):
        nonlocal py
        surf = (f or fs).render(s, True, color)
        panel.blit(surf, (px + indent, py))
        py += surf.get_height() + 2

    def hline(gap=3):
        nonlocal py
        py += gap
        pygame.draw.line(panel, GRAY, (px, py), (L.panel_w - px, py))
        py += gap + 2

    txt("СИМУЛЯТОР ЭВОЛЮЦИИ", WHITE, fb)
    txt(f"Тик: {sim.tick}  {'⏸ ПАУЗА' if sim.paused else '▶ работает'}", LIGHT_GRAY)
    hline(4)

    # Вкладки
    tabs = [("ИНФО", "INFO"), ("ВИДЫ", "SPECIES"), ("НАСТР", "SETTINGS"),
            ("ГРАФ", "GRAPH"), ("ОБЪЕКТ", "INSPECTOR")]
    tab_h = 28
    tw = L.panel_w // len(tabs)
    for i, (name, tid) in enumerate(tabs):
        tx = i * tw
        rect = pygame.Rect(tx, py, tw, tab_h)
        active = (sim.ui_tab == tid)
        pygame.draw.rect(panel, (40, 45, 70) if active else (20, 22, 35), rect)
        pygame.draw.rect(panel, GRAY if active else (50, 50, 60), rect, 1)
        t_surf = fs.render(name, True, WHITE if active else LIGHT_GRAY)
        panel.blit(t_surf, (tx + (tw - t_surf.get_width()) // 2,
                             py + (tab_h - t_surf.get_height()) // 2))
    py += tab_h + 10

    # ── Содержимое активной вкладки ───────────────────────────────────────────
    if sim.ui_tab == "INFO":
        year    = sim.tick // (SEASON_TICKS * 4) + 1
        s_idx   = sim.season_idx
        season_row = f"Год {year}  |  "
        for i, (sn, *_rest) in enumerate(SEASONS):
            season_row += f"[{sn}]" if i == s_idx else f" {sn} "
        txt(season_row, s_color)
        hline()

        py += 10
        tps = int(10 * speed_sl.value)
        speed_sl.draw_full(panel, L.panel_x, px, py, pw - 4, fs,
                           extra=f"  ({tps} тик/с)")
        py += 18
        hline()

        txt(f"Травоядные: {len(sim.herbs):>4}", GREEN)
        txt(f"Хищники:    {len(sim.preds):>4}", RED)
        txt(f"Падальщики: {len(sim.scavs):>4}", BROWN)
        txt(f"Всеядные:   {len(sim.omnis):>4}", GOLD)
        txt(f"Трупы:      {len(sim.corpses):>4}", GRAY)
        txt(f"Растения:   {len(sim.plants):>4}", (80, 200, 80))
        hline(2)

        def avg(seq, attr):
            return sum(getattr(a, attr) for a in seq) / len(seq) if seq else 0.0

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

        txt("ПОСЛЕДНИЕ СОБЫТИЯ:", WHITE)
        for ev in reversed(sim.events[-12:]):
            if py > L.sh - 110: break
            alpha = min(255, ev[2] * 2)
            c = tuple(min(255, int(ch * alpha / 255)) for ch in ev[1])
            panel.blit(fs.render(ev[0][:46], True, c), (px, py))
            py += 15

        py = L.sh - 100
        hline(2)
        for key, desc in [
            ("ПРОБЕЛ", "пауза"),   ("F11",  "полный экран"),
            ("Н",      "+трав."),  ("Х",    "+хищн."),
            ("С",      "+пад."),   ("R",    "рестарт"),
            ("Q",      "выход"),
        ]:
            sk = fs.render(key, True, YELLOW)
            sd = fs.render(f"  {desc}", True, GRAY)
            panel.blit(sk, (px, py)); panel.blit(sd, (px + sk.get_width(), py))
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

        thresh = int(param_sliders[5].value)   # порог видообразования из слайдера

        def sp_stats(grp):
            if not grp: return None
            n  = len(grp)
            sp = sum(a.speed      for a in grp) / n
            sz = sum(a.size       for a in grp) / n
            vs = sum(a.vision     for a in grp) / n
            ec = sum(a.ecost      for a in grp) / n
            en = sum(a.endurance  for a in grp) / n
            dt = sum(a.diet       for a in grp) / n
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
            asiz = sum(a.size for a in grp) / len(grp)
            adt  = sum(a.diet for a in grp) / len(grp)
            targets = []
            if adt <= DIET_CARN_THRESH: targets.append("Растения")
            if adt >= DIET_HERB_THRESH:
                for (name, mc), sg in all_sp:
                    if not sg or name == grp[0].species_name: continue
                    if asiz >= (sum(a.size for a in sg) / len(sg)) * 0.65:
                        if name not in targets: targets.append(name)
            return ("→ " + ", ".join(targets[:4])) if targets else ""

        def draw_species_block(active, label_color):
            nonlocal py
            for (name, mc), grp in active:
                if py > L.sh - 60: break
                t = sp_stats(grp)
                prey_str = prey_labels(grp)
                if mc > 0:
                    txt(f"  ПОДВИД {name}: {len(grp)}", label_color)
                    prog = min(1.0, mc / thresh)
                    bar_w = 120
                    pygame.draw.rect(panel, (30, 30, 45), (px + 10, py + 2, bar_w, 4))
                    pygame.draw.rect(panel, CYAN, (px + 10, py + 2, int(bar_w * prog), 4))
                    txt(f"    Прогресс вида: {mc}/{thresh}", (100, 200, 255), f=fs, indent=120)
                else:
                    txt(f"  ВИД {name}: {len(grp)}", WHITE)
                if t:
                    sp2, sz2, vs2, ec2, en2, dl2, gn2 = t
                    en_str = f" вын:{en2:.2f}" if en2 > 0.05 else ""
                    first = grp[0]
                    def dev(val, base):
                        d = val - base
                        return f"{'+' if d >= 0 else ''}{d:.2f}"
                    txt(f"    ск:{sp2:.1f}({dev(sp2, first.base_speed)}) "
                        f"рз:{sz2:.1f}({dev(sz2, first.base_size)}) "
                        f"зр:{vs2:.0f}({dev(vs2, first.base_vision)})", GRAY)
                    txt(f"    тип:{dl2} пок:{gn2:.0f} е:{ec2:.2f}{en_str}", GRAY)
                if prey_str:
                    txt(f"    {prey_str}", (120, 120, 120))
                py += 6

        if h_active:  txt(f"ТРАВОЯДНЫЕ ({len(h_active)} групп):", GREEN);  draw_species_block(h_active,  LIGHT_GRAY)
        if p_active:  txt(f"ХИЩНИКИ ({len(p_active)} групп):", RED);        draw_species_block(p_active,  LIGHT_GRAY)
        if sc_active: txt(f"ПАДАЛЬЩИКИ ({len(sc_active)} групп):", BROWN);  draw_species_block(sc_active, LIGHT_GRAY)
        if om_active: txt(f"ВСЕЯДНЫЕ ({len(om_active)} групп):", GOLD);     draw_species_block(om_active, LIGHT_GRAY)

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
            step = graph_w / (len(data) - 1)
            pts  = []
            for i, v in enumerate(data):
                gx = px + int(i * step)
                gy = max(graph_y, min(graph_y + graph_h,
                                      graph_y + graph_h - int(v / max_v * graph_h)))
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
        txt(" ● Зеленый: Травоядные",   GREEN)
        txt(" ● Красный: Хищники",       RED)
        txt(" ● Коричневый: Падальщики", BROWN)
        txt(" ● Золотой: Всеядные",      GOLD)
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
            kind_colors = {"Herbivore": GREEN, "Predator": RED, "Scavenger": BROWN, "Omnivore": GOLD}
            k_name = type(obj).__name__
            alive_color = WHITE if obj.alive else GRAY

            txt(f"ВИД: {obj.species_name}",
                kind_colors.get(k_name, WHITE) if obj.alive else GRAY, fb)
            if not obj.alive:
                txt("СТАТУС: ПОГИБ", RED, fb)

            txt(f"Тип: {k_name} ({obj.diet_label})", LIGHT_GRAY)
            txt(f"Поколение: {obj.generation}", alive_color)
            hline()

            if obj.alive:
                st_color = CYAN if obj.state == "бежит" else (ORANGE if obj.state == "охотится" else WHITE)
                txt(f"Состояние: {obj.state}", st_color)

            def draw_stat_bar(label, val, maxi, color):
                nonlocal py
                txt(f"{label}: {val:.1f}/{maxi:.0f}", WHITE if obj.alive else GRAY)
                pygame.draw.rect(panel, (30, 30, 40), (px, py, pw, 6))
                if obj.alive:
                    pygame.draw.rect(panel, color,
                                     (px, py, int(pw * max(0, min(1, val / maxi))), 6))
                py += 10

            draw_stat_bar("Энергия",    obj.energy,    obj.MAX_E,   YELLOW)
            draw_stat_bar("Жажда",      obj.hydration, obj.MAX_H,   BLUE)
            draw_stat_bar("Жир (запас)", obj.fat,      obj.MAX_FAT, (200, 200, 100))

            fat_ratio = obj.fat / max(1, obj.MAX_FAT)
            if fat_ratio > 0.1:
                txt(f"  Эффект: -{fat_ratio*25:.0f}% скор, +{fat_ratio*40:.0f}% расход",
                    (255, 100, 100))

            py += 5
            txt(f"Возраст: {obj.age}/{obj.max_age} тик", LIGHT_GRAY)
            hline()

            txt("ГЕНЕТИЧЕСКИЕ ТРЕЙТЫ:", WHITE)

            def trait_row(lab, val, base):
                d = val - base
                d_str = f"({'+' if d >= 0 else ''}{d:.2f})"
                txt(f"  {lab}: {val:.2f} {d_str}", LIGHT_GRAY)

            trait_row("Скорость", obj.speed,  obj.base_speed)
            trait_row("Зрение",   obj.vision, obj.base_vision)
            trait_row("Размер",   obj.size,   obj.base_size)
            txt(f"  Стадность: {obj.herd_instinct:.2f}", LIGHT_GRAY)

            vis   = obj.get_visibility(sim.season_idx)
            vis_p = int(vis * 100)
            v_col = GREEN if vis < 0.6 else (YELLOW if vis < 0.9 else RED)
            txt(f"  Заметность: {vis_p}%", v_col)

            txt(f"  Выносливость: {obj.endurance:.2f}", LIGHT_GRAY)
            txt(f"  Рацион (0-1): {obj.diet:.2f}", LIGHT_GRAY)
            hline()

            txt(f"Детей: {obj.children}  Убийств: {obj.kills}", WHITE)
            txt(f"Накоплено мутаций: {obj.mutation_count}", CYAN)

    # Подсветка выбранного животного в мире
    if sim.selected_animal and sim.selected_animal.alive:
        obj = sim.selected_animal
        sx, sy = int(obj.x * CELL), int(obj.y * CELL)
        r = max(6, int(obj.size * 6))
        pygame.draw.circle(world_surf, WHITE, (sx, sy), r + 2, 1)
        pygame.draw.circle(world_surf, CYAN,  (sx, sy), r + 4, 1)


def draw_legend(screen, layout: Layout, font):
    """Легенда символов в левом нижнем углу мирового поля."""
    items = [
        (GREEN,       "●", "Травоядное"),
        (RED,         "◆", "Хищник"),
        (BROWN,       "●", "Падальщик (×=труп)"),
        ((0, 160, 0), "●", "Растение"),
        (BLUE,        "■", "Вода"),
    ]
    x, y = 6, layout.world_h - len(items) * 14 - 8
    bg = pygame.Surface((170, len(items) * 14 + 8), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 150))
    screen.blit(bg, (x - 2, y - 2))
    for color, sym, label in items:
        screen.blit(font.render(f"{sym} {label}", True, color), (x, y))
        y += 14
