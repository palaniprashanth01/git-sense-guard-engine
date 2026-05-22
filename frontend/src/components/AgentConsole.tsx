import { useState } from 'react';
import { motion } from 'framer-motion';
import { Terminal, Play, Loader2, GitBranch, FileCode, Trash2, Code2, ShieldCheck, ShieldAlert, Wrench } from 'lucide-react';

type Level = 'info' | 'warn' | 'error' | 'success';

interface TranscriptEvent {
  role: string;
  level: Level;
  message: string;
  ts: number;
}

interface Finding {
  severity: string;
  category: string;
  evidence: string;
  rationale: string;
}

interface AuditResult {
  outcome: 'Clean' | 'Self-Healed' | 'Heal-Failed';
  audit_summary: string;
  findings: Finding[];
  healed_content: string | null;
  simulation: Record<string, unknown>;
  transcript: TranscriptEvent[];
}

const SAMPLE_DIFF = `import os

API_KEY = "sk-test-1234567890abcdefghij"  # hardcoded

def render(user_input):
    return f"<h1>{user_input}</h1>"  # unescaped XSS sink
`;

export function AgentConsole() {
  const [payload, setPayload] = useState({
    repo_url: '',
    branch: 'main',
    file_path: '',
    diff_content: ''
  });
  const [result, setResult] = useState<AuditResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [pushing, setPushing] = useState(false);
  const [pushSuccess, setPushSuccess] = useState<string | null>(null);
  const [pushError, setPushError] = useState<string | null>(null);

  const pushHealedFile = async () => {
    if (!result || !result.healed_content) return;
    if (result.outcome !== 'Self-Healed') {
      setPushError('Simulator did not certify this heal — push blocked by RULES.md §3.');
      return;
    }
    if (!payload.repo_url.trim()) {
      setPushError('Repository URL is required. Enter a real repo you have write access to before pushing.');
      return;
    }
    setPushing(true);
    setPushSuccess(null);
    setPushError(null);
    try {
      const response = await fetch('http://localhost:8000/push', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: payload.repo_url,
          file_path: payload.file_path,
          content: result.healed_content,
          commit_message: `git-sense(heal): automatically remediated Auditor findings in ${payload.file_path}`,
          branch: payload.branch || 'main'
        })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to push changes.');
      }
      setPushSuccess(data.message || 'Successfully committed and pushed healed changes!');
    } catch (err) {
      setPushError(err instanceof Error ? err.message : 'Push failed.');
    } finally {
      setPushing(false);
    }
  };

  const runAgentPipeline = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch('http://localhost:8000/api/agent/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`HTTP ${response.status}: ${detail}`);
      }
      const data: AuditResult = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pipeline crashed.');
    } finally {
      setLoading(false);
    }
  };

  const fillSample = () => {
    // Leave repo_url empty so the demo doesn't accidentally push to a fake repo.
    // The user fills it in only when they want to exercise the Push step.
    setPayload((prev) => ({
      ...prev,
      branch: 'main',
      file_path: 'app/views.py',
      diff_content: SAMPLE_DIFF,
    }));
  };

  const levelStyle = (lvl: Level) => {
    switch (lvl) {
      case 'warn': return 'text-amber-400 border-amber-500/40';
      case 'error': return 'text-rose-400 border-rose-500/40';
      case 'success': return 'text-emerald-400 border-emerald-500/40';
      default: return 'text-sky-300 border-sky-500/30';
    }
  };

  const outcomeBadge = (outcome: AuditResult['outcome']) => {
    const map = {
      'Clean': { icon: <ShieldCheck size={14} />, cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40' },
      'Self-Healed': { icon: <Wrench size={14} />, cls: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/40' },
      'Heal-Failed': { icon: <ShieldAlert size={14} />, cls: 'bg-rose-500/15 text-rose-300 border-rose-500/40' },
    } as const;
    const m = map[outcome];
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border ${m.cls}`}>
        {m.icon}{outcome}
      </span>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="max-w-6xl mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-8 p-1"
    >
      {/* Input panel */}
      <div className="lg:col-span-5 bg-surface p-6 rounded-xl border border-white/5 shadow-xl flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-primary/10 rounded-xl text-primary shadow-lg shadow-primary/5">
              <Code2 size={24} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white tracking-tight">Agent Control</h3>
              <p className="text-gray-400 text-xs mt-0.5">Auditor → Architect → Simulator</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">Repository URL</label>
              <input
                type="text"
                value={payload.repo_url}
                onChange={e => setPayload({ ...payload, repo_url: e.target.value })}
                placeholder="https://github.com/your-username/repo"
                className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-primary transition-all text-sm"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5 flex items-center gap-1">
                  <GitBranch size={12} className="text-gray-400" />Target Branch
                </label>
                <input
                  type="text"
                  value={payload.branch}
                  onChange={e => setPayload({ ...payload, branch: e.target.value })}
                  placeholder="main"
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-primary transition-all text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5 flex items-center gap-1">
                  <FileCode size={12} className="text-gray-400" />File to Guard
                </label>
                <input
                  type="text"
                  value={payload.file_path}
                  onChange={e => setPayload({ ...payload, file_path: e.target.value })}
                  placeholder="app/views.py"
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-primary transition-all text-sm"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400">Proposed Patch / File Body</label>
                <button onClick={fillSample} className="text-xs text-primary hover:underline">load sample</button>
              </div>
              <textarea
                value={payload.diff_content}
                onChange={e => setPayload({ ...payload, diff_content: e.target.value })}
                placeholder="Paste a diff or full file body to audit..."
                className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-primary transition-all text-sm font-mono h-40 resize-none"
              />
            </div>
          </div>
        </div>

        <div className="mt-8 pt-4 border-t border-white/5">
          <button
            onClick={runAgentPipeline}
            disabled={loading || !payload.file_path || !payload.diff_content}
            className="w-full py-3 bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/95 hover:to-indigo-600/95 text-white font-semibold rounded-lg shadow-lg shadow-primary/20 flex items-center justify-center gap-2 transition-all active:scale-98 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <><Loader2 className="w-5 h-5 animate-spin" /><span>Pipeline running...</span></>
            ) : (
              <><Play className="w-4 h-4 fill-white" /><span>Trigger Self-Healing Guard Loop</span></>
            )}
          </button>
        </div>
      </div>

      {/* Output panel */}
      <div className="lg:col-span-7 flex flex-col bg-slate-950 rounded-xl border border-white/10 shadow-2xl overflow-hidden h-[640px]">
        <div className="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Terminal size={16} className="text-primary" />
            <span className="text-xs font-mono font-bold tracking-wider uppercase text-slate-300">Validation Matrix</span>
          </div>
          <div className="flex items-center gap-3">
            {result && outcomeBadge(result.outcome)}
            {(result || error) && (
              <button onClick={() => { setResult(null); setError(null); }} className="text-slate-500 hover:text-slate-300 p-1 rounded hover:bg-white/5" title="Clear">
                <Trash2 size={14} />
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 p-5 font-mono text-xs overflow-y-auto space-y-3 scrollbar-thin scrollbar-thumb-slate-800">
          {!result && !error && !loading && (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-3">
              <Terminal size={32} className="text-slate-700 animate-pulse" />
              <p className="text-center font-sans">
                Idle. Configure the guard loop on the left and press trigger.
              </p>
            </div>
          )}

          {loading && (
            <div className="text-slate-400 animate-pulse pl-1">Running multi-agent pipeline...</div>
          )}

          {error && (
            <div className="text-rose-400 bg-rose-500/10 border-l-2 border-rose-500 px-3 py-2 rounded-r">
              <div className="font-bold mb-1">PIPELINE ERROR</div>
              <div className="whitespace-pre-wrap">{error}</div>
            </div>
          )}

          {result && (
            <>
              <div>
                <div className="text-slate-500 uppercase text-[10px] tracking-widest mb-1">Transcript</div>
                {result.transcript.map((ev, i) => (
                  <div key={i} className={`border-l-2 pl-3 py-1 my-1 ${levelStyle(ev.level)}`}>
                    <span className="opacity-60">[{ev.role}]</span> {ev.message}
                  </div>
                ))}
              </div>

              {result.audit_summary && (
                <div>
                  <div className="text-slate-500 uppercase text-[10px] tracking-widest mb-1">Auditor Summary</div>
                  <div className="text-slate-200 whitespace-pre-wrap font-sans bg-white/[0.02] p-3 rounded border border-white/5">
                    {result.audit_summary}
                  </div>
                </div>
              )}

              {result.findings.length > 0 && (
                <div>
                  <div className="text-slate-500 uppercase text-[10px] tracking-widest mb-1">Findings ({result.findings.length})</div>
                  <div className="space-y-2">
                    {result.findings.map((f, i) => (
                      <div key={i} className="border border-white/5 rounded p-2 bg-white/[0.02]">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                            ['high', 'critical'].includes(f.severity?.toLowerCase()) ? 'bg-rose-500/20 text-rose-300' :
                            f.severity?.toLowerCase() === 'medium' ? 'bg-amber-500/20 text-amber-300' :
                            'bg-slate-500/20 text-slate-300'
                          }`}>{f.severity}</span>
                          <span className="text-slate-400 text-[11px]">{f.category}</span>
                        </div>
                        <div className="text-slate-200 text-[11px] font-sans">{f.rationale}</div>
                        {f.evidence && (
                          <pre className="text-slate-400 text-[10px] mt-1 bg-black/40 p-1.5 rounded overflow-x-auto">{f.evidence}</pre>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.healed_content && (
                <div className="space-y-2">
                  <div className="text-slate-500 uppercase text-[10px] tracking-widest mb-1 font-semibold">
                    {result.outcome === 'Heal-Failed' ? 'Rejected Healed Content (Simulation Failed)' : 'Healed Content'}
                  </div>
                  <pre className={`p-3 rounded text-[11px] overflow-x-auto whitespace-pre-wrap border ${
                    result.outcome === 'Heal-Failed' 
                      ? 'text-rose-300 bg-rose-500/5 border-rose-500/20' 
                      : 'text-emerald-200 bg-emerald-500/5 border-emerald-500/20'
                  }`}>{result.healed_content}</pre>
                  
                  {result.outcome === 'Self-Healed' && (
                    <div className="pt-2">
                      <button
                        onClick={pushHealedFile}
                        disabled={pushing || !payload.repo_url.trim()}
                        title={!payload.repo_url.trim() ? 'Enter a Repository URL above before pushing' : undefined}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-900 disabled:text-emerald-300/50 disabled:cursor-not-allowed text-white font-medium text-xs rounded transition-all active:scale-98 cursor-pointer"
                      >
                        {pushing ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <GitBranch size={13} />
                        )}
                        <span>Push Healed File to Git</span>
                      </button>
                      {pushSuccess && (
                        <div className="mt-2 text-emerald-400 text-xs font-semibold bg-emerald-500/10 border-l-2 border-emerald-500 px-3 py-1.5 rounded-r">
                          {pushSuccess}
                        </div>
                      )}
                      {pushError && (
                        <div className="mt-2 text-rose-400 text-xs font-semibold bg-rose-500/10 border-l-2 border-rose-500 px-3 py-1.5 rounded-r">
                          {pushError}
                        </div>
                      )}
                    </div>
                  )}

                  {result.outcome === 'Heal-Failed' && (
                    <div className="bg-rose-500/10 border-l-2 border-rose-500 p-3 rounded-r space-y-1 mt-2 font-mono">
                      <div className="flex items-center gap-1.5 text-rose-400 font-bold text-[11px]">
                        <ShieldAlert size={14} />
                        <span>Simulation Verification Failed</span>
                      </div>
                      <p className="text-slate-300 font-sans text-xs">
                        The healed code generated by the Architect has syntax or safety errors and was blocked from shipping.
                      </p>
                      {result.simulation && (result.simulation as any).error && (
                        <div className="bg-black/40 p-2 rounded border border-rose-500/10 font-mono text-[10px] text-rose-300 whitespace-pre-wrap mt-1">
                          Error: {(result.simulation as any).error}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div>
                <div className="text-slate-500 uppercase text-[10px] tracking-widest mb-1">Simulation</div>
                <pre className="text-slate-300 bg-black/40 border border-white/5 p-2 rounded text-[10px] overflow-x-auto">{JSON.stringify(result.simulation, null, 2)}</pre>
              </div>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default AgentConsole;
