import React, { useEffect, useState, useRef } from 'react';
import { Activity, Brain, HandIcon, Settings, Zap } from 'lucide-react';

const App = () => {
  const [telemetry, setTelemetry] = useState(null);
  const [mode, setMode] = useState('gestures');
  const ws = useRef(null);

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:8000/ws');
    ws.current.onmessage = (event) => {
      setTelemetry(JSON.parse(event.data));
    };
    return () => ws.current.close();
  }, []);

  const changeMode = async (newMode) => {
    await fetch(`http://localhost:8000/set_mode?mode=${newMode}`, { method: 'POST' });
    setMode(newMode);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white p-8 font-sans">
      <header className="flex justify-between items-center mb-12">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
          Mão Robótica Pro
        </h1>
        <div className="flex gap-4 bg-[#1a1a1a] p-1 rounded-xl border border-white/10">
          <button 
            onClick={() => changeMode('gestures')}
            className={`flex items-center gap-2 px-6 py-2 rounded-lg transition-all ${mode === 'gestures' ? 'bg-blue-600 shadow-lg shadow-blue-900/40' : 'hover:bg-white/5'}`}
          >
            <HandIcon size={18} /> Gestos
          </button>
          <button 
            onClick={() => changeMode('eeg')}
            className={`flex items-center gap-2 px-6 py-2 rounded-lg transition-all ${mode === 'eeg' ? 'bg-purple-600 shadow-lg shadow-purple-900/40' : 'hover:bg-white/5'}`}
          >
            <Brain size={18} /> EEG
          </button>
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Status Card */}
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-[#111] border border-white/5 rounded-3xl p-8 relative overflow-hidden backdrop-blur-xl">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-50" />
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-3">
              <Activity className="text-blue-500" /> Monitoramento em Tempo Real
            </h2>
            
            {mode === 'gestures' ? (
              <div className="grid grid-cols-5 gap-4">
                {telemetry && Object.entries(telemetry.fingers).map(([finger, value]) => (
                  <div key={finger} className="flex flex-col items-center gap-4">
                    <div className="h-48 w-12 bg-[#1a1a1a] rounded-full relative overflow-hidden border border-white/5">
                      <div 
                        className="absolute bottom-0 w-full bg-blue-500 transition-all duration-300 rounded-full"
                        style={{ height: `${(value / 180) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs uppercase tracking-widest text-gray-500">{finger}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-12 py-8">
                <div className="flex justify-around items-center">
                  <div className="text-center">
                    <div className="text-6xl font-black text-purple-500 mb-2">
                       {telemetry?.eeg.attention || 0}%
                    </div>
                    <div className="text-sm text-gray-400 uppercase tracking-widest">Atenção</div>
                  </div>
                  <div className="h-24 w-px bg-white/10" />
                  <div className="text-center">
                    <div className="text-6xl font-black text-cyan-500 mb-2">
                      {telemetry?.eeg.meditation || 0}%
                    </div>
                    <div className="text-sm text-gray-400 uppercase tracking-widest">Meditação</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar Diagnostics */}
        <div className="space-y-6">
          <div className="bg-[#111] border border-white/5 rounded-3xl p-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-4 flex items-center gap-2">
              <Zap size={14} className="text-yellow-500" /> Diagnóstico do Sistema
            </h3>
            <div className="space-y-4">
              <StatusItem label="Arduino Online" active={true} />
              <StatusItem label="Webcam" active={telemetry?.hand_detected} />
              <StatusItem label="Sensor EEG" active={telemetry?.eeg.signal < 100} />
              <StatusItem label="Bateria EEG" val={`${telemetry?.eeg.battery || 0}%`} />
            </div>
          </div>
          
          <button className="w-full py-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-2xl flex items-center justify-center gap-3 transition-all group">
            <Settings className="group-hover:rotate-90 transition-transform" /> Configurações Avançadas
          </button>
        </div>
      </main>
    </div>
  );
};

const StatusItem = ({ label, active, val }) => (
  <div className="flex justify-between items-center text-sm">
    <span className="text-gray-400">{label}</span>
    {val ? (
      <span className="font-mono text-blue-400">{val}</span>
    ) : (
      <div className={`w-2 h-2 rounded-full ${active ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500'}`} />
    )}
  </div>
);

export default App;
