# animals/herbivore.py — травоядное животное
# Базовый вид симуляции. Ест растения, убегает от хищников, собирается в стада.
# При накоплении мутаций может породить Хищника, Падальщика или Всеядного.
import random
import pygame

from constants import MUTABLE_TRAITS, WHITE, GREEN, CELL, new_species_name
from params import SimParams
from animals.base import Animal


class Herbivore(Animal):
    """Травоядное. Основной вид, с которого начинается экосистема."""

    _base_species = "Травоядное"

    def __init__(self, x, y, speed=None, vision=None, size=None,
                 energy=100, generation=1, species_name=None,
                 mutation_count=0, base_speed=None, base_vision=None,
                 base_size=None, color=None, diet=None, endurance=None,
                 herd_instinct=None):
        speed  = speed  or random.uniform(0.9, 2.2)
        vision = vision or random.uniform(5, 13)
        size   = size   or random.uniform(0.7, 1.6)
        color  = color  or [30, random.randint(160, 230), random.randint(80, 140)]
        name   = species_name or self._base_species
        super().__init__(x, y, speed, vision, size, energy, generation, color,
                         name, mutation_count, base_speed, base_vision, base_size,
                         diet=diet, endurance=endurance, herd_instinct=herd_instinct)
        self.MAX_E   = 160.0
        self.max_age = random.randint(600, 1100)

    def _default_diet(self) -> float:
        return 0.10   # по умолчанию — чистый травоядный

    # ── Поведение ─────────────────────────────────────────────────────────────
    def update(self, plants, waters, predators, cols, rows, p: SimParams,
               season_idx, extra_threats=None, allies=None):
        """Приоритет действий: бегство → питьё → стадо → охота (если всеядный) → еда → блуждание."""
        self.age    += 1
        self.rep_cd -= 1
        self._metabolism(season_idx)
        self.energy    -= self.ecost + p.herb_hunger
        self.hydration -= self.thirst_drain * p.thirst_mult

        if self.energy    <= 0: self.alive = False; return "starved"
        if self.hydration <= 0: self.alive = False; return "thirst"
        if self.age > self.max_age: self.alive = False; return "old"

        # Бегство от хищников
        _all_threats = predators + (extra_threats or [])
        real_threats = []
        for pr in _all_threats:
            if pr.alive and pr.eats_animals and pr.size >= self.size * 0.65:
                vis = self.get_visibility(season_idx)
                if self.dist(pr) < pr.vision * vis * 1.5:
                    real_threats.append(pr)

        threat, td = self.nearest(real_threats, self.vision * 2.5)
        if threat and td < self.vision * 2:
            self.state = "бежит"
            self.away(threat.x, threat.y)
            self.step(cols, rows)
            return None

        # Питьё воды
        if self.hydration < 45:
            ws, wd = self.nearest_water(waters)
            if ws:
                self.state = "пьёт"
                if wd < ws.radius + 1.2:
                    self.hydration = min(self.MAX_H, self.hydration + 6)
                else:
                    self.step_toward(ws.x, ws.y, cols, rows)
                return None

        # Охота на мелких хищников (только если всеядный/хищный рацион)
        if self.eats_animals and self.energy < self.MAX_E * 0.5:
            prey_list = [pr for pr in predators if pr.alive and self.size >= pr.size * 0.65]
            prey, pd = self.nearest(prey_list, self.vision)
            if prey:
                self.state = "охотится"
                if pd < 1.4:
                    prey.alive = False
                    self.energy = min(self.MAX_E, self.energy + 55)
                    self.kills += 1
                else:
                    self.step_toward(prey.x, prey.y, cols, rows)
                return None

        # Поедание растений
        if self.eats_plants:
            if self.energy < self.MAX_E * 0.9 or self.fat < self.MAX_FAT * 0.95:
                food = [pl for pl in plants
                        if pl.alive and pl.energy > 5 and self.dist(pl) < self.vision]
                if food:
                    food.sort(key=lambda pl: self.dist(pl))
                    tgt = food[0]
                    self.state = "ест"
                    if self.dist(tgt) < 1.4:
                        bite = min(tgt.energy, 18)
                        self.energy = min(self.MAX_E, self.energy + bite)
                        tgt.energy -= bite
                        if tgt.energy <= 0: tgt.alive = False
                    else:
                        self.step_toward(tgt.x, tgt.y, cols, rows)
                    return None

        # Блуждание + boids стадный дрейф
        self.state = "бродит"
        if allies and self.herd_instinct > 0.05:
            if self._steer_herd(allies, cols, rows):
                self.state = "в стаде"
        self.wander()
        self.step(cols, rows)
        return None

    # ── Размножение с возможным видообразованием ───────────────────────────────
    def spawn(self, p: SimParams):
        """Рожает детёныша с мутациями. При накоплении мутаций может возникнуть новый вид."""
        from animals.predator import Predator
        from animals.scavenger import Scavenger
        from animals.omnivore import Omnivore

        if not self.can_reproduce():
            return None, None, None
        self.rep_cd = 350
        self.energy *= 0.58
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
                c_idx = random.randint(0, 2)
                new_color[c_idx] = max(0, min(255, new_color[c_idx] + random.randint(-20, 20)))

        if random.random() < p.mutation_chance * 0.5:
            diet_delta = random.gauss(0, 0.08)
            new_diet   = max(0.0, min(1.0, self.diet + diet_delta))
            mutations.append(("diet", diet_delta))

        if random.random() < p.mutation_chance * 0.4:
            end_delta     = random.gauss(0, 0.07)
            new_endurance = max(0.0, min(1.0, self.endurance + end_delta))
            mutations.append(("выносл", end_delta))

        new_mc = self.mutation_count + len(mutations)
        new_name, speciated = self.species_name, False
        thresh = int(p.speciation_thresh)

        if new_mc >= thresh and self.mutation_count < thresh:
            # Редкая мутация → Хищник (если рацион сместился к плотоядности)
            if new_diet > 0.65 and random.random() < 0.06:
                pr_c = [random.randint(160, 240), random.randint(15, 55), random.randint(15, 55)]
                child_pred = Predator(
                    self.x + random.uniform(-2, 2), self.y + random.uniform(-2, 2),
                    speed=max(1.0, new_speed * 1.25), vision=min(20.0, new_vision),
                    size=new_size, energy=90, generation=self.generation + 1,
                    species_name=new_species_name("pred"), mutation_count=0,
                    base_speed=self.base_speed, base_vision=self.base_vision,
                    base_size=self.base_size, color=pr_c,
                    diet=max(0.70, new_diet), endurance=new_endurance, herd_instinct=new_herd)
                return child_pred, True, None

            # Мутация → Падальщик (рацион сместился)
            if new_diet > 0.35 and random.random() < 0.22:
                sc = [random.randint(120, 165), random.randint(65, 110), random.randint(15, 55)]
                scav = Scavenger(
                    self.x + random.uniform(-2, 2), self.y + random.uniform(-2, 2),
                    speed=max(0.3, new_speed * 0.82), vision=min(20.0, new_vision * 1.2),
                    size=new_size, energy=55, generation=self.generation + 1,
                    species_name=new_species_name("scav"), mutation_count=0,
                    base_speed=self.base_speed, base_vision=self.base_vision,
                    base_size=self.base_size, color=sc,
                    diet=0.18, endurance=new_endurance, herd_instinct=new_herd)
                return scav, True, None

            # Мутация → Всеядный
            if new_diet > 0.20 and random.random() < 0.22:
                om_c = [random.randint(170, 215), random.randint(140, 190), random.randint(20, 65)]
                omni = Omnivore(
                    self.x + random.uniform(-2, 2), self.y + random.uniform(-2, 2),
                    speed=max(0.3, new_speed * 0.60), vision=min(18.0, new_vision),
                    size=new_size, energy=70, generation=self.generation + 1,
                    species_name=new_species_name("omni"), mutation_count=0,
                    base_speed=self.base_speed, base_vision=self.base_vision,
                    base_size=self.base_size, color=om_c,
                    diet=max(0.30, min(0.70, new_diet)), endurance=new_endurance, herd_instinct=new_herd)
                return omni, True, None

            # Новый подвид травоядного
            new_name, new_color = self._speciate_name_color("herb")
            new_mc, speciated = 0, True

        child = Herbivore(
            self.x + random.uniform(-2, 2), self.y + random.uniform(-2, 2),
            speed=new_speed, vision=new_vision, size=new_size, energy=65,
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
        pygame.draw.circle(surf, WHITE, (cx, cy), r, 1)
        self._draw_bar(surf, cx, cy, r, self.energy, self.MAX_E, GREEN)
