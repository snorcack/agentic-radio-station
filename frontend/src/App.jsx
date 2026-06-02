import React, { useState, useEffect, useRef } from 'react';
import { Mic2, Radio, ListMusic, Plus, Terminal } from 'lucide-react';

const API_URL = 'http://localhost:8000';

function App() {
  const [state, setState] = useState({
    current_program: null,
    upcoming_programs: [],
    logs: []
  });

  const [newShow, setNewShow] = useState({ theme: '', rj_name: 'Max' });
  const [caller, setCaller] = useState({ prompt: '', topic: '' });
  const logsEndRef = useRef(null);

  useEffect(() => {
    const fetchState = async () => {
      try {
        const res = await fetch(`${API_URL}/state`);
        const data = await res.json();
        setState(data);
      } catch (e) {
        console.error("Error fetching state:", e);
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.logs]);

  const handleAddShow = async (e) => {
    e.preventDefault();
    if (!newShow.theme) return;

    await fetch(`${API_URL}/program`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theme: newShow.theme, rj_name: newShow.rj_name })
    });
    setNewShow({ ...newShow, theme: '' });
  };

  const handleAddCaller = async (e) => {
    e.preventDefault();
    if (!caller.prompt || !caller.topic) return;

    await fetch(`${API_URL}/caller`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ caller_prompt: caller.prompt, caller_topic: caller.topic })
    });
    setCaller({ prompt: '', topic: '' });
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-8">
      <header className="mb-8 flex items-center gap-3">
        <Radio className="w-8 h-8 text-blue-400" />
        <h1 className="text-3xl font-bold">AI Radio Station Dashboard</h1>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left Column */}
        <div className="space-y-6 lg:col-span-2">

          {/* Now Playing */}
          <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-lg">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Mic2 className="text-green-400" /> Now Playing
            </h2>
            {state.current_program ? (
              <div className="bg-gray-900 p-4 rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider text-green-500 bg-green-500/10 px-2 py-1 rounded">
                      Live
                    </span>
                    <h3 className="text-2xl font-bold mt-2">{state.current_program.theme}</h3>
                    <p className="text-gray-400 mt-1">Host: RJ {state.current_program.rj_name}</p>
                  </div>
                  {state.current_program.type === 'caller_injection' && (
                    <div className="text-right">
                      <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-1 rounded border border-purple-500/30">
                        Caller Injection
                      </span>
                      <p className="text-sm text-gray-400 mt-1">ID: {state.current_program.caller_id}</p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-gray-900 p-8 rounded-lg text-center text-gray-500 border border-dashed border-gray-700">
                Silence on the air... Queue up a program!
              </div>
            )}
          </div>

          {/* Queue & Controls */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

            {/* Add Show */}
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
              <h2 className="text-xl font-semibold mb-4">Add Program</h2>
              <form onSubmit={handleAddShow} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Theme</label>
                  <input
                    type="text"
                    value={newShow.theme}
                    onChange={e => setNewShow({...newShow, theme: e.target.value})}
                    placeholder="e.g. AI taking over"
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Host RJ</label>
                  <select
                    value={newShow.rj_name}
                    onChange={e => setNewShow({...newShow, rj_name: e.target.value})}
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 focus:border-blue-500 focus:outline-none"
                  >
                    <option value="Max">RJ Max (High Energy)</option>
                    <option value="Luna">RJ Luna (Cosmic/Slow)</option>
                    <option value="Dave">RJ Dave (Sarcastic Rocker)</option>
                  </select>
                </div>
                <button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium p-2 rounded flex items-center justify-center gap-2 transition-colors">
                  <Plus className="w-4 h-4" /> Queue Program
                </button>
              </form>
            </div>

            {/* Inject Caller */}
            <div className="bg-gray-800 p-6 rounded-xl border border-purple-500/30">
              <h2 className="text-xl font-semibold mb-4 text-purple-400">Inject Random Caller</h2>
              <form onSubmit={handleAddCaller} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Caller Persona</label>
                  <input
                    type="text"
                    value={caller.prompt}
                    onChange={e => setCaller({...caller, prompt: e.target.value})}
                    placeholder="e.g. An angry boomer"
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 focus:border-purple-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Topic to discuss</label>
                  <input
                    type="text"
                    value={caller.topic}
                    onChange={e => setCaller({...caller, topic: e.target.value})}
                    placeholder="e.g. Self driving cars"
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 focus:border-purple-500 focus:outline-none"
                  />
                </div>
                <button type="submit" className="w-full bg-purple-600 hover:bg-purple-500 text-white font-medium p-2 rounded flex items-center justify-center gap-2 transition-colors">
                  <Mic2 className="w-4 h-4" /> Inject Now
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">

          {/* Upcoming Queue */}
          <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 h-64 overflow-hidden flex flex-col">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <ListMusic className="w-5 h-5" /> Up Next
            </h2>
            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              {state.upcoming_programs.length === 0 ? (
                <p className="text-gray-500 italic">Queue is empty</p>
              ) : (
                state.upcoming_programs.map((prog, i) => (
                  <div key={prog.id} className="bg-gray-900 p-3 rounded border border-gray-700 flex justify-between items-center">
                    <div>
                      <p className="font-medium truncate max-w-[200px]">{prog.theme}</p>
                      <p className="text-xs text-gray-400">
                        RJ {prog.rj_name}
                        {prog.type === 'caller_injection' && <span className="text-purple-400 ml-2">(Caller)</span>}
                      </p>
                    </div>
                    <span className="text-xs text-gray-500">#{i+1}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Debug Console */}
          <div className="bg-black p-4 rounded-xl border border-gray-700 h-96 flex flex-col font-mono">
            <h2 className="text-sm font-semibold mb-2 text-gray-400 flex items-center gap-2">
              <Terminal className="w-4 h-4" /> API & Pipeline Logs
            </h2>
            <div className="flex-1 overflow-y-auto text-xs space-y-1">
              {state.logs.map((log, i) => (
                <div key={i} className={`${log.toLowerCase().includes('error') ? 'text-red-400' : 'text-green-400'}`}>
                  <span className="text-gray-600 mr-2">&gt;</span>{log}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default App;
