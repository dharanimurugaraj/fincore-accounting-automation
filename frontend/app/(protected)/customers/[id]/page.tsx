"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { 
  Building2, 
  Mail, 
  Phone, 
  IdCard, 
  Briefcase, 
  FileText, 
  BarChart3, 
  Upload, 
  ChevronLeft,
  Calendar,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Clock,
  Download,
  MoreVertical,
  Activity,
  Tag
} from "lucide-react";
import { useAuth } from "@/components/auth/AuthContext";

export default function CustomerDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { profile } = useAuth();
  const [customer, setCustomer] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [pipelineRuns, setPipelineRuns] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'statements' | 'reports'>('statements');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (params.id) {
      fetchCustomerData();
    }
  }, [params.id]);

  const fetchCustomerData = async () => {
    try {
      const [custRes, docsRes, runsRes] = await Promise.all([
        fetch(`/api/customers/${params.id}`),
        fetch(`/api/customers/${params.id}/documents`),
        fetch(`/api/customers/${params.id}/pipeline-runs`)
      ]);

      if (custRes.ok) setCustomer(await custRes.json());
      if (docsRes.ok) setDocuments(await docsRes.json());
      if (runsRes.ok) setPipelineRuns(await runsRes.json());
    } catch (err) {
      console.error("Failed to fetch customer details", err);
    } finally {
      setLoading(false);
    }
  };

  const getRiskIcon = (risk: string) => {
    switch(risk?.toUpperCase()) {
      case 'HIGH': return <ShieldAlert className="h-5 w-5 text-status-critical" />;
      case 'MEDIUM': return <ShieldCheck className="h-5 w-5 text-status-medium" />;
      case 'LOW': return <ShieldX className="h-5 w-5 text-status-success opacity-50" />;
      default: return null;
    }
  };

  if (loading) return <div className="animate-pulse space-y-6">
    <div className="h-40 rounded-2xl bg-neutral-card/50 border border-neutral-border" />
    <div className="grid grid-cols-3 gap-6">
      <div className="h-64 rounded-2xl bg-neutral-card/50 border border-neutral-border" />
      <div className="h-64 rounded-2xl bg-neutral-card/50 border border-neutral-border" />
      <div className="h-64 rounded-2xl bg-neutral-card/50 border border-neutral-border" />
    </div>
  </div>;

  if (!customer) return <div className="text-center py-20 text-t-muted">Customer not found.</div>;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header / Navigation */}
      <div className="flex items-center justify-between">
        <button 
          onClick={() => router.push('/customers')}
          className="flex items-center gap-2 text-sm text-t-muted hover:text-t-heading"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Directory
        </button>
        <div className="flex items-center gap-3">
          <button className="rounded-lg border border-neutral-border bg-neutral-card px-4 py-2 text-sm font-semibold text-t-muted hover:border-neutral-border hover:text-t-heading">
            Edit Profile
          </button>
          <button 
            onClick={() => router.push(`/upload?customerId=${customer.id}`)}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-bold text-t-heading hover:bg-primary-hover"
          >
            <Upload className="h-4 w-4" />
            Upload New Statement
          </button>
        </div>
      </div>

      {/* Hero Card */}
      <div className="rounded-3xl border border-neutral-border bg-gradient-to-br from-slate-900 to-slate-950 p-8 shadow-2xl shadow-sm shadow-primary/5 overflow-hidden relative">
        <div className="absolute top-0 right-0 p-8 opacity-10">
          <Building2 className="h-40 w-40" />
        </div>
        
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-4">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <h1 className="text-3xl font-extrabold text-t-heading">{customer.companyName}</h1>
                <span className="rounded-full bg-primary/10 border border-primary/20 px-3 py-1 text-[10px] font-bold text-primary uppercase tracking-widest">
                  {customer.status}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-t-muted">
                <span className="font-mono uppercase tracking-widest text-[#6366F1]">{customer.customId}</span>
                <span className="opacity-20">•</span>
                <span className="flex items-center gap-1 font-medium"><Briefcase className="h-3 w-3" /> {customer.industry}</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-6 text-sm">
              <div className="flex items-center gap-2 text-t-muted">
                <IdCard className="h-4 w-4 text-t-muted" />
                <span className="font-mono font-bold tracking-widest uppercase text-t-body">{customer.pan}</span>
              </div>
              <div className="flex items-center gap-2 text-t-muted">
                <Mail className="h-4 w-4 text-t-muted" />
                <span>{customer.email}</span>
              </div>
              <div className="flex items-center gap-2 text-t-muted">
                <Phone className="h-4 w-4 text-t-muted" />
                <span>{customer.phone}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4 bg-neutral-app/40 p-6 rounded-2xl border border-neutral-border/50">
            <div className="text-right">
              <p className="text-[10px] font-bold text-t-muted uppercase tracking-widest">Risk Profiling</p>
              <p className={`text-lg font-bold uppercase italic tracking-tighter ${
                customer.risk === 'HIGH' ? 'text-status-critical' : customer.risk === 'MEDIUM' ? 'text-status-medium' : 'text-status-success'
              }`}>
                {customer.risk} RISK
              </p>
            </div>
            <div className="h-12 w-12 rounded-full border border-neutral-border flex items-center justify-center bg-neutral-card shadow-xl">
              {getRiskIcon(customer.risk)}
            </div>
          </div>
        </div>
      </div>

      {/* Analytics Mini Board */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Statements', value: documents.length, icon: FileText, color: 'text-ai-violet' },
          { label: 'Analysed Runs', value: pipelineRuns.length, icon: BarChart3, color: 'text-primary' },
          { label: 'WCDL Alerts', value: 0, icon: ShieldAlert, color: 'text-status-medium' },
          { label: 'Active Flags', value: 0, icon: ShieldX, color: 'text-status-critical' },
        ].map((stat, i) => (
          <div key={i} className="rounded-2xl border border-neutral-border bg-neutral-card/30 p-4 flex items-center gap-4">
            <div className={`h-10 w-10 rounded-xl bg-neutral-app border border-neutral-border flex items-center justify-center ${stat.color}`}>
              <stat.icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[10px] font-bold text-t-muted uppercase tracking-widest">{stat.label}</p>
              <p className="text-xl font-bold text-t-heading">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Document Tabs */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex border-b border-neutral-border">
            <button 
              onClick={() => setActiveTab('statements')}
              className={`px-6 py-3 text-sm font-bold uppercase tracking-widest transition-all relative ${
                activeTab === 'statements' ? 'text-primary' : 'text-t-muted hover:text-t-body'
              }`}
            >
              Bank Statements
              {activeTab === 'statements' && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-primary-hover rounded-full" />}
            </button>
            <button 
              onClick={() => setActiveTab('reports')}
              className={`px-6 py-3 text-sm font-bold uppercase tracking-widest transition-all relative ${
                activeTab === 'reports' ? 'text-primary' : 'text-t-muted hover:text-t-body'
              }`}
            >
              Extracted Reports
              {activeTab === 'reports' && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-primary-hover rounded-full" />}
            </button>
          </div>

          <div className="space-y-3 pt-2">
            {activeTab === 'statements' ? (
              documents.length === 0 ? (
                <div className="text-center py-20 rounded-2xl border border-dashed border-neutral-border text-t-muted">
                  No bank statements uploaded yet.
                </div>
              ) : (
                documents.map((doc, i) => (
                  <div key={doc.id} className="group flex items-center justify-between rounded-2xl border border-neutral-border bg-neutral-card/50 p-4 hover:border-neutral-border transition-all">
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-lg bg-neutral-app border border-neutral-border flex items-center justify-center">
                        <FileText className="h-5 w-5 text-ai-violet" />
                      </div>
                      <div>
                        <p className="font-bold text-t-heading group-hover:text-ai-violet transition-colors uppercase tracking-tight text-sm">{doc.filename}</p>
                        <div className="flex items-center gap-2 text-[10px] text-t-muted font-bold uppercase">
                          <span className="text-t-body">{doc.bankName}</span>
                          <span>•</span>
                          <span>{doc.statementMonth}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded border ${
                        doc.status === 'OCR_COMPLETE' ? 'bg-emerald-400/5 border-status-success/20 text-status-success' : 'bg-neutral-row border-neutral-border text-t-muted'
                      }`}>
                        {doc.status}
                      </span>
                      <a href={`/api/v1/uploads?action=download&key=${encodeURIComponent(doc.s3Key)}`} className="h-8 w-8 rounded-lg flex items-center justify-center text-t-muted hover:bg-neutral-row hover:text-t-heading transition-colors">
                        <Download className="h-4 w-4" />
                      </a>
                    </div>
                  </div>
                ))
              )
            ) : (
              pipelineRuns.length === 0 ? (
                <div className="text-center py-20 rounded-2xl border border-dashed border-neutral-border text-t-muted">
                  No reports generated yet. Run the pipeline to see results.
                </div>
              ) : (
                pipelineRuns.map((run, i) => (
                  <div key={run.id} className="rounded-2xl border border-neutral-border bg-neutral-card/50 p-6 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded bg-primary-hover/10 flex items-center justify-center">
                          <BarChart3 className="h-4 w-4 text-primary" />
                        </div>
                        <div>
                          <p className="text-sm font-bold text-t-heading uppercase">Analysis Cycle: {run.statementMonth}</p>
                          <p className="text-[10px] text-t-muted font-mono tracking-tighter uppercase">{run.id}</p>
                        </div>
                      </div>
                      <span className="text-[10px] font-bold uppercase text-status-success bg-status-success-bg px-2 py-0.5 rounded border border-status-success/20">
                        {run.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                       <a href={`/api/v1/pipeline?action=download&key=${encodeURIComponent(run.workingSheetKey)}`} className="flex items-center gap-3 p-3 rounded-xl border border-neutral-border bg-neutral-app/50 hover:bg-neutral-row transition-all group">
                         <div className="h-8 w-8 rounded bg-status-success-bg flex items-center justify-center text-status-success">
                           <Download className="h-4 w-4" />
                         </div>
                         <div>
                           <p className="text-xs font-bold text-t-body group-hover:text-status-success">Working Sheet</p>
                           <p className="text-[9px] text-t-muted uppercase">Excel format</p>
                         </div>
                       </a>
                       <a href={`/api/v1/pipeline?action=download&key=${encodeURIComponent(run.bankingReportKey)}`} className="flex items-center gap-3 p-3 rounded-xl border border-neutral-border bg-neutral-app/50 hover:bg-neutral-row transition-all group">
                         <div className="h-8 w-8 rounded bg-primary/10 flex items-center justify-center text-primary">
                           <Download className="h-4 w-4" />
                         </div>
                         <div>
                           <p className="text-xs font-bold text-t-body group-hover:text-primary">Banking Report</p>
                           <p className="text-[9px] text-t-muted uppercase">Final analysis</p>
                         </div>
                       </a>
                    </div>
                  </div>
                ))
              )
            )}
          </div>
        </div>

        {/* Sidebar info */}
        <div className="space-y-6">
          {/* Metadata Card */}
          <div className="rounded-2xl border border-neutral-border bg-neutral-card/40 p-6 space-y-6">
            <h3 className="text-[10px] font-bold text-t-muted uppercase tracking-widest flex items-center gap-2">
              <Activity className="h-3 w-3" /> System Intelligence
            </h3>
            
            <div className="space-y-4">
               <div>
                  <p className="text-[9px] text-t-muted uppercase font-bold tracking-widest mb-2">Portfolio Tags</p>
                  <div className="flex flex-wrap gap-2">
                    {customer.tags?.map((tag: any, i: number) => (
                      <span key={i} className="flex items-center gap-1.5 rounded-full bg-neutral-app border border-neutral-border px-3 py-1 text-[9px] font-bold text-t-muted uppercase tracking-tight">
                        <Tag className="h-2.5 w-2.5 text-primary" />
                        {tag}
                      </span>
                    ))}
                  </div>
               </div>

               <div className="pt-4 border-t border-neutral-border/50 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-t-muted uppercase font-bold">Onboarded On</span>
                    <span className="text-[10px] text-t-body font-mono">{new Date(customer.createdAt).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-t-muted uppercase font-bold">Last Activity</span>
                    <span className="text-[10px] text-t-body font-mono">2 hours ago</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-t-muted uppercase font-bold">Main Org ID</span>
                    <span className="text-[10px] text-[#6366F1] font-mono">{customer.orgId}</span>
                  </div>
               </div>
            </div>
          </div>

          {/* Audit Snippet */}
          <div className="rounded-2xl border border-neutral-border bg-neutral-card/40 p-6 space-y-4">
            <h2 className="text-[10px] font-bold text-t-muted uppercase tracking-widest flex items-center gap-2">
              <Clock className="h-3 w-3" /> Recent Audits
            </h2>
            <div className="space-y-4">
               {[1, 2].map((_, i) => (
                 <div key={i} className="border-l border-neutral-border pl-4 py-1 space-y-1">
                   <p className="text-[11px] text-t-body"><span className="font-bold text-primary">Analyst</span> uploaded HDFC statement</p>
                   <p className="text-[9px] text-t-muted uppercase font-bold">Apr 06, 2:15 PM</p>
                 </div>
               ))}
               <button className="w-full text-center py-2 text-[10px] font-bold text-t-muted hover:text-primary uppercase tracking-widest">
                  View full history
               </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
