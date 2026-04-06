"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Users, 
  Plus, 
  Search, 
  Filter, 
  MoreVertical, 
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  ShieldClose,
  Tag
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth/AuthContext";

interface CustomerSummary {
  id: string;
  customId: string;
  companyName: string;
  industry: string;
  status: string;
  risk: string;
  tags: string[];
  documentCount: number;
  wcdlCount: number;
  lastActivity: string | null;
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const { profile } = useAuth();

  useEffect(() => {
    fetchCustomers();
  }, []);

  const fetchCustomers = async () => {
    try {
      const data = await api.get<CustomerSummary[]>("customers");
      if (data) {
        setCustomers(data);
      }
    } catch (err) {
      console.error("Failed to fetch customers", err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = customers.filter(c => 
    c.companyName.toLowerCase().includes(search.toLowerCase()) ||
    c.customId.toLowerCase().includes(search.toLowerCase()) ||
    c.industry?.toLowerCase().includes(search.toLowerCase())
  );

  const getRiskColor = (risk: string) => {
    switch(risk.toUpperCase()) {
      case 'HIGH': return 'text-status-critical bg-status-critical-bg border-status-critical/20';
      case 'MEDIUM': return 'text-status-medium bg-status-medium-bg border-status-medium/20';
      case 'LOW': return 'text-status-success bg-status-success-bg border-status-success/20';
      default: return 'text-t-muted bg-neutral-row border-neutral-border';
    }
  };

  const getStatusColor = (status: string) => {
    switch(status.toUpperCase()) {
      case 'ACTIVE': return 'text-primary bg-primary-light border-primary/20';
      case 'INACTIVE': return 'text-t-muted bg-neutral-row border-neutral-border';
      case 'AUDIT': return 'text-ai-violet bg-ai-violet-light border-ai-violet/20';
      default: return 'text-t-muted bg-neutral-row border-neutral-border';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-t-heading">Customer Directory</h1>
          <p className="text-sm text-t-muted">Manage and track your client financial portfolios</p>
        </div>
        {(profile?.role_id === 0 || profile?.role_id === 1) && (
          <Link 
            href="/customers/new"
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-t-heading transition-colors hover:bg-primary-hover"
          >
            <Plus className="h-4 w-4" />
            Add Customer
          </Link>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-t-muted" />
          <input 
            type="text"
            placeholder="Search by name, ID or industry..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-neutral-border bg-neutral-card py-2.5 pl-10 pr-4 text-sm text-t-heading outline-none focus:border-primary/50"
          />
        </div>
        <button className="flex items-center gap-2 rounded-xl border border-neutral-border bg-neutral-card/50 px-4 py-2.5 text-sm font-medium text-t-muted hover:border-neutral-border hover:text-t-heading">
          <Filter className="h-4 w-4" />
          Filters
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-neutral-border bg-neutral-card/30 backdrop-blur-xl">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-neutral-border bg-neutral-row/20 text-[11px] font-bold uppercase tracking-widest text-t-muted">
              <th className="px-6 py-4">Customer</th>
              <th className="px-6 py-4">Industry</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Risk</th>
              <th className="px-6 py-4">Docs</th>
              <th className="px-6 py-4">Tags</th>
              <th className="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-border text-sm">
            {loading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i} className="animate-pulse">
                  <td colSpan={7} className="px-6 py-4"><div className="h-4 w-full rounded bg-neutral-row" /></td>
                </tr>
              ))
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-t-muted">
                  No customers found. 
                </td>
              </tr>
            ) : (
              filtered.map((customer) => (
                <tr key={customer.id} className="group hover:bg-neutral-row/30 transition-colors">
                  <td className="px-6 py-4">
                    <Link href={`/customers/${customer.id}`} className="block">
                      <div className="font-bold text-t-heading group-hover:text-primary transition-colors">{customer.companyName}</div>
                      <div className="text-[10px] text-t-muted font-mono uppercase tracking-tight">{customer.customId}</div>
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-t-muted">{customer.industry || '—'}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-tighter ${getStatusColor(customer.status)}`}>
                      {customer.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-tighter ${getRiskColor(customer.risk)}`}>
                      {customer.risk === 'HIGH' ? <ShieldAlert className="h-2.5 w-2.5" /> : 
                       customer.risk === 'MEDIUM' ? <ShieldCheck className="h-2.5 w-2.5" /> : 
                       <ShieldCheck className="h-2.5 w-2.5 opacity-50" />}
                      {customer.risk}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-col">
                      <span className="text-t-heading font-bold">{customer.documentCount}</span>
                      <span className="text-[10px] text-t-muted uppercase">Statements</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {customer.tags.slice(0, 2).map((tag, i) => (
                        <span key={i} className="rounded bg-neutral-row px-1.5 py-0.5 text-[9px] font-medium text-t-muted uppercase">
                          {tag}
                        </span>
                      ))}
                      {customer.tags.length > 2 && (
                        <span className="text-[9px] text-t-muted">+{customer.tags.length - 2}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link 
                      href={`/customers/${customer.id}`}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-t-muted hover:bg-neutral-row hover:text-t-heading"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
