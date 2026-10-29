import tkinter as tk
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'env'))
from environment import Environment

# ── Working memory reader ──────────────────────────────────────────────────────

_TRAIN_ATTRS = {'position', 'train-count'}
_CTRL_ATTRS  = {'ctrl-state'}
_GATE_ATTRS  = {'gate-position', 'gate-count'}

def wm_lines(agent, keep):
    """Return list of (attr, value) pairs from agent's top state, filtered by keep."""
    raw = agent.ExecuteCommandLine('print s1')
    pairs = re.findall(r'\^(\S+)\s+(\S+)', raw)
    result = [(a, v) for a, v in pairs if a in keep]
    op_id = next((v for a, v in pairs if a == 'operator'), None)
    if op_id:
        op_raw = agent.ExecuteCommandLine(f'print {op_id}')
        m = re.search(r'\^name\s+(\S+)', op_raw)
        if m:
            result.append(('operator', m.group(1)))
    return result

# ── Environment ────────────────────────────────────────────────────────────────

env = Environment()
env.create_agents()

# ── UI ────────────────────────────────────────────────────────────────────────

root = tk.Tk()
root.title("Tick Viewer")
root.configure(bg='#1e1e2e')
root.resizable(False, False)

FONT_MONO  = ('Courier New', 11)
FONT_BOLD  = ('Courier New', 11, 'bold')
FONT_HEAD  = ('Courier New', 13, 'bold')
BG         = '#1e1e2e'
BG2        = '#2a2a3e'
FG         = '#cdd6f4'
FG_DIM     = '#6c7086'
GREEN      = '#a6e3a1'
YELLOW     = '#f9e2af'
BLUE       = '#89b4fa'
RED        = '#f38ba8'
ORANGE     = '#fab387'

# ── Header ────────────────────────────────────────────────────────────────────
hdr = tk.Frame(root, bg=BG, pady=8)
hdr.pack(fill=tk.X, padx=16)

tick_lbl = tk.Label(hdr, text='Cycle 1 — Tick 0  (initial)', font=('Courier New', 22, 'bold'),
                    bg=BG, fg=GREEN)
tick_lbl.pack(side=tk.LEFT)

# ── State summary bar ─────────────────────────────────────────────────────────
summary_frame = tk.Frame(root, bg=BG2, pady=6)
summary_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

def state_badge(parent, label, var, color):
    tk.Label(parent, text=label, font=FONT_MONO, bg=BG2, fg=FG_DIM).pack(side=tk.LEFT, padx=(12,2))
    tk.Label(parent, textvariable=var, font=FONT_BOLD, bg=BG2, fg=color).pack(side=tk.LEFT, padx=(0,8))

train_var = tk.StringVar(value='far')
ctrl_var  = tk.StringVar(value='0')
gate_var  = tk.StringVar(value='up')

state_badge(summary_frame, 'train=', train_var, BLUE)
state_badge(summary_frame, 'controller=', ctrl_var, YELLOW)
state_badge(summary_frame, 'gate=', gate_var, ORANGE)

# ── Working memory panels ─────────────────────────────────────────────────────
panels_frame = tk.Frame(root, bg=BG)
panels_frame.pack(fill=tk.BOTH, padx=16, pady=4)

def make_wm_panel(parent, title, col):
    frame = tk.Frame(parent, bg=BG2, padx=10, pady=8, relief=tk.FLAT, bd=1)
    frame.grid(row=0, column=col, padx=6, sticky='nsew')
    parent.columnconfigure(col, weight=1)
    tk.Label(frame, text=title, font=FONT_BOLD, bg=BG2, fg=FG).pack(anchor='w', pady=(0,6))
    text = tk.Text(frame, width=32, height=10, font=FONT_MONO,
                   bg=BG2, fg=FG, insertbackground=FG,
                   relief=tk.FLAT, state=tk.DISABLED, wrap=tk.NONE)
    text.pack(fill=tk.BOTH)
    text.tag_config('key',   foreground=BLUE)
    text.tag_config('val',   foreground=GREEN)
    text.tag_config('op',    foreground=YELLOW)
    text.tag_config('dim',   foreground=FG_DIM)
    return text

train_wm  = make_wm_panel(panels_frame, 'Train WM',      0)
ctrl_wm   = make_wm_panel(panels_frame, 'Controller WM', 1)
gate_wm   = make_wm_panel(panels_frame, 'Gate WM',       2)

