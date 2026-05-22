import React, { useState } from 'react';
import { RepoInput } from './components/RepoInput';
import { AnalysisResults } from './components/AnalysisResults';
import { Sparkles, LayoutDashboard, GitBranch, FileCode, AlertTriangle, Lightbulb, GitCommit, FileText, Menu, X, Terminal } from 'lucide-react';
import clsx from 'clsx';
import { AgentConsole } from './components/AgentConsole';

interface AnalysisData {
  repo_id: string;
  status: string;
  bugs: any[];
  suggestions: any[];
  readme: string;
  structure: string;
  file_summaries: any[];
  commits: any[];
}

function App() {
  const [loading, setLoading] = useState(false);
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [currentRepoUrl, setCurrentRepoUrl] = useState<string>('');

  const handleAnalyze = async (url: string) => {
    setLoading(true);
    setError(null);
    setAnalysisData(null);
    setCurrentRepoUrl(url);
    try {
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: url }),
      });
      const data = await response.json();

      // Poll for results
      const pollInterval = setInterval(async () => {
        const resultResponse = await fetch(`http://localhost:8000/results/${data.repo_id}`);
        if (resultResponse.ok) {
          const resultData = await resultResponse.json();

          // Update data even if still processing (progressive rendering)
          if (resultData.status === 'completed' || resultData.status === 'processing') {
            setAnalysisData(resultData);
          }

          if (resultData.status === 'completed') {
            clearInterval(pollInterval);
            setLoading(false);
          } else if (resultData.status === 'failed') {
            clearInterval(pollInterval);
            setError('Analysis failed. Please check the repository URL and try again.');
            setLoading(false);
          }
        } else {
          clearInterval(pollInterval);
          setError('Failed to fetch analysis results. Please try again.');
          setLoading(false);
        }
      }, 1000); // Poll faster for smoother updates
    } catch (err) {
      setError('Failed to start analysis. Please try again.');
      setLoading(false);
    }
  };

  const navItems = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard size={20} /> },
    { id: 'structure', label: 'Structure', icon: <GitBranch size={20} /> },
    { id: 'files', label: 'File Summaries', icon: <FileCode size={20} /> },
    { id: 'bugs', label: 'Bugs & Security', icon: <AlertTriangle size={20} /> },
    { id: 'suggestions', label: 'Suggestions', icon: <Lightbulb size={20} /> },
    { id: 'commits', label: 'Commit History', icon: <GitCommit size={20} /> },
    { id: 'readme', label: 'README', icon: <FileText size={20} /> },
    { id: 'agent-console', label: 'Agent Autonomy', icon: <Terminal size={20} /> },
  ];

  return (
    <div className="min-h-screen bg-dark text-white flex overflow-hidden">
      {/* Sidebar */}
      <aside className={clsx(
        "fixed inset-y-0 left-0 z-50 w-64 bg-surface border-r border-white/5 transition-transform duration-300 ease-in-out transform",
        isSidebarOpen ? "translate-x-0" : "-translate-x-full",
        "lg:relative lg:translate-x-0"
      )}>
        <div className="h-full flex flex-col">
          <div className="p-6 flex items-center gap-3 border-b border-white/5">
            <Sparkles className="w-6 h-6 text-primary" />
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary">
              Git Sense
            </h1>
          </div>

          <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                disabled={item.id !== 'agent-console' && !analysisData}
                className={clsx(
                  "w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 cursor-pointer",
                  activeTab === item.id
                    ? "bg-primary/10 text-primary border border-primary/20 shadow-[0_0_10px_rgba(99,102,241,0.1)]"
                    : "text-gray-400 hover:bg-white/5 hover:text-white",
                  (item.id !== 'agent-console' && !analysisData) && "opacity-50 cursor-not-allowed"
                )}
              >
                {item.icon}
                <span className="font-medium">{item.label}</span>
              </button>
            ))}
          </nav>

          <div className="p-4 border-t border-white/5">
            <div className="text-xs text-gray-500 text-center">
              v2.0.0 • SaaS Edition
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden relative">
        {/* Mobile Header */}
        <div className="lg:hidden p-4 bg-surface border-b border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <span className="font-bold">Git Sense</span>
          </div>
          <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-2 text-gray-400">
            {isSidebarOpen ? <X /> : <Menu />}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 lg:p-8 scroll-smooth">
          {activeTab === 'agent-console' ? (
            <div className="max-w-6xl mx-auto w-full">
              <div className="mb-8 flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-white mb-1">Agent Autonomy Console</h2>
                  <p className="text-gray-400 text-sm">Autonomous simulation and self-healing engine logs</p>
                </div>
              </div>
              <AgentConsole />
            </div>
          ) : (
            <>
              {/* Repo Input Area - Persistent */}
              <div className={clsx(
                "transition-all duration-500 ease-in-out",
                analysisData ? "mb-6" : "max-w-2xl mx-auto mt-20 text-center"
              )}>
                {!analysisData && !loading && (
                  <>
                    <div className="mb-8 inline-flex p-4 rounded-full bg-primary/10 mb-6">
                      <Sparkles className="w-12 h-12 text-primary" />
                    </div>
                    <h2 className="text-3xl font-bold mb-4">Analyze any GitHub Repository</h2>
                    <p className="text-gray-400 mb-8 text-lg">
                      Get instant insights, structure analysis, bug detection, and more with our advanced AI engine.
                    </p>
                  </>
                )}
                <RepoInput onAnalyze={handleAnalyze} loading={loading} />
              </div>

              {loading && (
                <div className="flex flex-col items-center justify-center py-12 space-y-6">
                  <div className="relative w-24 h-24">
                    <div className="absolute inset-0 border-4 border-primary/20 rounded-full"></div>
                    <div className="absolute inset-0 border-4 border-primary rounded-full border-t-transparent animate-spin"></div>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Sparkles className="w-8 h-8 text-primary animate-pulse" />
                    </div>
                  </div>
                  <div className="text-center space-y-2">
                    <h3 className="text-xl font-semibold text-white">Analyzing Repository...</h3>
                    <p className="text-gray-400">This usually takes about 30-60 seconds.</p>
                  </div>
                </div>
              )}

              {error && (
                <div className="max-w-2xl mx-auto mt-8 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-center">
                  {error}
                </div>
              )}

              {analysisData && (
                <div className="max-w-6xl mx-auto w-full">
                  <div className="mb-8 flex items-center justify-between">
                    <div>
                      <h2 className="text-2xl font-bold text-white mb-1">
                        {navItems.find(i => i.id === activeTab)?.label}
                      </h2>
                      <p className="text-gray-400 text-sm">Analysis Results for Repository</p>
                    </div>
                  </div>
                  <AnalysisResults data={analysisData} activeTab={activeTab} repoUrl={currentRepoUrl} />
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
