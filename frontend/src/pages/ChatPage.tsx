import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import CollegeCard from '../components/CollegeCard';
import VoiceRecorder from '../components/VoiceRecorder';
import { Send, Bot, User, Loader2 } from 'lucide-react';

// const API_URL = "http://localhost:8000/api/v1/decisions/recommend";

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  recommendations?: any[];
};

export default function ChatPage() {
  // const { profile, updateProfile } = useStudent();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init',
      role: 'assistant',
      content: "Hello! I'm your AAST AI Agent. Tell me about what you'd like to study, your budget, or your certificate background, and I'll find the perfect program for you."
    }
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Use a stable session ID for this visitor
  const [sessionId] = useState(() => `sess_${Math.random().toString(36).substring(2, 11)}`);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      const response = await axios.post("http://localhost:8000/api/v1/chat/message", {
        session_id: sessionId,
        message: input
      });

      const { reply, recommendations } = response.data;

      const replyMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: reply,
        recommendations: recommendations || []
      };

      setMessages(prev => [...prev, replyMsg]);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Hmm, I encountered an error connecting to the AI Agent: ${err.message}`
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="h-full w-full bg-slate-50 flex flex-col relative">
      <div className="flex-1 overflow-y-auto w-full p-4 md:p-8">
        <div className="max-w-4xl mx-auto flex flex-col gap-6 pb-20">

          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-4 w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>

              {msg.role === 'assistant' && (
                <div className="w-10 h-10 rounded-full bg-aast-navy text-aast-gold flex items-center justify-center shrink-0 shadow-sm mt-1">
                  <Bot size={20} />
                </div>
              )}

              <div className={`max-w-[85%] flex flex-col gap-3 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`px-5 py-3.5 rounded-2xl shadow-sm leading-relaxed text-[15px] ${msg.role === 'user'
                  ? 'bg-aast-navy text-white rounded-tr-sm'
                  : 'bg-white border text-slate-700 border-slate-200 rounded-tl-sm'
                  }`}>
                  {msg.content}
                </div>

                {/* Inline College Cards */}
                {msg.recommendations && msg.recommendations.length > 0 && (
                  <div className="flex flex-wrap gap-4 mt-2 w-full">
                    {msg.recommendations.map((rec, idx) => (
                      <div key={idx} className="w-[340px] max-w-full">
                        <CollegeCard
                          programName={rec.program_name}
                          collegeName={rec.college_name}
                          matchScore={rec.score}
                          matchType={rec.match_type}
                          confidence={rec.confidence_level}
                          fee={rec.estimated_semester_fee}
                          currency={rec.currency}
                          feeMode={rec.fee_mode}
                          affordability={rec.affordability_label}
                          scoreBreakdown={rec.score_breakdown}
                          warnings={rec.warnings || []}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-10 h-10 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center shrink-0 shadow-sm mt-1">
                  <User size={20} />
                </div>
              )}
            </div>
          ))}

          {isTyping && (
            <div className="flex gap-4 w-full justify-start">
              <div className="w-10 h-10 rounded-full bg-aast-navy text-aast-gold flex items-center justify-center shrink-0 shadow-sm mt-1">
                <Bot size={20} />
              </div>
              <div className="px-5 py-4 bg-white border border-slate-200 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-2">
                <Loader2 className="animate-spin text-aast-navy" size={18} />
                <span className="text-sm text-slate-500 font-medium">Agent is thinking...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="flex-none p-4 md:p-6 bg-white border-t border-slate-200 shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.05)] absolute bottom-0 left-0 right-0">
        <div className="max-w-4xl mx-auto flex gap-3 relative items-center">
          <VoiceRecorder
            onResponseFetched={(reply, recs, transcribedText) => {
              const newMessages: Message[] = [];
              if (transcribedText) {
                newMessages.push({
                   id: Date.now().toString() + "_user",
                   role: 'user',
                   content: transcribedText
                });
              }
              newMessages.push({
                id: Date.now().toString() + "_assistant",
                role: 'assistant',
                content: reply || 'I analyzed your voice input.',
                recommendations: recs
              });
              setMessages(prev => [...prev, ...newMessages]);
              setInput("");
              scrollToBottom();
            }}
            setLoading={setIsTyping}
            setError={(errStr) => {
              if (errStr) {
                setMessages(prev => [...prev, {
                  id: Date.now().toString(),
                  role: 'assistant',
                  content: `Error: ${errStr}`
                }]);
              }
            }}
          />
          <div className="flex-1 relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              className="w-full bg-slate-50 border border-slate-200 rounded-full pl-6 pr-14 py-4 md:py-3.5 text-slate-800 shadow-inner focus:outline-none focus:ring-2 focus:ring-aast-navy/50 focus:border-aast-navy focus:bg-white transition-all"
              placeholder="Type your message to the AI Assistant..."
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isTyping}
              className="absolute right-2 top-0 bottom-0 aspect-square my-1.5 h-[calc(100%-12px)] bg-aast-navy text-white rounded-full flex items-center justify-center hover:bg-aast-blue transition-colors disabled:opacity-50 disabled:hover:bg-aast-navy"
            >
              <Send size={18} className="translate-x-0.5" />
            </button>
          </div>
        </div>
        <p className="text-center text-xs text-slate-400 mt-3 font-medium">
          AAST AI Agent can dynamically filter recommendations based on your chat context.
        </p>
      </div>
    </div>
  );
}
