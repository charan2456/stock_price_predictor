import { useState, useEffect } from "react";
import { MessageSquare, FileText, TrendingUp, Globe } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { fetchSentimentFeed, type SentimentItemAPI } from "../services/api";

// Fallback feed items
const FALLBACK_FEED = [
  { id: 1, source: 'reuters', headline: 'Apple announces new AI features for iPhone, stock surges in afternoon trading', sentiment: 'positive', sentimentScore: 0.82, timestamp: '14 min ago', ticker: 'AAPL' },
  { id: 2, source: 'reddit', headline: 'TSLA hourly RSI hitting overbought levels — short squeeze incoming? 🚀', sentiment: 'positive', sentimentScore: 0.74, timestamp: '28 min ago', ticker: 'TSLA' },
  { id: 3, source: 'marketwatch', headline: 'Amazon faces regulatory scrutiny — shares drop 2% in last hour', sentiment: 'negative', sentimentScore: -0.65, timestamp: '42 min ago', ticker: 'AMZN' },
  { id: 4, source: 'reuters', headline: 'Microsoft Azure revenue growth exceeds analyst expectations in Q4 preview', sentiment: 'positive', sentimentScore: 0.71, timestamp: '1h 15min ago', ticker: 'MSFT' },
  { id: 5, source: 'reddit', headline: 'Google search losing market share to AI competitors? Hourly sentiment plunging', sentiment: 'negative', sentimentScore: -0.58, timestamp: '1h 30min ago', ticker: 'GOOGL' },
  { id: 6, source: 'yahoo', headline: 'Tech stocks rally as Fed signals potential rate cuts — AAPL leads', sentiment: 'positive', sentimentScore: 0.88, timestamp: '2h ago', ticker: 'AAPL' },
  { id: 7, source: 'reddit', headline: 'AMZN Prime Day sales disappoint — negative sentiment across WSB this hour', sentiment: 'negative', sentimentScore: -0.73, timestamp: '2h 20min ago', ticker: 'AMZN' },
  { id: 8, source: 'reuters', headline: 'Tesla Gigafactory Austin production ramp accelerates — bullish momentum', sentiment: 'positive', sentimentScore: 0.69, timestamp: '3h ago', ticker: 'TSLA' },
];

const TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'];
const TICKER_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
const BASE_SENTIMENTS: Record<string, number> = { AAPL: 0.68, MSFT: 0.43, GOOGL: 0.55, AMZN: -0.32, TSLA: 0.81 };

function generateSentimentTrends() {
  const now = new Date();
  return Array.from({ length: 24 }, (_, i) => {
    const time = new Date(now);
    time.setHours(time.getHours() - (23 - i));
    const point: any = { time: time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }) };
    TICKERS.forEach(t => {
      point[t] = parseFloat((Math.max(-1, Math.min(1, BASE_SENTIMENTS[t] + (Math.random() - 0.5) * 0.25))).toFixed(2));
    });
    return point;
  });
}

function timeSince(ts: string | null): string {
  if (!ts) return 'recently';
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins} min ago`;
  return `${Math.floor(mins / 60)}h ${mins % 60}min ago`;
}

export function SentimentFeed() {
  const [feedItems, setFeedItems] = useState<any[]>(FALLBACK_FEED);
  const sentimentTrends = generateSentimentTrends();

  useEffect(() => {
    async function loadData() {
      const data = await fetchSentimentFeed(20);
      if (data?.items?.length) {
        setFeedItems(data.items.map((e: SentimentItemAPI) => ({
          id: e.id,
          source: e.source,
          headline: e.headline,
          sentiment: e.sentiment,
          sentimentScore: e.sentiment_score,
          timestamp: timeSince(e.timestamp),
          ticker: e.ticker,
        })));
      }
    }
    loadData();
  }, []);

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'reddit': return <MessageSquare className="w-5 h-5 text-[#ff4500]" />;
      case 'reuters': return <FileText className="w-5 h-5 text-[#ff6600]" />;
      case 'yahoo': return <TrendingUp className="w-5 h-5 text-[#720e9e]" />;
      case 'marketwatch': return <Globe className="w-5 h-5 text-[#3b82f6]" />;
      default: return <FileText className="w-5 h-5 text-gray-400" />;
    }
  };

  const getSentimentBadge = (sentiment: string, score?: number) => {
    const styles: Record<string, string> = {
      positive: 'bg-[#10b981]/20 text-[#10b981]',
      negative: 'bg-[#ef4444]/20 text-[#ef4444]',
      neutral: 'bg-gray-500/20 text-gray-400',
    };
    return (
      <div className="flex items-center gap-2">
        <span className={`px-2 py-1 rounded-md text-xs font-medium ${styles[sentiment] ?? styles.neutral}`}>{sentiment.toUpperCase()}</span>
        {score != null && <span className={`text-xs font-mono ${score > 0 ? 'text-[#10b981]' : score < 0 ? 'text-[#ef4444]' : 'text-gray-400'}`}>{score > 0 ? '+' : ''}{score.toFixed(2)}</span>}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-white mb-2">Sentiment Feed</h1>
        <p className="text-gray-400">Hourly sentiment analysis from news and social media — updated every hour</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-4 max-h-[800px] overflow-y-auto pr-2 custom-scrollbar">
          {feedItems.map((item) => (
            <div key={item.id} className="p-5 bg-white/5 border border-white/10 rounded-xl backdrop-blur-xl hover:bg-white/10 transition-all">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-white/5 rounded-lg">{getSourceIcon(item.source)}</div>
                <div className="flex-1">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <h3 className="text-white font-medium leading-tight">{item.headline}</h3>
                    {getSentimentBadge(item.sentiment, item.sentimentScore)}
                  </div>
                  <div className="flex items-center gap-4 text-sm text-gray-400">
                    <span className="capitalize">{item.source}</span><span>•</span>
                    <span>{item.timestamp}</span><span>•</span>
                    <span className="text-[#3b82f6] font-medium">${item.ticker}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-white/5 border border-white/10 rounded-xl backdrop-blur-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-2">24H Sentiment Trends</h3>
          <p className="text-xs text-gray-500 mb-6">Hourly compound sentiment per ticker</p>
          <ResponsiveContainer width="100%" height={700}>
            <LineChart data={sentimentTrends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#6b7280" tick={{ fill: '#6b7280', fontSize: 10 }} interval={3} />
              <YAxis stroke="#6b7280" tick={{ fill: '#6b7280', fontSize: 11 }} domain={[-1, 1]} />
              <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(71, 85, 105, 0.3)', borderRadius: '8px', color: '#e2e8f0' }} formatter={(value: number) => [value.toFixed(2), '']} labelFormatter={(l) => `Hour: ${l}`} />
              <Legend wrapperStyle={{ fontSize: '12px' }} iconType="line" />
              {TICKERS.map((ticker, i) => <Line key={ticker} type="monotone" dataKey={ticker} stroke={TICKER_COLORS[i]} strokeWidth={2} dot={false} />)}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <style>{`.custom-scrollbar::-webkit-scrollbar{width:8px}.custom-scrollbar::-webkit-scrollbar-track{background:rgba(30,41,59,.5);border-radius:4px}.custom-scrollbar::-webkit-scrollbar-thumb{background:rgba(71,85,105,.5);border-radius:4px}.custom-scrollbar::-webkit-scrollbar-thumb:hover{background:rgba(71,85,105,.7)}`}</style>
    </div>
  );
}
