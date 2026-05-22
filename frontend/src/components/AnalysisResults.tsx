import React from 'react';
import { motion } from 'framer-motion';
import { Lightbulb, Bug, FileCode, GitCommit, Loader2, UploadCloud } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import clsx from 'clsx';

interface Issue {
    file: string;
    line: number;
    description: string;
    severity: string;
}

interface Suggestion {
    file: string;
    description: string;
    suggestion: string;
}

interface FileSummary {
    file: string;
    summary: string;
}

interface Commit {
    hash: string;
    message: string;
    author: string;
    date: string;
}

interface AnalysisData {
    bugs: Issue[] | null;
    suggestions: Suggestion[] | null;
    readme: string | null;
    structure: string | null;
    file_summaries: FileSummary[] | null;
    commits: Commit[] | null;
}

interface AnalysisResultsProps {
    data: AnalysisData;
    activeTab: string;
    repoUrl: string;
}

// Helper for loading state
const LoadingSection = () => (
    <div className="flex flex-col items-center justify-center p-12 text-gray-400">
        <Loader2 className="w-8 h-8 animate-spin mb-4 text-primary" />
        <p>Analyzing...</p>
    </div>
);

export const AnalysisResults: React.FC<AnalysisResultsProps> = ({ data, activeTab, repoUrl }) => {
    const [pushing, setPushing] = React.useState(false);
    const [pushStatus, setPushStatus] = React.useState<{ success: boolean; message: string } | null>(null);

    const handlePush = async () => {
        if (!data.readme || !repoUrl) return;
        setPushing(true);
        setPushStatus(null);
        try {
            const response = await fetch('http://localhost:8000/push', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    repo_url: repoUrl,
                    file_path: 'README.md',
                    content: data.readme,
                    commit_message: 'Update README.md via Git Sense',
                    branch: 'main'
                }),
            });
            const result = await response.json();
            if (response.ok) {
                setPushStatus({ success: true, message: 'Successfully pushed to Git!' });
            } else {
                setPushStatus({ success: false, message: result.detail || 'Failed to push.' });
            }
        } catch (e) {
            setPushStatus({ success: false, message: 'Error connecting to server.' });
        } finally {
            setPushing(false);
        }
    };

    const renderContent = () => {
        switch (activeTab) {
            case 'overview':
                return (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-surface p-6 rounded-xl border border-white/5">
                            <h3 className="text-lg font-semibold mb-4 text-white">Quick Stats</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-4 bg-black/20 rounded-lg">
                                    <div className="text-2xl font-bold text-primary">
                                        {data.bugs ? data.bugs.length : <Loader2 className="w-4 h-4 animate-spin inline" />}
                                    </div>
                                    <div className="text-sm text-gray-400">Bugs Found</div>
                                </div>
                                <div className="p-4 bg-black/20 rounded-lg">
                                    <div className="text-2xl font-bold text-secondary">
                                        {data.suggestions ? data.suggestions.length : <Loader2 className="w-4 h-4 animate-spin inline" />}
                                    </div>
                                    <div className="text-sm text-gray-400">Suggestions</div>
                                </div>
                                <div className="p-4 bg-black/20 rounded-lg">
                                    <div className="text-2xl font-bold text-accent">
                                        {data.commits ? data.commits.length : <Loader2 className="w-4 h-4 animate-spin inline" />}
                                    </div>
                                    <div className="text-sm text-gray-400">Recent Commits</div>
                                </div>
                                <div className="p-4 bg-black/20 rounded-lg">
                                    <div className="text-2xl font-bold text-green-400">
                                        {data.file_summaries ? data.file_summaries.length : <Loader2 className="w-4 h-4 animate-spin inline" />}
                                    </div>
                                    <div className="text-sm text-gray-400">Files Analyzed</div>
                                </div>
                            </div>
                        </div>
                        <div className="bg-surface p-6 rounded-xl border border-white/5">
                            <h3 className="text-lg font-semibold mb-4 text-white">Latest Commit</h3>
                            {data.commits ? (
                                data.commits.length > 0 && (
                                    <div className="space-y-4">
                                        <div>
                                            <div className="text-sm text-gray-400 mb-1">Message</div>
                                            <div className="text-white font-medium">{data.commits[0].message}</div>
                                        </div>
                                        <div className="flex items-center justify-between text-sm">
                                            <span className="text-primary">{data.commits[0].author}</span>
                                            <span className="text-gray-500">{new Date(data.commits[0].date).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                )
                            ) : <LoadingSection />}
                        </div>
                    </div>
                );

            case 'structure':
                return (
                    <div className="bg-surface p-8 rounded-xl border border-white/5">
                        {data.structure ? (
                            <div className="prose prose-invert max-w-none prose-headings:text-primary prose-a:text-accent">
                                <ReactMarkdown>{data.structure}</ReactMarkdown>
                            </div>
                        ) : <LoadingSection />}
                    </div>
                );

            case 'files':
                return (
                    <div className="space-y-4">
                        {data.file_summaries ? (
                            data.file_summaries.length === 0 ? (
                                <div className="text-center py-12 bg-surface rounded-xl border border-white/5">
                                    <FileCode className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                                    <h3 className="text-lg font-medium text-white">No Files Summarized</h3>
                                    <p className="text-gray-400">Could not generate summaries for this repository.</p>
                                </div>
                            ) : (
                                <div className="grid gap-4 sm:grid-cols-2">
                                    {data.file_summaries.map((file, idx) => (
                                        <div key={idx} className="bg-surface p-6 rounded-xl border border-white/5 hover:border-primary/50 transition-colors">
                                            <div className="font-mono text-sm text-primary mb-3 truncate" title={file.file}>{file.file}</div>
                                            <p className="text-gray-400 text-sm leading-relaxed">{file.summary}</p>
                                        </div>
                                    ))}
                                </div>
                            )
                        ) : <LoadingSection />}
                    </div>
                );

            case 'bugs':
                return (
                    <div className="space-y-4">
                        {data.bugs ? (
                            data.bugs.length === 0 ? (
                                <div className="text-center py-12 bg-surface rounded-xl border border-white/5">
                                    <Bug className="w-12 h-12 text-green-500 mx-auto mb-4" />
                                    <h3 className="text-lg font-medium text-white">No Bugs Found</h3>
                                    <p className="text-gray-400">Great job! Your code looks clean.</p>
                                </div>
                            ) : (
                                data.bugs.map((bug, idx) => (
                                    <div key={idx} className="bg-surface p-6 rounded-xl border border-white/5 hover:border-red-500/30 transition-colors group">
                                        <div className="flex items-start justify-between mb-3">
                                            <div className="flex items-center gap-3">
                                                <div className="p-2 bg-red-500/10 rounded-lg text-red-500 group-hover:bg-red-500/20 transition-colors">
                                                    <Bug size={18} />
                                                </div>
                                                <span className="font-mono text-sm text-white font-medium">{bug.file}:{bug.line}</span>
                                            </div>
                                            <span className={clsx(
                                                "px-3 py-1 rounded-full text-xs font-medium border",
                                                bug.severity.toLowerCase() === 'high' ? "bg-red-500/10 text-red-400 border-red-500/20" :
                                                    bug.severity.toLowerCase() === 'medium' ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/20" :
                                                        "bg-blue-500/10 text-blue-400 border-blue-500/20"
                                            )}>
                                                {bug.severity}
                                            </span>
                                        </div>
                                        <p className="text-gray-300 leading-relaxed pl-11">{bug.description}</p>
                                    </div>
                                ))
                            )
                        ) : <LoadingSection />}
                    </div>
                );

            case 'suggestions':
                return (
                    <div className="space-y-6">
                        {data.suggestions ? (
                            data.suggestions.length === 0 ? (
                                <div className="text-center py-12 bg-surface rounded-xl border border-white/5">
                                    <Lightbulb className="w-12 h-12 text-yellow-500/50 mx-auto mb-4" />
                                    <h3 className="text-lg font-medium text-white">No Suggestions Found</h3>
                                    <p className="text-gray-400">The code looks good! No major refactoring needed.</p>
                                </div>
                            ) : (
                                data.suggestions.map((item, idx) => (
                                    <div key={idx} className="bg-surface p-6 rounded-xl border border-white/5">
                                        <div className="flex items-center gap-3 mb-4">
                                            <div className="p-2 bg-accent/10 rounded-lg text-accent">
                                                <Lightbulb size={18} />
                                            </div>
                                            <div className="font-mono text-sm text-white font-medium">{item.file}</div>
                                        </div>
                                        <p className="text-gray-300 mb-4 pl-11">{item.description}</p>
                                        <div className="pl-11">
                                            <div className="bg-black/30 p-4 rounded-lg border border-white/5 font-mono text-sm text-green-400 overflow-x-auto">
                                                {item.suggestion}
                                            </div>
                                        </div>
                                    </div>
                                ))
                            )
                        ) : <LoadingSection />}
                    </div>
                );

            case 'commits':
                return (
                    <div className="bg-surface rounded-xl border border-white/5 overflow-hidden">
                        {data.commits ? (
                            <div className="divide-y divide-white/5">
                                {data.commits.map((commit, idx) => (
                                    <div key={idx} className="p-6 hover:bg-white/5 transition-colors flex items-start gap-4">
                                        <div className="mt-1">
                                            <div className="w-2 h-2 rounded-full bg-primary ring-4 ring-primary/10"></div>
                                        </div>
                                        <div className="flex-1">
                                            <h4 className="text-white font-medium mb-1">{commit.message}</h4>
                                            <div className="flex items-center gap-3 text-sm text-gray-400">
                                                <span className="flex items-center gap-1">
                                                    <GitCommit size={14} />
                                                    <span className="font-mono">{commit.hash}</span>
                                                </span>
                                                <span>•</span>
                                                <span>{commit.author}</span>
                                                <span>•</span>
                                                <span>{new Date(commit.date).toLocaleDateString()}</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : <LoadingSection />}
                    </div>
                );

            case 'readme':
                return (
                    <div className="bg-surface p-8 rounded-xl border border-white/5 relative">
                        {data.readme ? (
                            <>
                                <div className="flex justify-between items-start mb-6 pb-6 border-b border-white/5">
                                    <h3 className="text-xl font-bold text-white">Generated README</h3>
                                    <div className="flex flex-col items-end gap-2">
                                        <button
                                            onClick={handlePush}
                                            disabled={pushing}
                                            className={clsx(
                                                "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all shadow-lg shadow-primary/20",
                                                pushing
                                                    ? "bg-primary/20 text-primary cursor-wait"
                                                    : "bg-gradient-to-r from-primary to-indigo-600 text-white hover:opacity-90 active:scale-95"
                                            )}
                                        >
                                            {pushing ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
                                            {pushing ? 'Pushing...' : 'Push to Git'}
                                        </button>
                                        {pushStatus && (
                                            <div className={clsx("text-sm font-medium animate-in fade-in slide-in-from-top-1", pushStatus.success ? "text-green-400" : "text-red-400")}>
                                                {pushStatus.message}
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <div className="prose prose-invert max-w-none prose-headings:text-primary prose-a:text-accent">
                                    <ReactMarkdown>{data.readme}</ReactMarkdown>
                                </div>
                            </>
                        ) : <LoadingSection />}
                    </div>
                );

            default:
                return null;
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
        >
            {renderContent()}
        </motion.div>
    );
};
