# Evolution Simulator

A real-time evolutionary biology simulator built with Python and Pygame. Watch species emerge, adapt, and go extinct as natural selection plays out tick by tick.

---

## Quick Start

```bash
pip install pygame
python main.py
```

**Controls**

| Key | Action |
|-----|--------|
| `Space` | Pause / Resume |
| `F11` | Toggle fullscreen |
| `N` / `Н` | Spawn 8 herbivores |
| `X` / `Х` | Spawn 3 predators |
| `S` / `С` | Spawn 5 scavengers |
| `R` | Restart simulation |
| `+` / `-` | Speed up / slow down |
| `Q` / `Esc` | Quit |
| **Click** animal | Inspect its stats |

---

## What Happens

The simulator starts with **30 herbivores** and **6 predators** on a world with 180 plants and 5 water sources. Each tick every animal spends energy and hydration, makes a decision (flee, drink, eat, wander), and may reproduce. When an animal reproduces, its offspring can inherit mutated traits. After enough mutations accumulate a new species can branch off.

### Seasons

Four seasons cycle every 4 800 ticks (one in-game year). Season affects plant growth and animal survival pressure:

| Season | Plant growth | Plant spawn | Effect |
|--------|-------------|-------------|--------|
| Spring | normal | ×1.2 | Moderate |
| Summer | ×1.4 | ×2.0 | Boom — herds grow |
| Autumn | ×0.6 | ×0.55 | Decline begins |
| Winter | −0.05/tick | ×0.08 | Plants wither; cold damage if low fat |

Animals accumulate **fat** in summer and burn it in winter. Cold damage in winter is proportional to how empty the fat reserve is.

---

## Animal Species

### Herbivore (green circle)

The base species. Eats plants, flees predators, herds with same-species members.

| Stat | Default range |
|------|--------------|
| Speed | 0.9 – 2.2 |
| Vision | 5 – 13 |
| Max energy | 160 |
| Max age | 600 – 1 100 ticks |

**Behaviour priority:** flee → drink → herd → hunt small prey (if diet shifted) → eat plants → wander

### Predator (red diamond/triangle)

Fastest and most dangerous. Hunts herbivores, scavengers and omnivores. Vision accounts for prey camouflage.

| Stat | Default range |
|------|--------------|
| Speed | 1.6 – 3.2 |
| Vision | 8 – 16 |
| Max energy | 250 |
| Max age | 900 – 1 600 ticks |

**Behaviour priority:** drink → hunt (camouflage-aware) → graze (if diet shifted) → wander

### Scavenger (brown circle with ×)

Emerges only via mutation from herbivores. Specialises in eating corpses.

| Stat | Default range |
|------|--------------|
| Speed | 0.6 – 1.5 |
| Vision | 10 – 18 |
| Max energy | 150 |
| Max age | 500 – 1 000 ticks |

**Trade-offs:** ×1.35 hunger rate, best vision, half plant efficiency, cannot hunt live animals.

### Omnivore (gold diamond)

Emerges only via mutation. Eats both plants and live prey; slowest class overall.

| Stat | Default range |
|------|--------------|
| Speed | 0.4 – 1.0 |
| Vision | 7 – 14 |
| Max energy | 170 |
| Max age | 700 – 1 200 ticks |

**Trade-offs:** ×1.10 hunger rate, flexible food sources, easy prey for predators.

---

## Genetics & Mutation

Every time an animal reproduces, each mutable trait has a chance to shift by a Gaussian delta:

| Trait | Bounds | Mutation chance |
|-------|--------|----------------|
| Speed | 0.3 – 5.0 | `mutation_chance` |
| Vision | 2.0 – 20.0 | `mutation_chance` |
| Size | 0.3 – 4.0 | `mutation_chance` |
| Herd instinct | 0.0 – 1.0 | `mutation_chance` |
| Diet | 0.0 – 1.0 | `mutation_chance × 0.5` |
| Endurance | 0.0 – 1.0 | `mutation_chance × 0.4` |

**Diet axis:** `0.0` = pure herbivore → `0.35` threshold → omnivore zone → `0.65` threshold → `1.0` = pure carnivore

