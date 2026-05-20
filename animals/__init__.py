# animals/ — все виды животных симуляции
from animals.base      import Animal
from animals.herbivore import Herbivore
from animals.predator  import Predator
from animals.scavenger import Scavenger
from animals.omnivore  import Omnivore

__all__ = ["Animal", "Herbivore", "Predator", "Scavenger", "Omnivore"]
