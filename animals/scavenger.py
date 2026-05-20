# animals/scavenger.py — падальщик
# Возникает только через мутацию травоядного. Специализируется на поедании трупов.
# Компромиссы: +зрение, -скорость, ×1.35 голод, не охотится на живых.
import random
import pygame

from constants import MUTABLE_TRAITS, WHITE, ORANGE, CELL, new_species_name
from params import SimParams
from animals.base import Animal


class Scavenger(Animal):
    """Падальщик. Ест трупы (основная еда) и растения (вспомогательно)."""

    _base_species = "Падальщик"

    def __init__(self, x, y, speed=None, vision=None, size=None,
                 energy=80, generation=1, species_name=None,
                 mutation_count=0, base_speed=None, base_vision=None,
                 base_size=None, color=None, diet=None, endurance=None,
                 herd_instinct=None):
        speed  = speed  or random.uniform(0.6, 1.5)
        vision = vision or random.uniform(10, 18)
        size   = size   or random.uniform(0.8, 2.0)
        color  = color  or [random.randint(120, 165), random.randint(65, 110), random.randint(15, 55)]
        name   = species_name or self._base_species
        super().__init__(x, y, speed, vision, size, energy, generation, color,
                         name, mutation_count, base_speed, base_vision, base_size,
                         diet=diet, endurance=endurance, herd_instinct=herd_instinct)
        self.MAX_E   = 150.0
        self.max_age = random.randint(500, 1000)

    def _default_diet(self) -> float:
        return 0.18

    # ── Поведение ─────────────────────────────────────────────────────────────
    def update(self, corpses, plants, waters, predators, cols, rows, p: SimParams,
               season_idx, extra_threats=None, allies=None):
        """Приоритет: бегство → питьё → стая → труп → растение → блуждание."""
        self.age    += 1
        self.rep_cd -= 1
        self._metabolism(season_idx)
        self.energy    -= self.ecost + p.herb_hunger * 1.35   # штраф голода
        self.hydration -= self.thirst_drain * p.thirst_mult

        if self.energy    <= 0: self.alive = False; return "starved"
        if self.hydration <= 0: self.alive = False; return "thirst"
        if self.age > self.max_age: self.alive = False; return "old"

        # Бегство от хищников
        _all_threats = predators + (extra_threats or [])
        threats = []
        for pr in _all_threats:
            if pr.alive and pr.eats_animals and pr.size >= self.size * 0.65:
                vis = self.get_visibility(season_idx)
                if self.dist(pr) < pr.vision * vis * 1.5:
                    threats.append(pr)

        threat, td = self.nearest(threats, self.vision * 2.5)
        if threat and td < self.vision * 2:
            self.state = "бежит"
            self.away(threat.x, threat.y)
            self.step(cols, rows)
            return None

        # Питьё
        if self.hydration < 45:
            ws, wd = self.nearest_water(waters)
            if ws:
                self.state = "пьёт"
                if wd < ws.radius + 1.2:
                    self.hydration = min(self.MAX_H, self.hydration + 6)
                else:
                    self.step_toward(ws.x, ws.y, cols, rows)
                return None

        # Стайное поведение
        if self.herd_instinct > 0.15 and allies and self.energy > self.MAX_E * 0.4:
            friends = [a for a in allies if a.alive and a != self and a.species_name == self.species_name]
            friend, fd = self.nearest(friends, self.vision * 2.5)
            if friend and fd > 5.0:
                self.state = "в стае"
                if random.random() < self.herd_instinct:
                    self.step_toward(friend.x, friend.y, cols, rows)
                    return None

        # Поедание трупа (основная еда)
        if self.energy < self.MAX_E * 0.9 or self.fat < self.MAX_FAT * 0.95:
            live_corpses = [c for c in corpses
                            if c.alive and c.energy > 1.5 and self.dist(c) < self.vision]
            if live_corpses:
                live_corpses.sort(key=lambda c: self.dist(c))
                tgt = live_corpses[0]
                self.state = "ест труп"
                if self.dist(tgt) < 1.4:
                    bite = min(tgt.energy, 24)
                    self.energy  = min(self.MAX_E, self.energy + bite)
                    tgt.energy  -= bite
                    if tgt.energy < 1.5: tgt.alive = False
                else:
                    self.step_toward(tgt.x, tgt.y, cols, rows)
                return None

        # Поедание растений (вдвое менее эффективно)
        if self.energy < self.MAX_E * 0.75:
            food = [pl for pl in plants
                    if pl.alive and pl.energy > 5 and self.dist(pl) < self.vision]
            if food:
                food.sort(key=lambda pl: self.dist(pl))
                tgt = food[0]
                self.state = "жует траву"
                if self.dist(tgt) < 1.4:
                    bite = min(tgt.energy, 9)   # вдвое меньше чем у травоядного
                    self.energy = min(self.MAX_E, self.energy + bite)
                    tgt.energy -= bite
                    if tgt.energy <= 0: tgt.alive = False
                else:
                    self.step_toward(tgt.x, tgt.y, cols, rows)
                return None

        self.state = "рыщет"
        self.wander()
        self.step(cols, rows)
        return None

    # ── Размножение ───────────────────────────────────────────────────────────
    def spawn(self, p: SimParams):
        if not self.can_reproduce():
            return None, None, None
        self.rep_cd = 420
        self.energy *= 0.55
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
                if delta > 0: new_color[0] = min(200, new_color[0] + 8)
                else:         new_color[1] = max(0,   new_color[1] - 5)

        if random.random() < p.mutation_chance * 0.3:
            diet_delta = random.gauss(0, 0.06)
            new_diet   = max(0.0, min(1.0, self.diet + diet_delta))
            mutations.append(("diet", diet_delta))

        if random.random() < p.mutation_chance * 0.4:
            end_delta     = random.gauss(0, 0.07)
            new_endurance = max(0.0, min(1.0, self.endurance + end_delta))
            mutations.append(("выносл", end_delta))
            if end_delta > 0: new_color[2] = min(160, new_color[2] + 12)
            else:              new_color[2] = max(0,   new_color[2] - 8)

        new_mc = self.mutation_count + len(mutations)
        new_name, speciated = self.species_name, False
        thresh = int(p.speciation_thresh)
        if new_mc >= thresh and self.mutation_count < thresh:
            new_name  = new_species_name("scav")
            new_color = [(self.color[i] + random.randint(0, 200)) // 2 for i in range(3)]
            new_mc, speciated = 0, True

        child = Scavenger(
            self.x + random.uniform(-2, 2), self.y + random.uniform(-2, 2),
            speed=new_speed, vision=new_vision, size=new_size, energy=55,
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
        r = max(3, int(self.size * 4))
        pygame.draw.circle(surf, tuple(self.color), (cx, cy), r)
        d = max(2, r - 1)
        pygame.draw.line(surf, (210, 160, 70), (cx - d, cy - d), (cx + d, cy + d), 1)
        pygame.draw.line(surf, (210, 160, 70), (cx + d, cy - d), (cx - d, cy + d), 1)
        pygame.draw.circle(surf, WHITE, (cx, cy), r, 1)
        self._draw_bar(surf, cx, cy, r, self.energy, self.MAX_E, ORANGE)
