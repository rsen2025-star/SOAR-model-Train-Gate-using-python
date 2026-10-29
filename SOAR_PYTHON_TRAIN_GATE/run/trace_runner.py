"""
trace_runner.py — Soar rule-firing trace + tick state log

Outputs two files:
  run/trace_raw.txt   — every Soar production firing, labelled by agent
  run/trace_ticks.txt — per-tick state snapshot + Python signal delivery events
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'env'))
from environment import Environment
import Python_sml_ClientInterface as sml

# ── Configuration ──────────────────────────────────────────────────────────────

NUM_CYCLES  = 1
MAX_TICKS   = 200     # safety cap per cycle
INITIAL     = {'train': 'far', 'controller': '0', 'gate': 'up'}
OUTPUT_DIR  = os.path.dirname(os.path.abspath(__file__))
RAW_FILE    = os.path.join(OUTPUT_DIR, 'trace_raw.txt')
TICKS_FILE  = os.path.join(OUTPUT_DIR, 'trace_ticks.txt')

# Productions to skip — fire every tick and add noise
SKIP_PRODUCTIONS = {
    'train*clear*output',
    'controller*clear*output',
}

# Raw Soar lines to skip — idle-agent impasse noise (no relabeling, just dropped)
SKIP_SUBSTRINGS = {
    'state no-change',
}

# ── State ──────────────────────────────────────────────────────────────────────

_current_tick = 0
_raw_file     = None


# ── Print event callbacks (one per agent) ─────────────────────────────────────

def _make_print_handler(label):
    """Return a RegisterForPrintEvent callback that writes [LABEL] prefixed lines."""
    def handler(id, user_data, agent, message):
        msg = message.strip()
        if not msg:
            return
        # Filter noisy always-on productions
        if any(skip in msg for skip in SKIP_PRODUCTIONS):
            return
        # Filter idle-agent impasse noise (raw text otherwise untouched)
        if any(skip in msg for skip in SKIP_SUBSTRINGS):
            return
        _raw_file.write(f"  [{label}] {msg}\n")
    return handler


# ── Signal delivery wrapper ────────────────────────────────────────────────────

class TracingEnvironment(Environment):
    """Environment subclass that logs signal deliveries to the ticks file."""

    def __init__(self, ticks_fh):
        super().__init__()
        self._ticks_fh = ticks_fh

    def _deliver_signals(self):
        # Remove stale WMEs first (same as parent)
        if self._ctrl_signal_wme:
            self.controller.DestroyWME(self._ctrl_signal_wme)
            self._ctrl_signal_wme = None
        if self._gate_command_wme:
            self.gate.DestroyWME(self._gate_command_wme)
            self._gate_command_wme = None

        # Deliver and log
        if self._pending_ctrl_signal:
            il = self.controller.GetInputLink()
            self._ctrl_signal_wme = self.controller.CreateStringWME(
                il, 'signal', self._pending_ctrl_signal)
            self.controller.Commit()
            self._ticks_fh.write(
                f"  >>> PY COMM @ tick {_current_tick:02d}:  "
                f"signal={self._pending_ctrl_signal!r:12s}  "
                f"train --[python]--> controller\n")
            self._pending_ctrl_signal = None

        if self._pending_gate_command:
            il = self.gate.GetInputLink()
            self._gate_command_wme = self.gate.CreateStringWME(
                il, 'command', self._pending_gate_command)
            self.gate.Commit()
            self._ticks_fh.write(
                f"  >>> PY COMM @ tick {_current_tick:02d}:  "
                f"command={self._pending_gate_command!r:12s}  "
                f"controller --[python]--> gate\n")
            self._pending_gate_command = None


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    global _current_tick, _raw_file

    with open(RAW_FILE, 'w', encoding='utf-8') as raw_fh, open(TICKS_FILE, 'w', encoding='utf-8') as ticks_fh:
        _raw_file = raw_fh

        # Headers
        raw_fh.write("Soar Production Firings — Railroad Crossing Simulation\n")
        raw_fh.write(f"Cycles: {NUM_CYCLES}  |  Skipped: {sorted(SKIP_PRODUCTIONS)}\n")
        raw_fh.write("=" * 70 + "\n\n")

        ticks_fh.write("Tick State Log — Railroad Crossing Simulation\n")
        ticks_fh.write(f"Cycles: {NUM_CYCLES}\n")
        ticks_fh.write("=" * 70 + "\n\n")

        # Build environment
        env = TracingEnvironment(ticks_fh)
        env.create_agents()

        # Enable watch level 3 (rule firings) on each agent
        env.train.ExecuteCommandLine('watch --productions')
        env.controller.ExecuteCommandLine('watch --productions')
        env.gate.ExecuteCommandLine('watch --productions')

        # Register print callbacks
        env.train.RegisterForPrintEvent(
            sml.smlEVENT_PRINT, _make_print_handler('TRAIN'), None)
        env.controller.RegisterForPrintEvent(
            sml.smlEVENT_PRINT, _make_print_handler('CTRL '), None)
        env.gate.RegisterForPrintEvent(
            sml.smlEVENT_PRINT, _make_print_handler('GATE '), None)

        try:
            for cycle in range(1, NUM_CYCLES + 1):
                ticks_fh.write(f"\n=== Cycle {cycle} ===\n")
                raw_fh.write(f"\n{'=' * 20} Cycle {cycle} {'=' * 20}\n\n")

                tick = 0
                left_initial = False

                while tick < MAX_TICKS:
                    tick += 1
                    _current_tick = tick

                    # Raw file — tick separator
                    raw_fh.write(f"── Tick {tick:02d} {'─' * 58}\n")

                    # Run agents
                    env.tick()

                    # Ticks file — state snapshot
                    s = env.get_states()
                    ticks_fh.write(
                        f"Tick {tick:02d}:  "
                        f"train={s['train']:<10s}  "
                        f"ctrl={s['controller']:<4s}  "
                        f"gate={s['gate']}\n")

                    raw_fh.flush()
                    ticks_fh.flush()

                    # Auto-detect cycle completion
                    if s != INITIAL:
                        left_initial = True
                    elif left_initial:
                        ticks_fh.write(f"--- cycle complete at tick {tick} ---\n")
                        raw_fh.write(f"--- cycle complete at tick {tick} ---\n")
                        break

                if cycle < NUM_CYCLES:
                    env.reset()

        except Exception as e:
            msg = f"\n*** EXCEPTION at cycle {cycle}, tick {_current_tick}: {type(e).__name__}: {e}\n"
            raw_fh.write(msg)
            ticks_fh.write(msg)
            import traceback
            traceback.print_exc()
        finally:
            env.shutdown()

    print(f"Done. Written to:")
    print(f"  {RAW_FILE}")
    print(f"  {TICKS_FILE}")


if __name__ == '__main__':
    main()
