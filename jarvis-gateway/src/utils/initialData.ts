import { VirtualFile, JarvisNote } from '../types.ts';

export const INITIAL_FILES: VirtualFile[] = [
  {
    id: 'folder-projects',
    name: 'Projects',
    path: '/Projects',
    content: '',
    type: 'folder',
    parentId: null,
    createdAt: Date.now() - 3600000,
    updatedAt: Date.now() - 3600000,
  },
  {
    id: 'folder-research',
    name: 'Research',
    path: '/Research',
    content: '',
    type: 'folder',
    parentId: null,
    createdAt: Date.now() - 3600000,
    updatedAt: Date.now() - 3600000,
  },
  {
    id: 'folder-screenshots',
    name: 'Screenshots',
    path: '/Screenshots',
    content: '',
    type: 'folder',
    parentId: null,
    createdAt: Date.now() - 3600000,
    updatedAt: Date.now() - 3600000,
  },
  {
    id: 'file-arc-reactor',
    name: 'arc_reactor.py',
    path: '/Projects/arc_reactor.py',
    type: 'file',
    parentId: 'folder-projects',
    fileType: 'py',
    createdAt: Date.now() - 2500000,
    updatedAt: Date.now() - 2500000,
    content: `# STARK INDUSTRIES - ARC REACTOR TELEMETRY SIMULATION
import math
import time

class ArcReactor:
    def __init__(self, core_element="Palladium-Isotope-V"):
        self.core = core_element
        self.output_gigawatts = 3.0
        self.temperature_kelvin = 8500.0
        self.containment_efficiency = 0.998

    def optimize_output(self, target_gw: float):
        """Calibrates magnetic constriction coils for peak energy output."""
        delta = target_gw - self.output_gigawatts
        flux_adjustment = math.sqrt(abs(delta)) * 0.42
        self.output_gigawatts = target_gw
        print(f"[JARVIS] Arc core stabilized at {self.output_gigawatts:.2f} GW. Flux delta: {flux_adjustment:.4f}")
        return True

if __name__ == "__main__":
    reactor = ArcReactor()
    reactor.optimize_output(3.85)
`,
  },
  {
    id: 'file-stark-protocol',
    name: 'stark_protocol.ts',
    path: '/Projects/stark_protocol.ts',
    type: 'file',
    parentId: 'folder-projects',
    fileType: 'ts',
    createdAt: Date.now() - 1800000,
    updatedAt: Date.now() - 1800000,
    content: `// J.A.R.V.I.S. AUTOMATION SUBSYSTEM
export interface VoiceCommandSubsystem {
  audioSamplingRate: number;
  wakeWordSensitivity: number;
  continuousListening: boolean;
  capabilities: {
    fileSystemManagement: boolean;
    screenCaptureVision: boolean;
    videoTelemetryNotes: boolean;
    dynamicCodeExecution: boolean;
  };
}

export const JARVIS_CONFIG: VoiceCommandSubsystem = {
  audioSamplingRate: 48000,
  wakeWordSensitivity: 0.95,
  continuousListening: true,
  capabilities: {
    fileSystemManagement: true,
    screenCaptureVision: true,
    videoTelemetryNotes: true,
    dynamicCodeExecution: true,
  },
};
`,
  },
  {
    id: 'file-quantum-notes',
    name: 'quantum_propulsion.md',
    path: '/Research/quantum_propulsion.md',
    type: 'file',
    parentId: 'folder-research',
    fileType: 'md',
    createdAt: Date.now() - 900000,
    updatedAt: Date.now() - 900000,
    content: `# Quantum Propulsion Research Dossier

- **Objective:** Sub-orbital vector stabilization with minimal thermal signature.
- **Key Equation:** $\\Delta v = I_{sp} g_0 \\ln(m_0 / m_f)$
- **Status:** Bench testing synthetic fuel composites.
- **Jarvis Directive:** Monitor vibrational resonance during full thrust simulation.
`,
  },
];

export const INITIAL_NOTES: JarvisNote[] = [
  {
    id: 'note-1',
    title: 'Voice Control Directive Manual',
    content: `Try speaking any of these natural voice commands to JARVIS:
- "Jarvis, create a folder named Artificial Intelligence"
- "Create file neural_net.py and write print('Model loaded')"
- "Jarvis, write in file neural_net.py: # Updated parameters"
- "Take a screenshot" or "Capture screen"
- "Jarvis, take note: Calibrate mark 85 repulsor capacitors"
- "Summarize this video" or "Take note of this video timestamp"`,
    category: 'General',
    tags: ['Jarvis', 'Commands', 'Guide'],
    pinned: true,
    createdAt: Date.now() - 7200000,
    updatedAt: Date.now() - 7200000,
  },
  {
    id: 'note-2',
    title: 'Video Note-taking System Protocol',
    content: `When watching lectures, coding tutorials, or YouTube streams:
1. Load any video link or share your active screen/tab
2. Click "Capture Moment" or speak "Jarvis, note this moment" to save the exact timestamp
3. Speak "Jarvis, summarize this video" to produce an executive study guide with key takeaways and action points.`,
    category: 'Video Notes',
    tags: ['Video', 'Study', 'Timestamps'],
    pinned: true,
    createdAt: Date.now() - 3600000,
    updatedAt: Date.now() - 3600000,
  },
];
