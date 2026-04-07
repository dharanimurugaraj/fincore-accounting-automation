"use client"

import { motion } from "framer-motion"

const AI_PROVIDERS = [
  {
    name: "OpenAI",
    logo: "https://openai.com/favicon.ico",
    models: [
      { name: "GPT-4o-mini", input: "$0.15", output: "$0.60", context: "128,000", released: "Jul 18, 2024" },
      { name: "GPT-4.1 Nano", input: "$0.10", output: "$0.40", context: "1,047,576", released: "Apr 14, 2025" },
      { name: "GPT-5 Nano", input: "$0.05", output: "$0.40", context: "400,000", released: "Aug 7, 2025" },
      { name: "gpt-oss-120b", input: "$0.039", output: "$0.19", context: "131,072", released: "Aug 5, 2025" },
      { name: "gpt-oss-20b", input: "$0.03", output: "$0.11", context: "131,072", released: "Aug 5, 2025" },
    ]
  },
  {
    name: "Anthropic",
    logo: "https://www.anthropic.com/favicon.ico",
    models: [
      { name: "Claude Opus 4.6", input: "$5.00", output: "$25.00", context: "1,000,000", released: "Feb 4, 2026" },
      { name: "Claude Sonnet 4.6", input: "$3.00", output: "$15.00", context: "1,000,000", released: "Feb 17, 2026" },
      { name: "Claude 3.7 Sonnet", input: "$3.00", output: "$15.00", context: "200,000", released: "Feb 25, 2025" },
      { name: "Claude 3.5 Haiku", input: "$0.80", output: "$4.00", context: "200,000", released: "Nov 4, 2024" },
    ]
  },
  {
    name: "Google",
    logo: "https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d47353046b5d92c69469.svg",
    models: [
      { name: "Gemini 1.5 Flash", input: "$0.075", output: "$0.30", context: "1,000,000", released: "May 14, 2024" },
      { name: "Gemini 1.5 Pro", input: "$1.25", output: "$5.00", context: "2,000,000", released: "Apr 9, 2024" },
      { name: "Gemma 3 27B", input: "Free", output: "Free", context: "131,072", released: "Mar 12, 2025" },
    ]
  },
  {
    name: "Meta",
    logo: "https://www.meta.com/favicon.ico",
    models: [
      { name: "Llama 3.3 70B", input: "$0.10", output: "$0.32", context: "131,072", released: "Dec 6, 2024" },
      { name: "Llama 4 Scout", input: "$0.08", output: "$0.30", context: "327,680", released: "Apr 6, 2025" },
      { name: "Llama 3.2 3B", input: "$0.051", output: "$0.34", context: "80,000", released: "Sep 25, 2024" },
    ]
  }
]

export default function AIModelsPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0F] text-white p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-12">
          <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-[#0ABFBC] to-white bg-clip-text text-transparent">
            AI Model Intelligence Hub
          </h1>
          <p className="text-white/40 max-w-2xl">
            Live token rates and context window specifications for all supported AI models in the FinCore pipeline.
          </p>
        </header>

        <div className="grid gap-8">
          {AI_PROVIDERS.map((provider, pIdx) => (
            <motion.section
              key={provider.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: pIdx * 0.1 }}
              className="bg-white/[0.02] border border-white/5 rounded-[2rem] overflow-hidden backdrop-blur-xl"
            >
              <div className="px-8 py-6 border-b border-white/5 flex items-center gap-4 bg-white/5">
                <div className="w-8 h-8 rounded-lg bg-white p-1.5 flex items-center justify-center">
                  <img src={provider.logo} alt={provider.name} className="w-full h-full object-contain" />
                </div>
                <h2 className="text-xl font-bold tracking-tight">{provider.name} Models</h2>
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-[0.2em] text-white/30">
                      <th className="px-8 py-4 font-bold">Model Name</th>
                      <th className="px-8 py-4 font-bold text-center">Input ($/1M)</th>
                      <th className="px-8 py-4 font-bold text-center">Output ($/1M)</th>
                      <th className="px-8 py-4 font-bold text-center">Context</th>
                      <th className="px-8 py-4 font-bold text-right">Released</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {provider.models.map((model, mIdx) => (
                      <tr key={mIdx} className="group hover:bg-[#0ABFBC]/5 transition-colors">
                        <td className="px-8 py-5 text-sm font-semibold text-white/90">{model.name}</td>
                        <td className="px-8 py-5 text-sm text-center font-mono text-[#0ABFBC]">{model.input}</td>
                        <td className="px-8 py-5 text-sm text-center font-mono text-white/70">{model.output}</td>
                        <td className="px-8 py-5 text-sm text-center text-white/40">{model.context}</td>
                        <td className="px-8 py-5 text-sm text-right text-white/20 font-mono">{model.released}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.section>
          ))}
        </div>
      </div>
    </div>
  )
}
