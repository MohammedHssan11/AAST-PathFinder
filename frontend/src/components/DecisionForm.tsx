import { useStudent } from '../context/StudentContext';

const CERTIFICATE_TYPES = [
  "Egyptian Thanaweya Amma (Science)",
  "Egyptian Thanaweya Amma (Math)",
  "Egyptian Thanaweya Amma (Literature)",
  "IGCSE",
  "American Diploma",
  "Other"
];

const INTERESTS = [
  "AI", "Software", "Hardware", "Robotics", "Business", "Management", "Logistics", "Maritime"
];

export default function DecisionForm() {
  const { profile, updateProfile } = useStudent();

  const handleInterestToggle = (interest: string) => {
    const current = new Set(profile.interests);
    if (current.has(interest)) current.delete(interest);
    else current.add(interest);
    updateProfile({ interests: Array.from(current) });
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Budget */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">
          Max Semester Budget (USD)
        </label>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="0" max="20000" step="500"
            value={profile.budget || 0}
            onChange={e => updateProfile({ budget: Number(e.target.value) || null })}
            className="flex-1 accent-aast-navy"
          />
          <span className="text-sm font-semibold text-aast-navy w-16 text-right">
            {profile.budget ? `$${profile.budget}` : 'Any'}
          </span>
        </div>
      </div>

      {/* Certificate Type */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">Certificate</label>
        <select
          className="w-full bg-slate-50 border border-slate-200 text-slate-700 rounded-md p-2 text-sm focus:ring-aast-navy focus:border-aast-navy outline-none"
          value={profile.certificate_type}
          onChange={e => updateProfile({ certificate_type: e.target.value as any })}
        >
          <option value="">Select Certificate</option>
          {CERTIFICATE_TYPES.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* High School Percentage */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">Grade Percentage</label>
        <input
          type="number" min="0" max="100" step="0.1"
          placeholder="e.g. 85.5"
          value={profile.high_school_percentage || ''}
          onChange={e => updateProfile({ high_school_percentage: parseFloat(e.target.value) || null })}
          className="w-full bg-slate-50 border border-slate-200 text-slate-700 rounded-md p-2 text-sm focus:ring-aast-navy focus:border-aast-navy outline-none"
        />
      </div>

      {/* Interests */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">Interests</label>
        <div className="flex flex-wrap gap-2">
          {INTERESTS.map(interest => {
            const isSelected = profile.interests.includes(interest);
            return (
              <button
                key={interest}
                onClick={() => handleInterestToggle(interest)}
                className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${isSelected
                  ? 'bg-aast-navy text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
              >
                {interest}
              </button>
            );
          })}
        </div>
      </div>

      {/* Student Group Toggle */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">Student Group</label>
        <div className="flex bg-slate-100 p-1 rounded-lg">
          <button
            className={`flex-1 py-1 text-sm font-medium rounded-md transition-colors ${profile.student_group === 'supportive_states' ? 'bg-white shadow text-aast-navy' : 'text-slate-500 hover:text-slate-700'
              }`}
            onClick={() => updateProfile({ student_group: 'supportive_states' })}
          >
            Supportive States
          </button>
          <button
            className={`flex-1 py-1 text-sm font-medium rounded-md transition-colors ${profile.student_group === 'other_states' ? 'bg-white shadow text-aast-navy' : 'text-slate-500 hover:text-slate-700'
              }`}
            onClick={() => updateProfile({ student_group: 'other_states' })}
          >
            Other States
          </button>
        </div>
      </div>
    </div>
  );
}