def set_wm(widget, pairs):
    widget.config(state=tk.NORMAL)
    widget.delete('1.0', tk.END)
    for attr, val in pairs:
        widget.insert(tk.END, f'  ^', 'dim')
        tag = 'op' if attr == 'operator' else 'key'
        widget.insert(tk.END, attr, tag)
        widget.insert(tk.END, '  ', 'dim')
        widget.insert(tk.END, val + '\n', 'val')
    if not pairs:
        widget.insert(tk.END, '  —\n', 'dim')
    widget.config(state=tk.DISABLED)

# ── Log panel ─────────────────────────────────────────────────────────────────
log_outer = tk.Frame(root, bg=BG)
log_outer.pack(fill=tk.BOTH, padx=16, pady=(8,4))
tk.Label(log_outer, text='Event Log', font=FONT_BOLD, bg=BG, fg=FG_DIM).pack(anchor='w')
log = tk.Text(log_outer, height=6, font=FONT_MONO, bg=BG2, fg=FG,
              relief=tk.FLAT, state=tk.DISABLED, wrap=tk.NONE)
log.pack(fill=tk.X)
log.tag_config('tick',  foreground=YELLOW)
log.tag_config('event', foreground=ORANGE)
log.tag_config('dim',   foreground=FG_DIM)

def log_append(tick, states, prev_states):
    log.config(state=tk.NORMAL)
    log.insert(tk.END, f'Tick {tick:>2}  ', 'tick')
    changes = []
    if states['train'] != prev_states['train']:
        changes.append(f"train {prev_states['train']}→{states['train']}")
    if states['controller'] != prev_states['controller']:
        changes.append(f"ctrl {prev_states['controller']}→{states['controller']}")
    if states['gate'] != prev_states['gate']:
        changes.append(f"gate {prev_states['gate']}→{states['gate']}")
    if changes:
        log.insert(tk.END, '  '.join(changes) + '\n', 'event')
    else:
        log.insert(tk.END, '(no state change)\n', 'dim')
    log.see(tk.END)
    log.config(state=tk.DISABLED)

# ── State ──────────────────────────────────────────────────────────────────────
_tick_count = [0]
_cycle_count = [1]
_prev_states = [{'train': 'far', 'controller': '0', 'gate': 'up'}]

def refresh(states, tick, is_initial=False):
    train_var.set(states['train'])
    ctrl_var.set(states['controller'])
    gate_var.set(states['gate'])
    label = '(initial)' if is_initial else ''
    tick_lbl.config(text=f'Cycle {_cycle_count[0]} \u2014 Tick {tick}  {label}')
    set_wm(train_wm, wm_lines(env.train,      _TRAIN_ATTRS))
    set_wm(ctrl_wm,  wm_lines(env.controller, _CTRL_ATTRS))
    set_wm(gate_wm,  wm_lines(env.gate,       _GATE_ATTRS))

def advance():
    prev = dict(_prev_states[0])
    env.tick()
    _tick_count[0] += 1
    s = env.get_states()
    refresh(s, _tick_count[0])
    log_append(_tick_count[0], s, prev)
    _prev_states[0] = dict(s)

def reset_cycle():
    env.reset()
    _tick_count[0] = 0
    _cycle_count[0] += 1
    _prev_states[0] = {'train': 'far', 'controller': '0', 'gate': 'up'}
    s = env.get_states()
    refresh(s, 0, is_initial=True)
    log.config(state=tk.NORMAL)
    log.insert(tk.END, f'--- Cycle {_cycle_count[0]} ---\n', 'tick')
    log.see(tk.END)
    log.config(state=tk.DISABLED)

# ── Initial render ────────────────────────────────────────────────────────────
s0 = env.get_states()
refresh(s0, 0, is_initial=True)

# ── Button ────────────────────────────────────────────────────────────────────
btn_frame = tk.Frame(root, bg=BG, pady=10)
btn_frame.pack()
tk.Button(btn_frame, text='  Next Tick  ', command=advance,
          font=('Courier New', 13, 'bold'), bg='#313244', fg=GREEN,
          activebackground='#45475a', activeforeground=GREEN,
          relief=tk.FLAT, padx=8, pady=6).pack(side=tk.LEFT, padx=6)
tk.Button(btn_frame, text='  Reset Cycle  ', command=reset_cycle,
          font=('Courier New', 13, 'bold'), bg='#313244', fg=YELLOW,
          activebackground='#45475a', activeforeground=YELLOW,
          relief=tk.FLAT, padx=8, pady=6).pack(side=tk.LEFT, padx=6)

root.mainloop()
env.shutdown()
