"""A small integer puzzle to verify the local Z3 environment."""
from z3 import Ints, Solver, sat

x, y = Ints("x y")
solver = Solver()
solver.add(x + y == 10, x - y == 4, x >= 0, y >= 0)
assert solver.check() == sat
model = solver.model()
assert model[x].as_long() == 7 and model[y].as_long() == 3
print(f"Z3 OK: x={model[x]}, y={model[y]}")
