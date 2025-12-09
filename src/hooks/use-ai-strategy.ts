import { useState, useCallback, useRef, useEffect } from 'react';

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  reasoning?: string;
  strategyJson?: any;
}

interface UseAIStrategyProps {
  initialHistory?: Message[];
  onHistoryChange?: (msgs: Message[]) => void;
}

export function useAIStrategy({ initialHistory, onHistoryChange }: UseAIStrategyProps = {}) {
  // Internal state, seeded by props if available
  const [messages, setMessagesState] = useState<Message[]>(initialHistory || []);
  const [isLoading, setIsLoading] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Sync with parent if provided
  const setMessages = useCallback((newMsgs: Message[] | ((prev: Message[]) => Message[])) => {
    setMessagesState(prev => {
      const resolved = typeof newMsgs === 'function' ? newMsgs(prev) : newMsgs;
      if (onHistoryChange) {
        // Defer to avoid render-cycle issues
        setTimeout(() => onHistoryChange(resolved), 0);
      }
      return resolved;
    });
  }, [onHistoryChange]);

  // Update local state if parent prop changes remotely
  useEffect(() => {
    if (initialHistory && initialHistory !== messages) {
        // Only sync if we detect a reset or significant external change
        if (initialHistory.length === 0 && messages.length > 0) {
             setMessagesState([]);
        } else if (initialHistory.length > 0 && messages.length === 0) {
             setMessagesState(initialHistory);
        }
    }
  }, [initialHistory]); 

  const extractStrategyJson = (text: string): any | null => {
    try {
      // Try standard markdown code block
      const jsonBlockMatch = text.match(/```json\n([\s\S]*?)\n```/);
      if (jsonBlockMatch && jsonBlockMatch[1]) {
        return JSON.parse(jsonBlockMatch[1]);
      }
    } catch (e) {
      // Ignore parse errors during streaming
    }
    return null;
  };

  const sendMessage = useCallback(async (text: string, hiddenContext?: string, userIntent?: string) => {
    if (!text.trim() || isLoading) return;

    setIsLoading(true);
    abortControllerRef.current = new AbortController();

    // 1. Optimistic Update
    const userMsg: Message = { role: 'user', content: text };
    const assistantPlaceholder: Message = { role: 'assistant', content: '', reasoning: '' };
    
    setMessages(prev => [...prev, userMsg, assistantPlaceholder]);

    try {
      // 2. Prepare API Payload with Context Pruning
      // Keep only last 6 messages to save tokens
      const prunedHistory = messages.slice(-6); 
      const currentHistory = [...prunedHistory, userMsg];
      
      const apiMessages = currentHistory.map(({ role, content }) => ({ role, content }));

      // Inject hidden context and user intent
      let systemContent = '';
      if (hiddenContext) {
          systemContent += `[HIDDEN CONTEXT]\n${hiddenContext}\n\n`;
      }
      if (userIntent) {
          systemContent += `[USER ORIGINAL INTENT]\n${userIntent}\n\nIMPORTANT: The user's original goal was "${userIntent}". Ensure any optimization or diagnosis aligns with this goal. Do not make the strategy overly conservative if the user asked for high risk/reward.`;
      }

      if (systemContent) {
        // Insert system message as the 'context wrapper'
        // For 'deepseek-reasoner', system prompt is best placed at start or just before task.
        // We put it before the last user message for freshness.
        apiMessages.splice(Math.max(0, apiMessages.length - 1), 0, {
          role: 'system',
          content: systemContent.trim()
        });
      }

      const res = await fetch('/api/strategy/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages }),
        signal: abortControllerRef.current.signal,
      });

      if (!res.body || !res.ok) throw new Error(`API Error: ${res.statusText}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            
            setMessages(prev => {
              const newMsgs = [...prev];
              const lastIndex = newMsgs.length - 1;
              const lastMsg = { ...newMsgs[lastIndex] };

              if (data.type === 'error') {
                 // Handle explicit error from backend
                 const errText = `\n\n❌ **Error:** ${data.message}`;
                 lastMsg.content = (lastMsg.content || '') + errText;
              } else if (data.type === 'reasoning') {
                lastMsg.reasoning = (lastMsg.reasoning || '') + (data.content || '');
              } else if (data.type === 'content') {
                lastMsg.content = (lastMsg.content || '') + (data.content || '');
                lastMsg.strategyJson = extractStrategyJson(lastMsg.content);
              }
              
              newMsgs[lastIndex] = lastMsg;
              return newMsgs;
            });
          } catch (e) { }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        console.error(e);
        setMessages(prev => {
            const newMsgs = [...prev];
            const lastIdx = newMsgs.length - 1;
            if (lastIdx >= 0) {
                const errText = `\n\n[System Error: ${e.message || 'Unknown Network Error'}]`;
                const m = newMsgs[lastIdx];
                newMsgs[lastIdx] = { ...m, content: m.content + errText };
            }
            return newMsgs;
        });
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [messages, isLoading, setMessages]);

  const stop = useCallback(() => {
    if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
        setIsLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
      setMessages([]);
  }, [setMessages]);

  return {
    messages,
    isLoading,
    sendMessage,
    stop,
    clear,
    setMessages
  };
}