**Endurance trade-off:** higher endurance reduces hunger and thirst costs (up to 45%) but also reduces effective speed (up to 35%).

**Camouflage:** an animal's RGB color drifts with mutations. The closer the color is to the seasonal background, the harder it is for predators to spot it.

### Speciation

Each inherited mutation increments `mutation_count`. When the count crosses `speciation_thresh` (default 10), the next offspring may become a new species:

- **→ Predator** (6% chance if `diet > 0.65`): speed ×1.25, large energy reserve
- **→ Scavenger** (22% chance if `diet > 0.35`): vision ×1.2, speed ×0.82
- **→ Omnivore** (22% chance if `diet > 0.20`): speed ×0.60, flexible diet
- **→ New herbivore sub-species** (otherwise): `mutation_count` resets to 0

---

## Tunable Settings (НАСТР tab)

All parameters apply immediately every tick:

| Slider | Effect |
|--------|--------|
| Mutation chance | Probability each trait mutates at birth |
| Mutation magnitude | σ of the Gaussian shift |
| Herb hunger | Extra energy drain per tick for herbivores / scavengers |
| Pred hunger | Extra energy drain per tick for predators |
| Thirst multiplier | Scales hydration loss for all species |
| Speciation threshold | Mutations needed before speciation is possible |

---

## UI Tabs

| Tab | Content |
|-----|---------|
| **ИНФО** | Live counts, averages, birth/death stats, event log, speed slider |
| **ВИДЫ** | Living species grouped by name + mutation level; shows trait drift and prey targets |
| **НАСТР** | Six live-tuning sliders |
| **ГРАФ** | Population time-series graph |
| **ОБЪЕКТ** | Detailed inspector for the clicked animal |

---

## Project Structure

```
EvoGame/
├── main.py                  # Entry point — game loop, input, window
├── constants.py             # All colours, seasons, species name pools, trait bounds
├── params.py                # SimParams (slider values) + Layout (window geometry)
│
├── animals/                 # One file per species
│   ├── base.py              # Animal — movement, metabolism, reproduction base
│   ├── herbivore.py         # Herbivore — also handles speciation branching
│   ├── predator.py          # Predator
│   ├── scavenger.py         # Scavenger
│   └── omnivore.py          # Omnivore
│
├── world/                   # Inanimate world objects
│   ├── plant.py             # Plant — energy source, grows seasonally
│   ├── water.py             # WaterSource — static, animals drink from it
│   └── corpse.py            # Corpse — decays, scavengers eat it
│
├── simulation/
│   └── core.py              # Simulation — master update loop, history, logging
│
├── ui/
│   └── slider.py            # Slider widget — full and compact rendering modes
│
└── rendering/
    └── renderer.py          # draw_all() + draw_legend() — all pygame drawing
```

### Dependency graph

```
constants  (no project imports)
    ↑
params     (← constants)
    ↑
world/*    (← constants)
    ↑
animals/*  (← constants, params, world via simulation)
    ↑
simulation (← constants, params, world, animals)
    ↑
ui         (← constants)
    ↑
rendering  (← constants, params, simulation, ui)
    ↑
main       (← all)
```

---

## Adding a New Species

1. Create `animals/myspecies.py` — inherit from `Animal`, override `_default_diet`, `update`, `spawn`, `draw`.
2. Add a name pool to `constants.py` and handle the new kind in `new_species_name()`.
3. Add the list to `Simulation.__init__` and update `Simulation.update` (the four-species block).
4. Register the new type in `rendering/renderer.py` for counting and drawing.
5. Export from `animals/__init__.py`.

---

## Technical Notes

- **Coordinate system:** float grid cells; rendered at `CELL = 8 px/cell`. World fills ~70% of the window; the right panel is ~30%.
- **Collision:** animals can overlap; proximity checks use Euclidean distance in cell units.
- **Performance:** all lists are rebuilt each tick with list comprehensions; suitable for hundreds of animals at 60 FPS.
- **Fat system:** energy above 80% MAX_E converts to fat (slightly lossy); fat burns 1.5× when energy drops below 30% MAX_E.
