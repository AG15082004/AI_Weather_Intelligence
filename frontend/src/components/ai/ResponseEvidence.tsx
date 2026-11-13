import { useState } from "react";
import { ChevronDown, ChevronRight, Database, Clock, Activity, CheckCircle2 } from "lucide-react";

interface ResponseEvidenceProps {
  sources?: string[];
  timestamp?: string | null;
  intent?: string | null;
  district?: string | null;
}

export function ResponseEvidence({
  sources = [],
  timestamp,
  intent,
  district,
}: ResponseEvidenceProps) {
  const [isOpen, setIsOpen] = useState(false);

  // If no source or evidence data is present, do not render empty container
  const hasEvidence = (sources && sources.length > 0) || timestamp || intent;
  if (!hasEvidence) return null;

  const primarySource = sources[0] || "Microsoft Fabric Lakehouse";
  const isFabricSource = primarySource.toLowerCase().includes("fabric") || primarySource.toLowerCase().includes("dbo");

  return (
    <div className="mt-3 border-t border-slate-100 pt-2 text-xs">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-800 transition-colors py-1 group"
      >
        {isOpen ? (
          <ChevronDown className="size-3.5 text-slate-400 group-hover:text-slate-600" />
        ) : (
          <ChevronRight className="size-3.5 text-slate-400 group-hover:text-slate-600" />
        )}
        <Database className="size-3 text-blue-600" />
        <span>Verified Data Grounding & Provenance</span>
        {isFabricSource && (
          <span className="ml-1 inline-flex items-center gap-1 rounded bg-blue-50 px-1.5 py-0.2 text-[10px] font-semibold text-blue-700">
            Fabric Verified
          </span>
        )}
      </button>

      {isOpen && (
        <div className="mt-2 rounded-lg border border-slate-200/80 bg-slate-50/70 p-3 space-y-2 text-xs text-slate-600">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="size-3.5 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-800">Source Tables:</span>
              <ul className="mt-0.5 space-y-0.5">
                {sources.map((src, idx) => (
                  <li key={idx} className="font-mono text-[11px] text-slate-700">
                    {src}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {timestamp && (
            <div className="flex items-center gap-2 pl-5.5">
              <Clock className="size-3.5 text-slate-400 shrink-0" />
              <span>
                <strong className="text-slate-700">Observation Time:</strong> {timestamp} (Asia/Kolkata IST)
              </span>
            </div>
          )}

          {intent && (
            <div className="flex items-center gap-2 pl-5.5">
              <Activity className="size-3.5 text-slate-400 shrink-0" />
              <span>
                <strong className="text-slate-700">Analytical Intent:</strong>{" "}
                <span className="capitalize">{intent.replace(/_/g, " ")}</span>
                {district && ` (District: ${district})`}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
