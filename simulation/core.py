# simulation/core.py — главный класс симуляции
# Управляет всеми объектами мира: растения, вода, трупы, животные.
# Каждый тик обновляет их, обрабатывает рождения/смерти и ведёт историю.
import random

from constants import (
    SEASONS, SEASON_TICKS,
    LIGHT_GRAY, CYAN, RED, GREEN, PINK, BROWN, GOLD,
    ORANGE, YELLOW, LIGHT_BLUE, GRAY,
)
from params import SimParams, Layout
from world import Plant, WaterSource, Corpse
from animals import Herbivore, Predator, Scavenger, Omnivore


_KIND_LABEL = {
    'herb': 'Травоядное',
    'pred': 'Хищник',
    'scav': 'Падальщик',
    'omni': 'Всеядное',
}


class SpeciesRecord:
    """Пожизненная статистика одного вида."""

    __slots__ = [
        'name', 'kind', 'color', 'first_tick', 'last_seen',
        'peak_pop', 'total_births', 'total_kills', 'best_generation',
        'avg_speed', 'avg_vision', 'avg_size', 'avg_diet', 'avg_endurance',
    ]

    def __init__(self, name: str, kind: str, color: list, tick: int):
        self.name           = name
        self.kind           = kind
        self.color          = list(color)
        self.first_tick     = tick
        self.last_seen      = tick
        self.peak_pop       = 0
        self.total_births   = 0
        self.total_kills    = 0
        self.best_generation = 1
        self.avg_speed      = 0.0
        self.avg_vision     = 0.0
        self.avg_size       = 0.0
        self.avg_diet       = 0.0
        self.avg_endurance  = 0.0

    @property
    def kind_label(self) -> str:
        return _KIND_LABEL.get(self.kind, '?')

    @property
    def lifespan(self) -> int:
        return self.last_seen - self.first_tick

    @property
    def score(self) -> int:
        """Очки успеха: чем дольше прожил и больше размножился — тем выше."""
        return self.peak_pop * 8 + self.lifespan // 50 + self.best_generation * 3 + self.total_kills * 2


