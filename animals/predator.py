# animals/predator.py — хищник
# Самый быстрый и опасный вид. Охотится на травоядных, падальщиков и всеядных.
# Медленно размножается; высокий порог воспроизводства из-за большого MAX_E.
import random
import pygame

from constants import MUTABLE_TRAITS, WHITE, RED, CELL
from params import SimParams
from animals.base import Animal


class Predator(Animal):
    """Хищник. Охотится на других животных; может есть растения при смещении рациона."""

    _base_species = "Хищник"

    def __init__(self, x, y, speed=None, vision=None, size=None,
                 energy=160, generation=1, species_name=None,
                 mutation_count=0, base_speed=None, base_vision=None,
                 base_size=None, color=None, diet=None, endurance=None,
                 herd_instinct=None):
        speed  = speed  or random.uniform(1.6, 3.2)
        vision = vision or random.uniform(8, 16)
        size   = size   or random.uniform(1.3, 2.8)
        color  = color  or [random.randint(180, 255), random.randint(20, 70), random.randint(20, 70)]
        name   = species_name or self._base_species
        super().__init__(x, y, speed, vision, size, energy, generation, color,
                         name, mutation_count, base_speed, base_vision, base_size,
                         diet=diet, endurance=endurance, herd_instinct=herd_instinct)
        self.MAX_E   = 250.0
        self.max_age = random.randint(900, 1600)

    def _default_diet(self) -> float:
        return 0.90   # по умолчанию — чистый хищник

    # ── Поведение ─────────────────────────────────────────────────────────────
    def update(self, herbivores, waters, cols, rows, p: SimParams, season_idx, plants=None):
        """Приоритет: питьё → охота (учёт камуфляжа) → пастьба (если всеядный) → блуждание."""
        self.age    += 1
        self.rep_cd -= 1
        self._metabolism(season_idx)
        self.energy    -= self.ecost + p.pred_hunger
        self.hydration -= self.thirst_drain * p.thirst_mult

        if self.energy    <= 0: self.alive = False; return "starved"
        if self.hydration <= 0: self.alive = False; return "thirst"
        if self.age > self.max_age: self.alive = False; return "old"

        # Питьё воды
        if self.hydration < 30:
            ws, wd = self.nearest_water(waters)
            if ws:
                self.state = "пьёт"
                if wd < ws.radius + 1.2:
                    self.hydration = min(self.MAX_H, self.hydration + 7)
                else:
                    self.step_toward(ws.x, ws.y, cols, rows)
                return None

        # Охота (видимость жертвы зависит от камуфляжа)
        if self.eats_animals:
            if self.energy < self.MAX_E * 0.85 or self.fat < self.MAX_FAT * 0.95:
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

        # Пастьба (если рацион сместился к растениям)
        if self.eats_plants and plants and self.energy < self.MAX_E * 0.70:
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

    # ── Размножение ───────────────────────────────────────────────────────────
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
        new_herd      = self.herd_instinct
        new_color     = list(self.color)

        for trait, (lo, hi) in MUTABLE_TRAITS.items():
            if random.random() < p.mutation_chance:
                delta = random.gauss(0, p.mutation_std)
                new   = max(lo, min(hi, getattr(self, trait) + delta))
                if trait == "speed":         new_speed  = new
                if trait == "vision":        new_vision = new
                if trait == "size":          new_size   = new
                if trait == "herd_instinct": new_herd   = new
                mutations.append((trait, delta))
                if delta > 0: new_color[0] = min(255, new_color[0] + 10)
                else:         new_color[0] = max(100, new_color[0] - 8); new_color[1] = min(80, new_color[1] + 6)

        if random.random() < p.mutation_chance * 0.5:
            diet_delta = random.gauss(0, 0.08)
            new_diet   = max(0.0, min(1.0, self.diet + diet_delta))
            mutations.append(("diet", diet_delta))
            if diet_delta < 0: new_color[1] = min(120, new_color[1] + 20)
            else:              new_color[0] = min(255, new_color[0] + 10)

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
            generation=self.generation + 1, species_name=new_name,
            mutation_count=new_mc, base_speed=self.base_speed,
            base_vision=self.base_vision, base_size=self.base_size,
            color=new_color, diet=new_diet, endurance=new_endurance, herd_instinct=new_herd)

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

    # ── Отрисовка ─────────────────────────────────────────────────────────────
    def draw(self, surf):
        cx, cy = int(self.x * CELL), int(self.y * CELL)
        r = max(4, int(self.size * 5))
        pts = [(cx, cy - r), (cx + r, cy + r // 2), (cx, cy + r // 2 - 1), (cx - r, cy + r // 2)]
        pygame.draw.polygon(surf, tuple(self.color), pts)
        pygame.draw.polygon(surf, WHITE, pts, 1)
        self._draw_bar(surf, cx, cy, r, self.energy, self.MAX_E, RED)
