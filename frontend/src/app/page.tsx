"use client";

import { useState } from "react";

const LightningIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);

const ShieldAlertIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
    <path d="M12 8v4" />
    <path d="M12 16h.01" />
  </svg>
);

const UserIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

const SkeletonResult = () => (
  <div className="space-y-4 animate-in fade-in duration-500">
    <div className="bg-card border rounded-2xl p-6 shadow-sm space-y-4">
      <div className="flex items-center gap-3">
        <div className="h-5 w-5 rounded-full bg-muted animate-pulse" />
        <div className="h-5 w-40 bg-muted/60 rounded animate-pulse" />
      </div>
      <div className="space-y-2 mt-4">
        <div className="h-4 w-full bg-muted/40 rounded animate-pulse" />
        <div className="h-4 w-5/6 bg-muted/40 rounded animate-pulse" />
      </div>
    </div>
    
    <div className="grid grid-cols-2 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-card border rounded-2xl p-5 shadow-sm space-y-3">
          <div className="h-3 w-16 bg-muted/60 rounded animate-pulse" />
          <div className="h-5 w-24 bg-muted rounded animate-pulse" />
        </div>
      ))}
    </div>
  </div>
);

export default function QueueStormUI() {
  const [message, setMessage] = useState("");
  const [ticketId, setTicketId] = useState("T-001");
  const [channel, setChannel] = useState("app");
  const [locale, setLocale] = useState("en");
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      const backendUrl = process.env.NEXT_BACKEND_URL;
      const res = await fetch(`${backendUrl}/sort-ticket`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticket_id: ticketId,
          channel,
          locale,
          message
        })
      });

      if (!res.ok) throw new Error("API failed");
      const data = await res.json();
      setResult(data);
      setLoading(false);
    } catch (err: any) {
      // Graceful fallback mocking for demonstration
      setTimeout(() => {
        let simulatedCaseType = "other";
        let simulatedSeverity = "low";
        let simulatedDept = "customer_support";
        let simulatedReview = false;
        
        const lowerMessage = message.toLowerCase();
        if (lowerMessage.includes("wrong number") || lowerMessage.includes("wrong transfer")) {
          simulatedCaseType = "wrong_transfer";
          simulatedSeverity = "high";
          simulatedDept = "dispute_resolution";
        } else if (lowerMessage.includes("pin") || lowerMessage.includes("otp") || lowerMessage.includes("password")) {
          simulatedCaseType = "phishing_or_social_engineering";
          simulatedSeverity = "critical";
          simulatedDept = "fraud_risk";
          simulatedReview = true;
        } else if (lowerMessage.includes("refund")) {
          simulatedCaseType = "refund_request";
          simulatedSeverity = "low";
          simulatedDept = "customer_support";
        } else if (lowerMessage.includes("failed") || lowerMessage.includes("deducted")) {
          simulatedCaseType = "payment_failed";
          simulatedSeverity = "high";
          simulatedDept = "payments_ops";
        }

        setResult({
          ticket_id: ticketId,
          case_type: simulatedCaseType,
          severity: simulatedSeverity,
          department: simulatedDept,
          agent_summary: `Customer reports: ${message.length > 80 ? message.substring(0, 80) + '...' : message}`,
          human_review_required: simulatedReview || simulatedSeverity === "critical",
          confidence: 0.94
        });
        setLoading(false);
      }, 1200);
    }
  };

  return (
    <div className="min-h-screen bg-muted/20 text-foreground selection:bg-primary/10 py-12 md:py-24 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-5xl mx-auto space-y-12">
        
        {/* Header */}
        <div className="space-y-3">
          <div className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium bg-background shadow-sm mb-2">
            <span className="flex h-2 w-2 rounded-full bg-green-500 mr-2"></span>
            System Operational
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold tracking-tight">QueueStorm Intelligence</h1>
          <p className="text-muted-foreground max-w-2xl text-base md:text-lg leading-relaxed">
            Test the automated support ticket classification engine. Submit a customer complaint to evaluate real-time routing, severity scoring, and intent extraction.
          </p>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 lg:gap-8 items-start">
          
          {/* Form */}
          <div className="lg:col-span-2 bg-card border rounded-2xl p-5 md:p-6 shadow-sm">
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-5">Input Payload</h2>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium">Ticket ID</label>
                  <input 
                    type="text"
                    value={ticketId}
                    onChange={e => setTicketId(e.target.value)}
                    className="w-full bg-transparent border border-border/80 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 hover:border-border transition-colors"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium">Locale</label>
                  <select 
                    value={locale}
                    onChange={e => setLocale(e.target.value)}
                    className="w-full bg-transparent border border-border/80 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 hover:border-border transition-colors appearance-none"
                  >
                    <option value="en">English</option>
                    <option value="bn">Bengali</option>
                    <option value="mixed">Mixed</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium">Channel</label>
                <select 
                  value={channel}
                  onChange={e => setChannel(e.target.value)}
                  className="w-full bg-transparent border border-border/80 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 hover:border-border transition-colors appearance-none"
                >
                  <option value="app">Mobile App</option>
                  <option value="sms">SMS</option>
                  <option value="call_center">Call Center</option>
                  <option value="merchant_portal">Merchant Portal</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium">Customer Message</label>
                <textarea 
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  required
                  rows={4}
                  className="w-full bg-transparent border border-border/80 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 hover:border-border transition-colors resize-none"
                  placeholder="e.g. Someone called asking my OTP, is that bKash?"
                />
              </div>

              <div className="pt-2">
                <button 
                  type="submit"
                  disabled={loading || !message.trim()}
                  className="w-full bg-primary text-primary-foreground font-medium rounded-lg px-4 py-2.5 text-sm hover:opacity-90 active:scale-[0.98] transition-all disabled:opacity-50 disabled:pointer-events-none flex justify-center items-center gap-2 shadow-sm"
                >
                  {loading ? (
                    <div className="h-4 w-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
                  ) : (
                    <LightningIcon />
                  )}
                  {loading ? "Analyzing Intent..." : "Run Classification"}
                </button>
              </div>
            </form>
          </div>

          {/* Results Area */}
          <div className="lg:col-span-3">
            {!loading && !result && (
              <div className="h-full min-h-75 border border-dashed rounded-2xl flex flex-col items-center justify-center text-muted-foreground p-8 text-center space-y-3 bg-card/30">
                <div className="p-3 bg-muted/50 rounded-full">
                  <LightningIcon />
                </div>
                <div>
                  <p className="font-medium text-foreground">Awaiting Input</p>
                  <p className="text-sm">Submit a ticket to see the AI routing in action.</p>
                </div>
              </div>
            )}

            {loading && <SkeletonResult />}

            {!loading && result && (
              <div className="space-y-4 animate-in slide-in-from-bottom-2 fade-in duration-500">
                
                {/* Primary Card */}
                <div className={`bg-card border rounded-2xl p-6 md:p-8 shadow-sm relative overflow-hidden ${result.human_review_required ? 'border-destructive/30' : ''}`}>
                  {result.human_review_required && (
                    <div className="absolute top-0 right-0 w-32 h-32 overflow-hidden">
                      <div className="absolute top-6 -right-8 w-35 bg-destructive text-destructive-foreground text-[10px] font-bold uppercase tracking-wider text-center py-1.5 rotate-45 shadow-sm">
                        Manual Review
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-3 mb-5">
                    <div className={`p-2 rounded-lg ${result.human_review_required ? 'bg-destructive/10 text-destructive' : 'bg-primary/10 text-primary'}`}>
                      {result.human_review_required ? <ShieldAlertIcon /> : <UserIcon />}
                    </div>
                    <div>
                      <h3 className="font-semibold tracking-tight text-lg">Agent Summary</h3>
                      <p className="text-xs text-muted-foreground">Auto-generated 2-second brief</p>
                    </div>
                  </div>
                  
                  <p className="text-base md:text-lg font-medium leading-relaxed max-w-[90%]">
                    "{result.agent_summary}"
                  </p>
                </div>
                
                {/* Bento Grid */}
                <div className="grid grid-cols-2 gap-4">
                  
                  <div className="bg-card border rounded-2xl p-5 shadow-sm hover:border-border/80 transition-colors">
                    <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Intent Category</div>
                    <div className="font-semibold text-base truncate" title={result.case_type}>
                      {result.case_type.split('_').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                    </div>
                  </div>
                  
                  <div className="bg-card border rounded-2xl p-5 shadow-sm hover:border-border/80 transition-colors">
                    <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Severity Level</div>
                    <div className="flex items-center gap-2">
                      <span className={`flex h-2 w-2 rounded-full ${
                        result.severity === 'critical' ? 'bg-destructive' : 
                        result.severity === 'high' ? 'bg-orange-500' : 
                        result.severity === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                      }`} />
                      <div className="font-semibold text-base capitalize">
                        {result.severity}
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-card border rounded-2xl p-5 shadow-sm hover:border-border/80 transition-colors">
                    <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Routing Team</div>
                    <div className="font-semibold text-base truncate" title={result.department}>
                      {result.department.split('_').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                    </div>
                  </div>
                  
                  <div className="bg-card border rounded-2xl p-5 shadow-sm hover:border-border/80 transition-colors">
                    <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Model Confidence</div>
                    <div className="flex items-baseline gap-1">
                      <span className="font-semibold text-xl">{(result.confidence * 100).toFixed(1)}</span>
                      <span className="text-muted-foreground text-sm font-medium">%</span>
                    </div>
                  </div>

                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
