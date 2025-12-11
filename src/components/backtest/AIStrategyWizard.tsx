'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Brain, Send, Sparkles, X, Check, ChevronRight, Square, Coins, Loader2 } from 'lucide-react';
import { useAIStrategy, Message } from '@/hooks/use-ai-strategy';
import { useTranslations } from 'next-intl';

interface AIStrategyWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onApply: (strategy: any) => Promise<void>; 
  hiddenContext?: string;
  diagnosisContext?: { report: string, summary: string };
  userIntent?: string; 
  history?: Message[];
  onHistoryChange?: (msgs: Message[]) => void;
  onUserQuery?: (query: string) => void;
  credits?: number | null;
  onCreditsUpdate?: (newCredits: number) => void;
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
  onUserQuery,
  credits,
  onCreditsUpdate
}: AIStrategyWizardProps) {
  const t = useTranslations('Backtest');
  const { messages, isLoading, sendMessage, setMessages, stop } = useAIStrategy({
    initialHistory: history,
    onHistoryChange: onHistoryChange
  });

  const [input, setInput] = useState('');
  // credits is now a prop
  const [isApplying, setIsApplying] = useState(false); 
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasInitialized = useRef(false);
  const lastSentContextRef = useRef<string>('');

  // No internal fetch for credits anymore

  // Initialize Logic
  useEffect(() => {
    if (isOpen) {
      if (messages.length === 0 && !hasInitialized.current) {
        hasInitialized.current = true;
        
        if (diagnosisContext) {
          setMessages([{
            role: 'assistant',
            content: `🤖 **策略诊断就绪**\n\n${diagnosisContext.summary}\n\n请告诉我您希望如何优化？\n例如：\n- "收益太低，想激进一点"\n- "回撤太大，想稳健一点"\n- "交易太少，想捕捉更多机会"`
          }]);
        } else if (hiddenContext) {
          sendMessage(
            "策略表现不佳，请根据回测报告进行诊断和优化。", 
            hiddenContext, 
            userIntent
          );
        } else {
          setMessages([{ 
            role: 'assistant', 
            content: "你好！我是你的 AI 策略顾问。请描述你的交易想法（例如：做超跌反弹，或者均线趋势），我会帮你设计并生成可执行的策略配置。" 
          }]);
        }
      }
    } else {
      // Always reset initialization state when closed.
      // The protection against double-init is handled by (messages.length === 0) check above.
      hasInitialized.current = false;
    }
  }, [isOpen, diagnosisContext, hiddenContext, userIntent, messages.length, sendMessage, setMessages]); 

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (input.trim()) {
      if (credits !== null && credits < 1) {
          alert('积分不足，请充值'); 
          return;
      }

      const userMsgCount = messages.filter(m => m.role === 'user').length;
      if (userMsgCount === 0 && onUserQuery) {
          onUserQuery(input);
      }

      let contextToSend: string | undefined = undefined;

      if (diagnosisContext) {
        const configStr = (diagnosisContext as any).strategy_config || '';
        const reportStr = diagnosisContext.report || '';
        const fullContext = `[CURRENT STRATEGY CONFIG]\n${configStr}\n\n[LATEST BACKTEST REPORT]\n${reportStr}`;
        if (fullContext !== lastSentContextRef.current) {
            contextToSend = fullContext;
            lastSentContextRef.current = fullContext;
        }
      } else if (hiddenContext && userMsgCount === 0) {
        contextToSend = hiddenContext;
      }
      
      sendMessage(input, contextToSend, userIntent);
      setInput('');
      
      if (credits !== null && onCreditsUpdate) onCreditsUpdate((credits || 0) - 1);
    }
  };

  const handleApply = async () => {
    const lastStratMsg = [...messages].reverse().find(m => m.strategyJson);
    if (!lastStratMsg) return;

    setIsApplying(true);
    try {
        await onApply(lastStratMsg.strategyJson);
        onClose();
    } catch (error) {
        console.error('Apply failed', error);
    } finally {
        setIsApplying(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4">
      <div className="w-full max-w-6xl h-[90vh] bg-white dark:bg-zinc-950 rounded-2xl shadow-2xl overflow-hidden border border-zinc-200 dark:border-zinc-800 flex flex-col relative">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 flex justify-between items-center bg-zinc-50 dark:bg-zinc-900/50">
          <div className="flex items-center gap-2">
            <Sparkles className="size-5 text-purple-500" />
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              {diagnosisContext ? t('wizard.titleDiagnose') : t('wizard.titleNew')}
            </h2>
          </div>
          <div className="flex items-center gap-4">
              {/* Credits Display */}
              <div className="flex items-center gap-1.5 px-3 py-1 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-500 rounded-full text-xs font-bold border border-amber-200 dark:border-amber-800">
                  <Coins className="size-3.5" />
                  <span>{credits !== null ? credits : '-'} {t('credits')}</span>
              </div>
              <button onClick={onClose} className="text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300">
                <X className="size-5" />
              </button>
          </div>
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

                  {/* Reasoning Collapsible */}
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
                  className="w-full pl-4 pr-32 py-3.5 bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-700 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all disabled:opacity-50"
                  placeholder={credits !== null && credits < 1 ? "Insufficient credits" : "Describe your strategy..."}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  disabled={isLoading || (credits !== null && credits < 1)}
                />
                
                {isLoading ? (
                    <button
                        onClick={stop}
                        className="absolute right-2 px-3 py-1.5 bg-red-500/10 text-red-600 hover:bg-red-500/20 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors border border-red-500/20"
                    >
                        <Square className="size-3 fill-current" />
                        Stop
                    </button>
                ) : (
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || (credits !== null && credits < 1)}
                        className="absolute right-2 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors text-xs font-medium flex items-center gap-1.5"
                    >
                        <span>Send</span>
                        {/* Only show cost if needed, user said 'hardcoded cost is 1' but Apply is 0 */}
                        <span className="opacity-70 font-normal border-l border-white/20 pl-1.5 ml-0.5">-1 {t('credits')}</span>
                        <Send className="size-3" />
                    </button>
                )}
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
                  onClick={handleApply}
                  disabled={isApplying}
                  className="w-full py-3 bg-green-600 hover:bg-green-700 disabled:bg-green-600/50 text-white rounded-xl font-medium shadow-lg shadow-green-600/20 transition-all flex items-center justify-center gap-2"
                >
                  {isApplying ? (
                    <>
                        <Loader2 className="size-4 animate-spin" />
                        Creating Session...
                    </>
                  ) : (
                    <>
                        <Check className="size-4" />
                        {t('wizard.apply')}
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
