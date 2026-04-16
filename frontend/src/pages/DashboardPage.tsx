import { useState, useEffect } from 'react';
import axios from 'axios';
import { useStudent } from '../context/StudentContext';
import DecisionForm from '../components/DecisionForm';
import CollegeCard from '../components/CollegeCard';
import { Loader2 } from 'lucide-react';

const API_URL = "http://localhost:8000/api/v1/decisions/recommend";

export default function DashboardPage() {
  const { profile } = useStudent();
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Only fetch if we have minimum requirements, or we can just fetch immediately with defaults.
    // Let's debounce the fetch or do it automatically.
    const fetchRecommendations = async () => {
      setLoading(true);
      setError(null);

      try {
        const payload = {
          certificate_type: profile.certificate_type || null,
          high_school_percentage: profile.high_school_percentage || null,
          student_group: profile.student_group,
          budget: profile.budget || null,
          preferred_branch: profile.preferred_branch || null,
          preferred_city: profile.preferred_city || null,
          interests: profile.interests,
          track_type: profile.track_type,
          max_results: 10,
          min_results: 3,
        };

        const response = await axios.post(API_URL, payload);
        setRecommendations(response.data.recommendations || []);
      } catch (err: any) {
        console.error(err);
        setError(err.response?.data?.detail || "Failed to fetch recommendations. Make sure FastAPI backend is running.");
      } finally {
        setLoading(false);
      }
    };

    const debounce = setTimeout(() => {
      fetchRecommendations();
    }, 500);

    return () => clearTimeout(debounce);
  }, [profile]);

  return (
    <div className="flex h-full w-full">
      <aside className="w-[340px] h-full border-r border-slate-200 bg-white shadow-sm flex flex-col z-0 shrink-0">
        <div className="p-6 flex-1 overflow-y-auto w-full">
          <h2 className="text-lg font-bold text-aast-navy mb-6">Decision Inputs</h2>
          <DecisionForm />
        </div>
      </aside>

      <section className="flex-1 h-full bg-slate-50 flex flex-col overflow-y-auto">
        <div className="p-8 max-w-7xl mx-auto w-full">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-slate-800">Program Recommendations</h2>
            {loading && (
              <div className="flex items-center gap-2 text-aast-navy text-sm font-medium">
                <Loader2 className="animate-spin" size={16} />
                Updating Results...
              </div>
            )}
          </div>

          {error && (
            <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-6 border border-red-200">
              {error}
            </div>
          )}

          {!loading && !error && recommendations.length === 0 && (
            <div className="bg-white p-12 rounded-xl border border-slate-200 shadow-sm text-center text-slate-500 flex flex-col items-center">
              <span className="text-4xl mb-4">🔍</span>
              <p className="text-lg">No recommendations found matching your current strict criteria.</p>
              <p className="text-sm mt-2 max-w-md">Try relaxing your budget, adding more interests, or removing location constraints.</p>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6 pb-12">
            {recommendations.map((rec, idx) => (
              <CollegeCard
                key={`${rec.program_id}-${idx}`}
                programName={rec.program_name}
                collegeName={rec.college_name}
                matchScore={rec.score}
                matchType={rec.match_type}
                confidence={rec.confidence_level}
                fee={rec.estimated_semester_fee}
                currency={rec.currency}
                feeMode={rec.fee_mode}
                affordability={rec.affordability_label}
                scoreBreakdown={rec.score_breakdown}
                warnings={rec.warnings || []}
              />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
