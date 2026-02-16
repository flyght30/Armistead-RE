import React, { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bot,
  Send,
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  Loader2,
} from 'lucide-react';
import apiClient from '../lib/api';
import PageHeader from '../components/ui/PageHeader';
import Card from '../components/ui/Card';
import { FullPageSpinner } from '../components/ui/Spinner';

interface AIMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

interface RiskAlert {
  id: string;
  transaction_id: string;
  severity: string;
  title: string;
  description: string;
  recommendation: string;
  status: string;
  created_at: string;
}

interface ClosingReadiness {
  score: number;
  status: string;
  blockers: string[];
  warnings: string[];
  ready_items: string[];
}

const suggestedPrompts = [
  "What's the biggest risk on this deal?",
  "Draft a counter-offer email to the seller",
  "What milestones are behind schedule?",
  "Summarize this transaction's status",
];

export default function AIAdvisor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: conversation, isLoading } = useQuery({
    queryKey: ['advisor-conversation', id],
    queryFn: async () => {
      const res = await apiClient.get(`/transactions/${id}/advisor/conversation`);
      return res.data as { messages: AIMessage[] };
    },
    enabled: !!id,
  });

  const { data: riskAlerts } = useQuery({
    queryKey: ['risk-alerts', id],
    queryFn: async () => {
      const res = await apiClient.get(`/transactions/${id}/risk-alerts`);
      return res.data as RiskAlert[];
    },
    enabled: !!id,
  });

  const { data: readiness } = useQuery({
    queryKey: ['closing-readiness', id],
    queryFn: async () => {
      const res = await apiClient.get(`/transactions/${id}/closing-readiness`);
      return res.data as ClosingReadiness;
    },
    enabled: !!id,
  });

  const chatMutation = useMutation({
    mutationFn: async (message: string) => {
      const res = await apiClient.post(`/transactions/${id}/advisor/chat`, { message });
      return res.data as { response: string; risk_alerts?: RiskAlert[] };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['advisor-conversation', id] });
      queryClient.invalidateQueries({ queryKey: ['risk-alerts', id] });
      setInput('');
    },
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation?.messages, chatMutation.isPending]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || chatMutation.isPending) return;
    chatMutation.mutate(trimmed);
  };

  if (isLoading) return <FullPageSpinner />;

  const messages = conversation?.messages ?? [];

  return (
    <div>
      <div className="mb-4">
        <button
          onClick={() => navigate(`/transaction/${id}`)}
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Transaction
        </button>
      </div>

      <PageHeader
        title="AI Advisor"
        subtitle="Get AI-powered insights about your transaction"
        actions={
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-indigo-600" />
            <Sparkles className="w-4 h-4 text-yellow-500" />
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat Panel */}
        <div className="lg:col-span-2">
          <Card padding={false} className="flex flex-col h-[600px]">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 && !chatMutation.isPending && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <Bot className="w-12 h-12 text-indigo-300 mb-3" />
                  <p className="text-gray-500 text-sm mb-4">
                    Ask me anything about this transaction
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-md">
                    {suggestedPrompts.map((prompt) => (
                      <button
                        key={prompt}
                        onClick={() => {
                          setInput(prompt);
                          inputRef.current?.focus();
                        }}
                        className="text-left text-xs px-3 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-colors"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                      msg.role === 'user'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    <time className={`text-[10px] mt-1 block ${msg.role === 'user' ? 'text-indigo-200' : 'text-gray-400'}`}>
                      {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </time>
                  </div>
                </div>
              ))}

              {chatMutation.isPending && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-xl px-4 py-3 text-sm text-gray-500">
                    <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
                    Thinking...
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="border-t border-gray-200 p-4">
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Ask about this transaction..."
                  className="flex-1 px-4 py-2.5 text-sm rounded-lg border border-gray-300 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  disabled={chatMutation.isPending}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || chatMutation.isPending}
                  className="px-4 py-2.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </Card>
        </div>

        {/* Sidebar: Risk Alerts + Closing Readiness */}
        <div className="space-y-6">
          {/* Closing Readiness */}
          {readiness && (
            <Card title="Closing Readiness">
              <div className="text-center mb-4">
                <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full ${
                  readiness.score >= 80 ? 'bg-green-100' : readiness.score >= 50 ? 'bg-yellow-100' : 'bg-red-100'
                }`}>
                  <span className={`text-xl font-bold ${
                    readiness.score >= 80 ? 'text-green-700' : readiness.score >= 50 ? 'text-yellow-700' : 'text-red-700'
                  }`}>
                    {readiness.score}%
                  </span>
                </div>
                <p className="text-sm text-gray-500 mt-2 capitalize">{readiness.status}</p>
              </div>

              {readiness.blockers.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs font-medium text-red-600 mb-1">Blockers</p>
                  {readiness.blockers.map((b, i) => (
                    <p key={i} className="text-xs text-red-500 flex items-start gap-1.5 mb-1">
                      <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                      {b}
                    </p>
                  ))}
                </div>
              )}

              {readiness.ready_items.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-green-600 mb-1">Ready</p>
                  {readiness.ready_items.map((r, i) => (
                    <p key={i} className="text-xs text-green-600 flex items-start gap-1.5 mb-1">
                      <CheckCircle2 className="w-3 h-3 mt-0.5 flex-shrink-0" />
                      {r}
                    </p>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* Risk Alerts */}
          <Card title="Risk Alerts" subtitle={riskAlerts ? `${riskAlerts.length} alerts` : undefined}>
            {!riskAlerts || riskAlerts.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">No active risk alerts</p>
            ) : (
              <div className="space-y-3">
                {riskAlerts.filter(a => a.status === 'active').slice(0, 5).map((alert) => (
                  <div key={alert.id} className={`p-3 rounded-lg border ${
                    alert.severity === 'high' ? 'border-red-200 bg-red-50' :
                    alert.severity === 'medium' ? 'border-yellow-200 bg-yellow-50' :
                    'border-blue-200 bg-blue-50'
                  }`}>
                    <p className={`text-xs font-semibold ${
                      alert.severity === 'high' ? 'text-red-700' :
                      alert.severity === 'medium' ? 'text-yellow-700' :
                      'text-blue-700'
                    }`}>{alert.title}</p>
                    <p className="text-xs text-gray-600 mt-1">{alert.description}</p>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
