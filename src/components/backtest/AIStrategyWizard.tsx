'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Brain, Send, Sparkles, X, Check, ChevronRight } from 'lucide-react';
import { useAIStrategy, Message } from '@/hooks/use-ai-strategy';

interface AIStrategyWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onApply: (strategy: any) => void;
  hiddenContext?: string; // Replaced by diagnosisContext in new flow, but kept for compatibility
  diagnosisContext?: { report: string, summary: string }; // New structured context
  userIntent?: string; 
  history?: Message[];
  onHistoryChange?: (msgs: Message[]) => void;
  onUserQuery?: (query: string) => void;
}

export default function AIStrategyWizard({
  isOpen, 
  onClose, 
  onApply, 
  hiddenContext, 
  diagnosisContext,
  userIntent,
  history, 
  onHistoryChange,
  onUserQuery
}: AIStrategyWizardProps) {
  const { messages, isLoading, sendMessage, setMessages } = useAIStrategy({
    initialHistory: history,
    onHistoryChange: onHistoryChange
  });

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasInitialized = useRef(false);
  const lastSentContextRef = useRef<string>('');

  // Initialize Logic
  useEffect(() => {
    if (isOpen) {
      if (messages.length === 0 && !hasInitialized.current) {
        hasInitialized.current = true;
        
        if (diagnosisContext) {
          // DIAGNOSIS MODE: Interactive Start
          setMessages([{
            role: 'assistant',
            content: `🤖 **策略诊断就绪**\n\n${diagnosisContext.summary}\n\n请告诉我您希望如何优化？\n例如：\n- "收益太低，想激进一点"\n- "回撤太大，想稳健一点"\n- "交易太少，想捕捉更多机会"`
          }]);
        } else if (hiddenContext) {
          // LEGACY MODE: Auto-start (Fallback)
          sendMessage(
            "策略表现不佳，请根据回测报告进行诊断和优化。", 
            hiddenContext, 
            userIntent
          );
        } else {
          // CREATION MODE: Welcome message
          setMessages([{ 
            role: 'assistant', 
            content: "你好！我是你的 AI 策略顾问。请描述你的交易想法（例如：做超跌反弹，或者均线趋势），我会帮你设计并生成可执行的策略配置。" 
          }]);
        }
      }
    } else {
      hasInitialized.current = false;
    }
  }, [isOpen, diagnosisContext, hiddenContext, userIntent, messages.length, sendMessage, setMessages]); 

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (input.trim()) {
      // Capture intent if first user msg
      const userMsgCount = messages.filter(m => m.role === 'user').length;
      if (userMsgCount === 0 && onUserQuery) {
          onUserQuery(input);
      }

      let contextToSend: string | undefined = undefined;

      // Construct Diagnosis Context if available
      if (diagnosisContext) {
        // Safe access to strategy_config (it might be injected as string or object, handle both if needed, but assuming string based on previous page.tsx change)
        // In page.tsx: strategy_config: JSON.stringify(strategyConfig, null, 2)
        const configStr = (diagnosisContext as any).strategy_config || '';
        const reportStr = diagnosisContext.report || '';
        
        const fullContext = `[CURRENT STRATEGY CONFIG]\n${configStr}\n\n[LATEST BACKTEST REPORT]\n${reportStr}`;
        
        // Check if we need to send this context (if it changed or hasn't been sent)
        if (fullContext !== lastSentContextRef.current) {
            contextToSend = fullContext;
            lastSentContextRef.current = fullContext;
        }
      } else if (hiddenContext && userMsgCount === 0) {
        // Fallback for legacy hiddenContext (only on first message)
        contextToSend = hiddenContext;
      }
      
      sendMessage(input, contextToSend, userIntent);
      
      setInput('');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md">
      <div className="w-full max-w-6xl h-[85vh] bg-white dark:bg-zinc-950 rounded-2xl shadow-2xl overflow-hidden border border-zinc-200 dark:border-zinc-800 flex flex-col">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 flex justify-between items-center bg-zinc-50 dark:bg-zinc-900/50">
          <div className="flex items-center gap-2">
            <Sparkles className="size-5 text-purple-500" />
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              DeepSeek R1 Strategy Builder
            </h2>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300">
            <X className="size-5" />
          </button>
        </div>

        {/* Main Content Area: Split View */}
        <div className="flex-1 flex overflow-hidden">
          
          {/* Chat Area */}
          <div className="flex-1 flex flex-col border-r border-zinc-200 dark:border-zinc-800">
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {messages.map((m, idx) => (
                <div key={idx} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                  
                  {/* Message Bubble */}
                  <div className={`max-w-[90%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed shadow-sm ${ 
                    m.role === 'user' 
                      ? 'bg-blue-600 text-white rounded-br-none' 
                      : 'bg-zinc-100 dark:bg-zinc-900 text-zinc-800 dark:text-zinc-200 rounded-bl-none border border-zinc-200 dark:border-zinc-800'
                  }`}> 
                    <div className="whitespace-pre-wrap">{m.content}</div>
                  </div>

                  {/* Reasoning Collapsible (Only for assistant) */}
                  {m.role === 'assistant' && m.reasoning && (
                    <div className="mt-2 max-w-[90%]">
                      <details className="group">
                        <summary className="flex items-center gap-2 text-xs font-medium text-zinc-400 cursor-pointer hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors list-none select-none">
                          <div className="flex items-center gap-1 bg-zinc-50 dark:bg-zinc-900/50 px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800">
                            <Brain className="size-3" />
                            <span>Thinking Process</span>
                            <ChevronRight className="size-3 group-open:rotate-90 transition-transform" />
                          </div>
                        </summary>
                        <div className="mt-2 p-3 bg-zinc-50/50 dark:bg-zinc-900/30 rounded-lg border-l-2 border-purple-500 text-xs font-mono text-zinc-500 dark:text-zinc-400 overflow-x-auto whitespace-pre-wrap">
                          {m.reasoning}
                        </div>
                      </details>
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
              <div className="relative flex items-center">
                <input
                  type="text"
                  className="w-full pl-4 pr-12 py-3.5 bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-700 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all"
                  placeholder="Describe your strategy (e.g., 'Buy dip in super trend...'))"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  disabled={isLoading}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                  className="absolute right-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors"
                >
                  {isLoading ? (
                    <div className="size-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <Send className="size-4" />
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Preview Panel (Shows latest generated JSON) */}
          {messages.some(m => m.strategyJson) && (
            <div className="w-1/3 bg-zinc-50 dark:bg-zinc-950/50 border-l border-zinc-200 dark:border-zinc-800 flex flex-col animate-in slide-in-from-right-10 duration-300">
              <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 font-medium text-sm text-zinc-500 uppercase tracking-wider flex justify-between items-center">
                <span>Configuration Preview</span>
                <span className="text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 px-2 py-0.5 rounded-full border border-green-200 dark:border-green-800">
                  Ready to Apply
                </span>
              </div>
              <div className="flex-1 overflow-y-auto p-4">
                {/* Show the LATEST generated strategy */}
                {(() => {
                  const lastStratMsg = [...messages].reverse().find(m => m.strategyJson);
                  if (!lastStratMsg) return null;
                  return (
                    <pre className="text-xs font-mono text-zinc-600 dark:text-zinc-400 whitespace-pre-wrap">
                      {JSON.stringify(lastStratMsg.strategyJson, null, 2)}
                    </pre>
                  );
                })()}
              </div>
              <div className="p-4 border-t border-zinc-200 dark:border-zinc-800">
                <button
                  onClick={() => {
                    const lastStratMsg = [...messages].reverse().find(m => m.strategyJson);
                    if (lastStratMsg) onApply(lastStratMsg.strategyJson);
                    onClose();
                  }}
                  className="w-full py-3 bg-green-600 hover:bg-green-700 text-white rounded-xl font-medium shadow-lg shadow-green-600/20 transition-all flex items-center justify-center gap-2"
                >
                  <Check className="size-4" />
                  Apply Strategy
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
