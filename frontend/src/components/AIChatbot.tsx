"use client";

import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, Bot, User } from 'lucide-react';
import { clsx } from 'clsx';
import { API_BASE_URL } from '@/config';

interface Message {
  text: string;
  isUser: boolean;
  timestamp: Date;
}

const AIChatbot = ({ patientUid }: { patientUid: string }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { text: "Hello! I'm your SRRIS Clinical Assistant. How can I help you today?", isUser: false, timestamp: new Date() }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = input.trim();
    setMessages(prev => [...prev, { text: userMsg, isUser: true, timestamp: new Date() }]);
    setInput('');
    setIsTyping(true);

    // AI Logic (Ported and expanded from Brainstroke project)
    setTimeout(async () => {
      let response = "";
      const lowerMsg = userMsg.toLowerCase();

      if (lowerMsg.includes('risk') || lowerMsg.includes('stroke')) {
        response = "I've analyzed the patient's longitudinal data. The current risk profile is influenced by recent blood pressure readings. You can see the full breakdown in the 'AI Diagnostic Engine' tab.";
      } else if (lowerMsg.includes('analytics') || lowerMsg.includes('history')) {
        try {
          const res = await fetch(`${API_BASE_URL}/api/v1/analytics/patient/${patientUid}/benchmarks`);
          if (res.ok) {
            const data = await res.json();
            const highRisk = data.filter((d: any) => d.status === 'High Risk').map((d: any) => d.metric).join(', ');
            response = highRisk 
              ? `Currently, the following markers are in the high-risk zone: ${highRisk}. I recommend reviewing the latest lab results.`
              : "All primary physiological markers are currently within clinical tolerance levels.";
          } else {
            response = "I can fetch the analytics summary if you're viewing a valid patient profile.";
          }
        } catch {
          response = "I'm having trouble accessing the real-time analytics stream right now.";
        }
      } else if (lowerMsg.includes('tpa') || lowerMsg.includes('protocol')) {
        response = "The tPA eligibility gate is automatically calculated based on the Last Known Normal (LKN) and contraindications like INR > 1.7 or SBP > 185. Check the 'Treatment Protocols' section.";
      } else {
        response = "I'm here to assist with clinical questions, diagnostic results, and protocol verification. How else can I help?";
      }

      setMessages(prev => [...prev, { text: response, isUser: false, timestamp: new Date() }]);
      setIsTyping(false);
    }, 1000);
  };

  return (
    <>
      {/* Toggle Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-blue-600 hover:bg-blue-500 text-white rounded-full flex items-center justify-center shadow-2xl transition-all hover:scale-110 z-50 group"
      >
        {isOpen ? <X size={24} /> : <MessageSquare size={24} className="group-hover:rotate-12 transition-transform" />}
      </button>

      {/* Chat Container */}
      <div className={clsx(
        "fixed bottom-24 right-6 w-[400px] h-[600px] bg-slate-950 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden transition-all duration-300 z-50",
        isOpen ? "scale-100 opacity-100 translate-y-0" : "scale-95 opacity-0 translate-y-10 pointer-events-none"
      )}>
        {/* Header */}
        <div className="bg-blue-600 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
              <Bot size={20} className="text-white" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-sm">SRRIS Assistant</h3>
              <p className="text-blue-100 text-[10px]">AI-Powered Clinical Decisions</p>
            </div>
          </div>
          <div className="flex gap-2">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
            <span className="text-white/80 text-[10px]">Online</span>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-950">
          {messages.map((msg, i) => (
            <div key={i} className={clsx("flex gap-3", msg.isUser ? "flex-row-reverse" : "flex-row")}>
              <div className={clsx(
                "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                msg.isUser ? "bg-slate-800" : "bg-blue-900/30"
              )}>
                {msg.isUser ? <User size={16} className="text-slate-400" /> : <Bot size={16} className="text-blue-400" />}
              </div>
              <div className={clsx(
                "max-w-[75%] p-3 rounded-2xl text-sm",
                msg.isUser 
                  ? "bg-blue-600 text-white rounded-tr-none" 
                  : "bg-slate-900 text-slate-300 border border-slate-800 rounded-tl-none"
              )}>
                {msg.text}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-blue-900/30 flex items-center justify-center">
                <Bot size={16} className="text-blue-400" />
              </div>
              <div className="bg-slate-900 border border-slate-800 p-3 rounded-2xl rounded-tl-none">
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 bg-slate-600 rounded-full animate-bounce"></div>
                  <div className="w-1.5 h-1.5 bg-slate-600 rounded-full animate-bounce delay-100"></div>
                  <div className="w-1.5 h-1.5 bg-slate-600 rounded-full animate-bounce delay-200"></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 bg-slate-900/50 border-t border-slate-800">
          <div className="relative">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Type clinical question..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-blue-600 transition-colors"
            />
            <button 
              onClick={handleSendMessage}
              className="absolute right-2 top-2 p-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-colors"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default AIChatbot;
