import { useState } from 'react';
import { ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis,  ResponsiveContainer } from 'recharts';

export interface CollegeCardProps {
  programName: string;
  collegeName: string;
  matchScore: number;
  matchType: string;
  confidence: string;
  fee: number | null;
  currency: string;
  feeMode: string;
  affordability: string;
  scoreBreakdown: any;
  warnings?: string[];
}

export default function CollegeCard({
  programName,
  collegeName,
  matchScore,
  matchType,
  confidence,
  fee,
  currency,
  feeMode,
  affordability,
  scoreBreakdown,
  warnings = []
}: CollegeCardProps) {
  const [expanded, setExpanded] = useState(false);

  // Parse breakdown for the radar chart
  const radarData = [
    { subject: 'Interest', A: scoreBreakdown.interest_alignment || 0, fullMark: 100 },
    { subject: 'Affordability', A: scoreBreakdown.affordability || 0, fullMark: 100 },
    { subject: 'Employment', A: scoreBreakdown.employment_outlook || 0, fullMark: 100 },
    { subject: 'Location', A: scoreBreakdown.location_preference || 0, fullMark: 100 },
    { subject: 'Flexibility', A: scoreBreakdown.career_flexibility || 0, fullMark: 100 },
    { subject: 'Admission', A: scoreBreakdown.certificate_compatibility || 0, fullMark: 100 },
  ];

  // Circle color mapping
  const strokeColor = matchScore >= 80 ? '#16a34a' : matchScore >= 60 ? '#eab308' : '#ef4444';
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (matchScore / 100) * circumference;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col transition-all hover:shadow-md">
      <div className="p-5 flex gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
              matchType === 'Exact' ? 'bg-green-100 text-green-700' :
              matchType === 'Stretch' ? 'bg-yellow-100 text-yellow-700' :
              matchType === 'Partial' ? 'bg-blue-100 text-blue-700' :
              'bg-slate-100 text-slate-600'
            }`}>
              {matchType} Match
            </span>
            {confidence === 'High' && <span className="text-[10px] bg-aast-navy/10 text-aast-navy font-bold px-2 py-0.5 rounded-full">High Confidence</span>}
          </div>
          <h3 className="font-bold text-lg text-slate-800 leading-tight mb-1">{programName}</h3>
          <p className="text-sm text-slate-500 leading-snug">{collegeName}</p>
        </div>

        {/* Circular Score Indicator */}
        <div className="relative flex items-center justify-center w-16 h-16 shrink-0">
          <svg className="transform -rotate-90 w-16 h-16">
            <circle cx="32" cy="32" r={radius} stroke="currentColor" strokeWidth="6" fill="transparent" className="text-slate-100" />
            <circle cx="32" cy="32" r={radius} stroke={strokeColor} strokeWidth="6" fill="transparent" strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} className="transition-all duration-1000 ease-out" />
          </svg>
          <span className="absolute text-sm font-bold text-slate-700">{Math.round(matchScore)}</span>
        </div>
      </div>

      <div className="px-5 pb-4">
        <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-sm">
          <div className="flex justify-between items-center mb-1">
            <span className="text-slate-500">Estimated Tuition</span>
            <span className={`font-semibold ${
              affordability === 'match' ? 'text-green-600' :
              affordability === 'stretch' ? 'text-orange-500' : 'text-red-500'
            }`}>
              {affordability.toUpperCase()}
            </span>
          </div>
          <div className="font-medium text-slate-800">
            {fee ? `${fee.toLocaleString()} ${currency} / ${feeMode}` : 'Tuition Unavailable'}
          </div>
        </div>
      </div>

      {warnings.length > 0 && (
        <div className="px-5 pb-4">
          <div className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 p-2 rounded border border-amber-200">
            <AlertTriangle size={14} className="shrink-0 mt-0.5" />
            <div>
              {warnings[0]}
              {warnings.length > 1 && ` (+${warnings.length - 1} more)`}
            </div>
          </div>
        </div>
      )}

      {/* Expandable Breakdown */}
      <div className="mt-auto border-t border-slate-100">
        <button 
          onClick={() => setExpanded(!expanded)}
          className="w-full py-2 px-5 flex items-center justify-between text-xs font-medium text-slate-500 hover:bg-slate-50 transition-colors"
        >
          <span>Score Breakdown</span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        
        {expanded && (
          <div className="px-5 pb-5 pt-2 bg-slate-50 border-t border-slate-100 shadow-inner">
            <div className="h-40 w-full font-sans text-[10px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} margin={{ top: 5, right: 15, bottom: 5, left: 15 }}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 10 }} />
                  <Radar name="Score" dataKey="A" stroke="#1e3a8a" fill="#1e3a8a" fillOpacity={0.2} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2 text-xs">
              <div className="flex justify-between"><span className="text-slate-500">Completeness</span><span className="font-medium">{scoreBreakdown.decision_data_completeness}%</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Penalty</span><span className="font-medium text-red-500">-{scoreBreakdown.missing_data_penalty}%</span></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
