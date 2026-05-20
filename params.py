# params.py — параметры симуляции и геометрия экрана
# SimParams  — слайдерные настройки, которые пользователь меняет в реальном времени.
# Layout     — вычисляет размеры мирового поля и панели при изменении окна.

from constants import CELL


class SimParams:
    """Параметры симуляции, управляемые слайдерами в UI.

    Все значения применяются каждый тик; их можно менять на лету.
    """
    def __init__(self):
        self.mutation_chance   = 0.40   # вероятность мутации каждого трейта при рождении
        self.mutation_std      = 0.18   # σ нормального распределения мутации (Гаусс)
        self.herb_hunger       = 0.03   # дополнительный расход энергии травоядных/тик
        self.pred_hunger       = 0.06   # дополнительный расход энергии хищников/тик
        self.thirst_mult       = 1.0    # множитель скорости потери гидратации
        self.speciation_thresh = 10     # накоплено мутаций → событие видообразования


class Layout:
    """Вычисляет и хранит геометрию окна.

    Мировое поле занимает левую часть экрана,
    правая часть (~30%) — информационная панель.
    Пересчитывается при изменении размера окна (VIDEORESIZE).
    """
    PANEL_FRAC = 0.30   # доля ширины экрана под панель

    def __init__(self, screen_w: int, screen_h: int):
        self.update(screen_w, screen_h)

    def update(self, sw: int, sh: int):
        self.sw      = sw
        self.sh      = sh
        self.panel_w = max(320, int(sw * self.PANEL_FRAC))
        self.world_w = sw - self.panel_w - 6
        self.world_h = sh
        self.panel_x = self.world_w + 3
        self.cols    = self.world_w // CELL   # ширина мира в клетках
        self.rows    = self.world_h // CELL   # высота мира в клетках
