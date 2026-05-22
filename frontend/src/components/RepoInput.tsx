import React, { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

interface RepoInputProps {
    onAnalyze: (url: string) => void;
    loading: boolean;
}

export const RepoInput: React.FC<RepoInputProps> = ({ onAnalyze, loading }) => {
    const [url, setUrl] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (url.trim()) {
            onAnalyze(url);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-2xl mx-auto"
        >
            <form onSubmit={handleSubmit} className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-primary to-secondary rounded-lg blur opacity-25 group-hover:opacity-75 transition duration-1000 group-hover:duration-200"></div>
                <div className="relative flex items-center bg-surface rounded-lg p-2 ring-1 ring-white/10 focus-within:ring-2 focus-within:ring-primary transition-all shadow-xl">
                    <Search className="w-6 h-6 text-gray-400 ml-3" />
                    <input
                        type="text"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="https://github.com/username/repo"
                        className="w-full bg-transparent border-none focus:ring-0 text-white placeholder-gray-500 px-4 py-3 text-lg"
                        disabled={loading}
                    />
                    <button
                        type="submit"
                        disabled={loading || !url}
                        className="bg-primary hover:bg-cyan-400 text-dark px-6 py-2 rounded-md font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Analyze'}
                    </button>
                </div>
            </form>
        </motion.div>
    );
};
