import sys
import warnings

# Определяем, использовать ли print вместо display
if hasattr(sys, 'frozen'):  # Если код выполняется в собранном файле
    def display(*args, **kwargs):
        print(*args, **kwargs)

warnings.filterwarnings("ignore")
print("d2loadout update started")