class Simulation:
    """Главный класс симуляции. Хранит все объекты мира и управляет временным циклом."""

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
        self.species_registry: dict[str, SpeciesRecord] = {}
        self.game_over         = False
        self.ui_tab            = "INFO"
        self.selected_animal   = None
        self._init()

    @property
    def cols(self) -> int: return self.layout.cols

    @property
    def rows(self) -> int: return self.layout.rows

    @property
    def season_idx(self) -> int:
        return (self.tick // SEASON_TICKS) % 4

    @property
    def season_info(self):
        return SEASONS[self.season_idx]

    @property
    def season_progress(self) -> float:
        return (self.tick % SEASON_TICKS) / SEASON_TICKS

    # ── Инициализация ─────────────────────────────────────────────────────────
    def _init(self):
        for _ in range(5):
            ws = WaterSource(
                random.randint(6, self.cols - 6),
                random.randint(6, self.rows - 6),
                radius=random.randint(3, 6))
            ws.rebuild(self.layout.world_w, self.layout.world_h)
            self.waters.append(ws)
        for _ in range(180):
            self.plants.append(Plant(
                random.randint(0, self.cols - 1),
                random.randint(0, self.rows - 1)))
        for _ in range(30):
            h = Herbivore(random.randint(3, self.cols - 3), random.randint(3, self.rows - 3))
            self.herbs.append(h)
            self.species_list["herb"].add(h.species_name)
        for _ in range(6):
            pr = Predator(random.randint(3, self.cols - 3), random.randint(3, self.rows - 3))
            self.preds.append(pr)
            self.species_list["pred"].add(pr.species_name)
        self._log("Симуляция запущена", CYAN)

    def on_resize(self):
        """Пересчитать геометрию воды после изменения размера окна."""
        for ws in self.waters:
            ws.rebuild(self.layout.world_w, self.layout.world_h)

    def _log(self, text: str, color=LIGHT_GRAY):
        self.events.append([text, color, 320])
        if len(self.events) > 20:
            self.events.pop(0)

    # ── Главный цикл обновления ────────────────────────────────────────────────
    def update(self, p: SimParams):
        if self.paused:
            return
        self.tick += 1
        cols, rows = self.cols, self.rows

        sname, spawn_m, max_m, grow_m, _, _ = self.season_info
        effective_max  = int(self.BASE_MAX_PLANTS * max_m)
        effective_rate = self.BASE_PLANT_RATE * spawn_m
        effective_grow = self.BASE_PLANT_GROW * grow_m

        if self.tick % SEASON_TICKS == 1 and self.tick > 1:
            self._log(f"Наступил(а) {sname}!", SEASONS[self.season_idx][5])

        # Растения
        alive_pl = [pl for pl in self.plants if pl.alive]
        deficit  = effective_max - len(alive_pl)
        if deficit > 0 and random.random() < effective_rate:
            for _ in range(random.randint(1, min(4, max(1, deficit)))):
                if alive_pl and random.random() < 0.7:
                    ref = random.choice(alive_pl)
                    x = max(0, min(cols - 1, ref.x + random.randint(-6, 6)))
                    y = max(0, min(rows - 1, ref.y + random.randint(-6, 6)))
                else:
                    x, y = random.randint(0, cols - 1), random.randint(0, rows - 1)
                self.plants.append(Plant(x, y, random.uniform(5, 25)))
        for pl in self.plants:
            pl.update(effective_grow)
        self.plants = [pl for pl in self.plants if pl.alive]

        # Трупы
        for c in self.corpses:
            c.update()
        self.corpses = [c for c in self.corpses if c.alive]

        # Травоядные
        new_h = []
        for h in self.herbs:
            res = h.update(self.plants, self.waters, self.preds, cols, rows, p,
                           self.season_idx, self.omnis, self.herbs)
            if not h.alive:
                self.total_deaths += 1
                ce = max(6.0, h.size * 20 + h.energy * 0.3)
                self.corpses.append(Corpse(h.x, h.y, ce))
                msgs = {"starved": ("умерло от голода", YELLOW),
                        "thirst":  ("умерло от жажды",  LIGHT_BLUE),
                        "old":     ("умерло от старости", GRAY)}
                if res in msgs:
                    self._log(f"{h.species_name} {msgs[res][0]}", msgs[res][1])
            else:
                child, spec, mut_desc = h.spawn(p)
                if child:
                    if isinstance(child, Omnivore):
                        self.omnis.append(child); self.total_births_o += 1
                        self.total_speciations += 1
                        self.species_list["omni"].add(child.species_name)
                        self._log(f"МУТАЦИЯ → ВСЕЯДНЫЙ: «{child.species_name}»!", GOLD)
                    elif isinstance(child, Predator):
                        self.preds.append(child); self.total_births_p += 1
                        self.total_speciations += 1
                        self.species_list["pred"].add(child.species_name)
                        self._log(f"МУТАЦИЯ → ХИЩНИК: «{child.species_name}»!", RED)
                    elif isinstance(child, Scavenger):
                        self.scavs.append(child); self.total_births_s += 1
                        self.total_speciations += 1
                        self.species_list["scav"].add(child.species_name)
                        self._log(f"МУТАЦИЯ → ПАДАЛЬЩИК: «{child.species_name}»!", BROWN)
                    else:
                        new_h.append(child); self.total_births_h += 1
                        self.species_list["herb"].add(child.species_name)
                        if spec:
                            self.total_speciations += 1
                            self._log(f"НОВЫЙ ВИД: «{child.species_name}»!", CYAN)
                        elif mut_desc:
                            self._log(mut_desc, (120, 255, 120))
                        else:
                            self._log(f"Рождение {child.species_name} пок.{child.generation}", GREEN)
        self.herbs = [h for h in self.herbs if h.alive] + new_h

        # Хищники охотятся на травоядных + падальщиков + всеядных
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
                if res in msgs:
                    self._log(f"{pred.species_name} {msgs[res][0]}", msgs[res][1])
            else:
                if res == "kill":
                    self.total_kills += 1
                    self._log(f"{pred.species_name} схватил добычу! ({self.total_kills})", RED)
                child, spec, mut_desc = pred.spawn(p)
                if child:
                    new_p.append(child); self.total_births_p += 1
                    self.species_list["pred"].add(child.species_name)
                    if spec:
                        self.total_speciations += 1
                        self._log(f"НОВЫЙ ВИД ХИЩНИКА: «{child.species_name}»!", ORANGE)
                    elif mut_desc:
                        self._log(mut_desc, PINK)
                    else:
                        self._log(f"Рождение {child.species_name} пок.{child.generation}", PINK)
        self.preds = [pr for pr in self.preds if pr.alive] + new_p

        # Падальщики
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
                if res in msgs:
                    self._log(f"{scav.species_name} {msgs[res][0]}", msgs[res][1])
            else:
                child, spec, mut_desc = scav.spawn(p)
                if child:
                    new_s.append(child); self.total_births_s += 1
                    self.species_list["scav"].add(child.species_name)
                    if spec:
                        self.total_speciations += 1
                        self._log(f"НОВЫЙ ВИД ПАДАЛЬЩИКА: «{child.species_name}»!", BROWN)
                    elif mut_desc:
                        self._log(mut_desc, (200, 140, 60))
                    else:
                        self._log(f"Рождение {child.species_name} пок.{child.generation}", (200, 140, 60))
        self.scavs = [s for s in self.scavs if s.alive] + new_s

        # Всеядные охотятся на травоядных и падальщиков
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
                if res in msgs:
                    self._log(f"{omni.species_name} {msgs[res][0]}", msgs[res][1])
            else:
                if res == "kill":
                    self.total_kills += 1
                child, spec, mut_desc = omni.spawn(p)
                if child:
                    new_o.append(child); self.total_births_o += 1
                    self.species_list["omni"].add(child.species_name)
                    if spec:
                        self.total_speciations += 1
                        self._log(f"НОВЫЙ ВИД ВСЕЯДНОГО: «{child.species_name}»!", GOLD)
                    elif mut_desc:
                        self._log(mut_desc, (200, 180, 60))
                    else:
                        self._log(f"Рождение {child.species_name} пок.{child.generation}", (200, 180, 60))
        self.omnis = [o for o in self.omnis if o.alive] + new_o

        # История популяций (каждые 90 тиков)
        if self.tick % 90 == 0:
            self.history["h"].append(len(self.herbs))
            self.history["p"].append(len(self.preds))
            self.history["s"].append(len(self.scavs))
            self.history["o"].append(len(self.omnis))
            self.history["pl"].append(len(self.plants))
            for k in self.history:
                if len(self.history[k]) > 120:
                    self.history[k].pop(0)
            self._update_registry()

        for e in self.events:
            e[2] -= 1
        self.events = [e for e in self.events if e[2] > 0]

        # Уведомления о вымирании
        if len(self.herbs) == 0 and self.tick % 300 == 0:
            self._log("Травоядные вымерли.", RED)
        if len(self.preds) == 0 and self.tick % 300 == 0:
            self._log("Хищники вымерли.", ORANGE)
        if len(self.scavs) == 0 and self.tick % 600 == 0 and self.total_births_s > 0:
            self._log("Падальщики вымерли.", BROWN)
        if len(self.omnis) == 0 and self.tick % 600 == 0 and self.total_births_o > 0:
            self._log("Всеядные вымерли.", GOLD)

        # Полное вымирание → зал славы
        if (not self.game_over
                and len(self.herbs) == 0 and len(self.preds) == 0
                and len(self.scavs) == 0 and len(self.omnis) == 0
                and self.tick > 300):
            self._update_registry()
            self.game_over = True

    # ── Реестр видов ──────────────────────────────────────────────────────────
    def _update_registry(self):
        """Обновить статистику всех живых видов в реестре."""
        groups = [
            (self.herbs, 'herb'),
            (self.preds, 'pred'),
            (self.scavs, 'scav'),
            (self.omnis, 'omni'),
        ]
        for population, kind in groups:
            by_name: dict[str, list] = {}
            for a in population:
                by_name.setdefault(a.species_name, []).append(a)

            for name, animals in by_name.items():
                if name not in self.species_registry:
                    self.species_registry[name] = SpeciesRecord(
                        name, kind, animals[0].color, self.tick)
                rec = self.species_registry[name]
                rec.last_seen        = self.tick
                rec.peak_pop         = max(rec.peak_pop, len(animals))
                rec.total_kills      = max(rec.total_kills, sum(a.kills for a in animals))
                rec.best_generation  = max(rec.best_generation,
                                           max(a.generation for a in animals))
                n = len(animals)
                rec.avg_speed     = sum(a.speed     for a in animals) / n
                rec.avg_vision    = sum(a.vision    for a in animals) / n
                rec.avg_size      = sum(a.size      for a in animals) / n
                rec.avg_diet      = sum(a.diet      for a in animals) / n
                rec.avg_endurance = sum(a.endurance for a in animals) / n
                rec.total_births  += len([a for a in animals if a.children > 0])

    def top_species(self, n: int = 10) -> list:
        """Топ N видов по очкам успеха, отсортированных по убыванию."""
        return sorted(self.species_registry.values(),
                      key=lambda r: r.score, reverse=True)[:n]
