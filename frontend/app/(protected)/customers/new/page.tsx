"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { 
  Building2, 
  User, 
  IdCard, 
  Building, 
  Mail, 
  Phone, 
  Briefcase, 
  MapPin, 
  Tag, 
  Save, 
  X,
  Plus
} from "lucide-react";

const PRESET_TAGS = [
  "High Value", "VIP", "Under Audit", "New Client", 
  "Priority", "Watch List", "Low Activity"
];

const INDUSTRIES = [
  "Manufacturing", "IT Services", "Finance", "Healthcare", 
  "Retail", "Construction", "Logistics", "Export/Import"
];

export default function NewCustomerPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    companyName: "",
    contactName: "",
    pan: "",
    cin: "",
    email: "",
    phone: "",
    industry: "",
    address: "",
    tags: [] as string[],
    status: "ACTIVE",
    risk: "LOW"
  });

  const [customTag, setCustomTag] = useState("");

  const toggleTag = (tag: string) => {
    if (formData.tags.includes(tag)) {
      setFormData({ ...formData, tags: formData.tags.filter(t => t !== tag) });
    } else {
      if (formData.tags.length < 5) {
        setFormData({ ...formData, tags: [...formData.tags, tag] });
      }
    }
  };

  const addCustomTag = () => {
    if (customTag && !formData.tags.includes(customTag) && formData.tags.length < 5) {
      setFormData({ ...formData, tags: [...formData.tags, customTag] });
      setCustomTag("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("customers", formData);
      router.push("/customers");
    } catch (err: any) {
      alert(`Error: ${err.message || "Failed to create customer"}`);
      console.error("Submit failed", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-t-heading uppercase tracking-widest">Register New Client</h1>
          <p className="text-sm text-t-muted">Onboard a new customer profile into the FinCore monitoring system</p>
        </div>
        <button 
          onClick={() => router.back()}
          className="rounded-lg p-2 text-t-muted hover:bg-neutral-row hover:text-t-heading"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-20">
        {/* Basic Info Section */}
        <section className="space-y-4 rounded-2xl border border-neutral-border bg-neutral-card/40 p-6 backdrop-blur-xl">
          <h2 className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-primary">
            <Building2 className="h-3 w-3" />
            Core Identification
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-t-muted">Company Name</label>
              <div className="relative mt-1">
                <Building className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-t-muted" />
                <input 
                  required
                  type="text"
                  placeholder="e.g. Acme FinTech Pvt Ltd"
                  className="w-full bg-neutral-app/50 border border-neutral-border rounded-lg py-2 pl-10 pr-4 text-sm text-t-heading outline-none focus:border-primary/50"
                  value={formData.companyName}
                  onChange={(e) => setFormData({...formData, companyName: e.target.value})}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] font-bold uppercase tracking-widest text-t-muted">PAN Number</label>
                <div className="relative mt-1">
                  <IdCard className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-t-muted" />
                  <input 
                    required
                    type="text"
                    placeholder="ABCDE1234F"
                    className="w-full bg-neutral-app/50 border border-neutral-border rounded-lg py-2 pl-10 pr-4 text-sm text-t-heading uppercase outline-none focus:border-primary/50"
                    value={formData.pan}
                    onChange={(e) => setFormData({...formData, pan: e.target.value})}
                  />
                </div>
              </div>
              <div>
                <label className="text-[10px] font-bold uppercase tracking-widest text-t-muted">CIN (Optional)</label>
                <div className="relative mt-1">
                  <IdCard className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-t-muted" />
                  <input 
                    type="text"
                    placeholder="U12345DL2024..."
                    className="w-full bg-neutral-app/50 border border-neutral-border rounded-lg py-2 pl-10 pr-4 text-sm text-t-heading uppercase outline-none focus:border-primary/50"
                    value={formData.cin}
                    onChange={(e) => setFormData({...formData, cin: e.target.value})}
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Contact Section */}
        <section className="space-y-4 rounded-2xl border border-neutral-border bg-neutral-card/40 p-6 backdrop-blur-xl">
          <h2 className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-ai-violet">
            <User className="h-3 w-3" />
            Contact & Communication
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-t-muted">Primary Contact Name</label>
              <div className="mt-1 relative">
                <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-t-muted" />
                <input 
                  required
                  type="text"
                  placeholder="John Doe"
                  className="w-full bg-neutral-app/50 border border-neutral-border rounded-lg py-2 pl-10 pr-4 text-sm text-t-heading outline-none focus:border-indigo-500/50"
                  value={formData.contactName}
                  onChange={(e) => setFormData({...formData, contactName: e.target.value})}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] font-bold uppercase tracking-widest text-t-muted">Email Address</label>
                <div className="relative mt-1">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-t-muted" />
                  <input 
                    required
                    type="email"
                    placeholder="john@company.com"
                    className="w-full bg-neutral-app/50 border border-neutral-border rounded-lg py-2 pl-10 pr-4 text-sm text-t-heading outline-none focus:border-indigo-500/50"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                  />
                </div>
              </div>
              <div>
                <label className="text-[10px] font-bold uppercase tracking-widest text-t-muted">Phone</label>
                <div className="relative mt-1">
                  <Phone className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-t-muted" />
                  <input 
                    required
                    type="tel"
                    placeholder="+91 98765 43210"
                    className="w-full bg-neutral-app/50 border border-neutral-border rounded-lg py-2 pl-10 pr-4 text-sm text-t-heading outline-none focus:border-indigo-500/50"
                    value={formData.phone}
                    onChange={(e) => setFormData({...formData, phone: e.target.value})}
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Industry & Location */}
        <section className="space-y-4 rounded-2xl border border-neutral-border bg-neutral-card/40 p-6 backdrop-blur-xl md:col-span-2">
          <h2 className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-status-medium">
            <Briefcase className="h-3 w-3" />
            Geography & Industry
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-t-muted">Industry Vertical</label>
              <div className="mt-1 relative">
                <Briefcase className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-t-muted" />
                <select 
                  className="w-full bg-neutral-app/50 border border-neutral-border rounded-lg py-2 pl-10 pr-4 text-sm text-t-heading outline-none appearance-none focus:border-amber-500/50"
                  value={formData.industry}
                  onChange={(e) => setFormData({...formData, industry: e.target.value})}
                >
                  <option value="" disabled>Select Industry</option>
                  {INDUSTRIES.map(ind => <option key={ind} value={ind}>{ind}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-t-muted">Physical Address (Optional)</label>
              <div className="mt-1 relative">
                <MapPin className="absolute left-3 top-3 h-4 w-4 text-t-muted" />
                <textarea 
                  rows={2}
                  placeholder="Enter full address..."
                  className="w-full bg-neutral-app/50 border border-neutral-border rounded-lg py-2 pl-10 pr-4 text-sm text-t-heading outline-none focus:border-amber-500/50"
                  value={formData.address}
                  onChange={(e) => setFormData({...formData, address: e.target.value})}
                />
              </div>
            </div>
          </div>
        </section>

        {/* Tags Section */}
        <section className="space-y-4 rounded-2xl border border-neutral-border bg-neutral-card/40 p-6 backdrop-blur-xl md:col-span-2">
          <h2 className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest text-status-success">
            <div className="flex items-center gap-2">
              <Tag className="h-3 w-3" />
              Segmentation Tags (Upto 5)
            </div>
            <span className={formData.tags.length === 5 ? "text-status-critical" : "text-t-muted italic"}>
              {formData.tags.length}/5 Selected
            </span>
          </h2>
          
          <div className="flex flex-wrap gap-2">
            {PRESET_TAGS.map(tag => (
              <button
                key={tag}
                type="button"
                onClick={() => toggleTag(tag)}
                className={`rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-tight transition-all border ${
                  formData.tags.includes(tag) 
                    ? "bg-emerald-500 border-emerald-400 text-t-heading" 
                    : "border-neutral-border bg-neutral-app/50 text-t-muted hover:border-emerald-500/50 hover:text-status-success"
                }`}
              >
                {tag}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 mt-4 pt-4 border-t border-neutral-border/50">
            <input 
              type="text"
              placeholder="Add custom tag..."
              value={customTag}
              onChange={(e) => setCustomTag(e.target.value)}
              className="bg-neutral-app/50 border border-neutral-border rounded-lg py-1.5 px-4 text-xs text-t-heading outline-none focus:border-status-success/30"
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addCustomTag())}
            />
            <button 
              type="button"
              onClick={addCustomTag}
              className="rounded-lg p-1.5 text-t-muted hover:bg-neutral-row hover:text-status-success"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
        </section>

        {/* Footer Actions */}
        <div className="md:col-span-2 flex items-center justify-end gap-3 pt-6 border-t border-neutral-border/50">
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded-lg px-6 py-2.5 text-sm font-semibold text-t-muted hover:bg-neutral-row"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 rounded-xl bg-primary px-8 py-2.5 text-sm font-bold text-t-heading shadow-lg shadow-sm shadow-primary/10 transition-all hover:bg-primary-hover hover:scale-[1.02] disabled:opacity-50"
          >
            {loading ? "Registering..." : <><Save className="h-4 w-4" /> Finalize Registration</>}
          </button>
        </div>
      </form>
    </div>
  );
}
