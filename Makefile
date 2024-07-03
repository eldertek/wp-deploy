# Variables
PYTHON = python3
PIP = pip3
FLAKE8 = flake8
BLACK = black
ISORT = isort

# Chemins
SRC_DIR = .

# Commandes
.PHONY: install lint format fix-all

install:
	$(PIP) install flake8 black isort

lint:
	$(FLAKE8) $(SRC_DIR)

format:
	$(BLACK) $(SRC_DIR)
	$(ISORT) $(SRC_DIR)

fix-all: format lint
	@echo "Correction et vérification terminées."

help:
	@echo "Commandes disponibles:"
	@echo "  make install : Installe les dépendances (flake8, black, isort)"
	@echo "  make lint    : Vérifie le code avec flake8"
	@echo "  make format  : Formate le code avec black et isort"
	@echo "  make fix-all : Formate le code et vérifie avec flake8"
