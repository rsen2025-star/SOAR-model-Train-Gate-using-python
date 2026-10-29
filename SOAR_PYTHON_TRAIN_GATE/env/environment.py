import os, sys, re

_ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SOAR_BIN = os.path.join(_ROOT, 'SOAR', 'bin')
os.add_dll_directory(_SOAR_BIN)
sys.path.insert(0, _SOAR_BIN)
import Python_sml_ClientInterface as sml

_AGENTS = os.path.join(_ROOT, 'agents')


class Environment:

    def __init__(self):
        self.kernel = self.train = self.controller_optimized = self.gate = None
        self._pending_ctrl_signal  = None
        self._pending_gate_command = None
        self._ctrl_signal_wme  = None
        self._gate_command_wme = None

    def _on_train_signal(self, id, user_data, agent, wme):
        self._pending_ctrl_signal = wme.GetValueAsString()

    def _on_ctrl_command(self, id, user_data, agent, wme):
        self._pending_gate_command = wme.GetValueAsString()

    def create_agents(self):
        self.kernel = sml.Kernel.CreateKernelInNewThread()
        self.train      = self.kernel.CreateAgent('train')
        self.controller = self.kernel.CreateAgent('controller')
        self.gate       = self.kernel.CreateAgent('gate')
        self.train.LoadProductions(os.path.join(_AGENTS, 'train', 'train.soar'))
        self.controller.LoadProductions(os.path.join(_AGENTS, 'controller', 'controller.soar'))
        self.gate.LoadProductions(os.path.join(_AGENTS, 'gate', 'gate.soar'))
        self.train.AddOutputHandler('signal', self._on_train_signal, None)
        self.controller.AddOutputHandler('command', self._on_ctrl_command, None)

    def tick(self):
        self.kernel.RunAllAgents(5, sml.sml_PHASE)
        self._deliver_signals()

    def _deliver_signals(self):
        if self._ctrl_signal_wme:
            self.controller.DestroyWME(self._ctrl_signal_wme)
            self._ctrl_signal_wme = None
        if self._gate_command_wme:
            self.gate.DestroyWME(self._gate_command_wme)
            self._gate_command_wme = None

        if self._pending_ctrl_signal:
            il = self.controller.GetInputLink()
            self._ctrl_signal_wme = self.controller.CreateStringWME(il, 'signal', self._pending_ctrl_signal)
            self.controller.Commit()
            self._pending_ctrl_signal = None

        if self._pending_gate_command:
            il = self.gate.GetInputLink()
            self._gate_command_wme = self.gate.CreateStringWME(il, 'command', self._pending_gate_command)
            self.gate.Commit()
            self._pending_gate_command = None
# for output purpose
    def get_states(self):
        def q(agent, attr):
            raw = agent.ExecuteCommandLine('print s1')
            m = re.search(r'\^' + re.escape(attr) + r'\s+(\S+)', raw)
            return m.group(1) if m else '-'
        return {
            'train': q(self.train, 'position'),
            'controller': q(self.controller, 'ctrl-state'),
            'gate': q(self.gate, 'gate-position')
        }

    def reset(self):
        """Re-initialise all three agents so the next cycle starts fresh."""
        for agent in (self.train, self.controller, self.gate):
            agent.InitSoar()
        self._pending_ctrl_signal  = None
        self._pending_gate_command = None
        self._ctrl_signal_wme  = None
        self._gate_command_wme = None

    def shutdown(self):
        if self.kernel:
            self.kernel.Shutdown()
            self.kernel = None
