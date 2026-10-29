# Railroad Crossing — Soar Multi-Agent Simulation

## Context

This project simulates a railroad crossing with three agents: a **Train**, a **Controller**, and a **Gate**.
Each agent is a separate program written in **Soar**, a rule-based AI system. All decisions are made by Soar rules.
Python only starts the agents, moves the simulation forward one step ("tick") at a time, and passes messages between them, because the agents cannot see each other directly.

One full cycle (train arrives, gate closes, train passes, gate opens) takes **27 ticks**.

## Soar files (`agents/`)

| File | What it does |
|---|---|
| `train/train.soar` | The train moves **far → near → in → far**. It waits 6 ticks at each position before moving on. It sends an `approach` message when it gets near and an `exit` message when it leaves. |
| `controller/controller.soar` | The controller moves through states **0 → 1 → 2 → 3 → 0**. 0 = idle, 1 = train approaching, 2 = gate told to lower, 3 = train has left. It sends a `lower` command to the gate when it gets `approach` and a `raise` command when it gets `exit`. |
| `gate/gate.soar` | The gate moves **up → lowering → down → raising → up**. When it gets a command, it takes 2 ticks to finish moving. |

## Python files

| File | What it does |
|---|---|
| `env/environment.py` | Starts the three Soar agents, runs them one tick at a time, and passes messages: train → controller and controller → gate. |
| `run/trace_runner.py` | Runs one full cycle and saves two text files in `run/`:<br>`trace_raw.txt` lists every Soar rule that fired, tick by tick.<br>`trace_ticks.txt` shows each agent's state at every tick and every message passed. |
| `ui/tick_viewer.py` | Opens a window for stepping through the simulation by hand, one tick at a time. |

`SOAR/bin/` contains the Soar engine and its Python connector. Do not change or move these files.

## Requirements

- Windows
- **Python 3.12, 64-bit**. Download it from https://www.python.org/downloads/. Other Python versions will not work.

To check your Python version, run:

```
python --version
```

It should print `Python 3.12.x`.

## How to run

1. Open this folder in File Explorer. Click the address bar, type `cmd`, and press **Enter**. A terminal opens in this folder.

2. **To make the trace files**, run:

   ```
   python run/trace_runner.py
   ```

   When it says `Done`, open `run/trace_raw.txt` and `run/trace_ticks.txt` to see the results.

3. **To use the step-by-step viewer**, run:

   ```
   python ui/tick_viewer.py
   ```

   - **Next Tick** moves the simulation forward one step.
   - **Reset Cycle** starts again from the beginning.
   - Close the window to stop.
