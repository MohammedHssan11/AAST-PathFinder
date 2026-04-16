import { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings, Save, X, Edit2, ShieldAlert, Loader2 } from 'lucide-react';

interface Program {
  id: string;
  program_name: string;
  college_id: string;
  min_percentage: number | null;
  program_fees: number | null;
  allowed_tracks: string | null;
}

export default function AdminDashboardPage() {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingProgram, setEditingProgram] = useState<Program | null>(null);
  const [editForm, setEditForm] = useState<{ min_percentage: number | '', program_fees: number | '', allowed_tracks: string }>({ min_percentage: '', program_fees: '', allowed_tracks: '' });
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchPrograms();
  }, []);

  const fetchPrograms = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/v1/admin/programs');
      setPrograms(response.data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch programs. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (program: Program) => {
    setEditingProgram(program);
    setEditForm({
      min_percentage: program.min_percentage ?? '',
      program_fees: program.program_fees ?? '',
      allowed_tracks: program.allowed_tracks ?? ''
    });
  };

  const handleCancel = () => {
    setEditingProgram(null);
    setError(null);
  };

  const handleSave = async () => {
    if (!editingProgram) return;
    
    const minP = editForm.min_percentage === '' ? null : Number(editForm.min_percentage);
    
    // Percentage Validation
    if (minP !== null && (minP < 0 || minP > 100)) {
        setError('Minimum percentage must be between 0 and 100.');
        return;
    }

    setIsSaving(true);
    setError(null);
    
    try {
      await axios.put(`http://localhost:8000/api/v1/admin/programs/${editingProgram.id}`, {
        min_percentage: minP,
        program_fees: editForm.program_fees === '' ? null : Number(editForm.program_fees),
        allowed_tracks: editForm.allowed_tracks === '' ? null : editForm.allowed_tracks
      });
      setEditingProgram(null);
      fetchPrograms();
    } catch (err) {
      console.error(err);
      setError('Failed to update program constraints.');
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-slate-500 gap-3">
         <Loader2 className="animate-spin text-[rgb(20,41,82)]" size={32} />
         <span>Loading configurations...</span>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-8 bg-slate-50 relative">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <Settings className="text-[rgb(20,41,82)]" />
              Gatekeeper Administration
            </h1>
            <p className="text-slate-500 mt-1">Configure hard eligibility constraints and fees for all programs.</p>
          </div>
        </div>

        {error && !editingProgram && (
          <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center gap-3">
            <ShieldAlert size={20} />
            {error}
          </div>
        )}

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Program Name</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">College ID</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Min %</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Program Fees</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Allowed Tracks</th>
                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {programs.map((program) => (
                <tr key={program.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">{program.program_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{program.college_id}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                    {program.min_percentage !== null ? <span className="font-semibold text-slate-800">{program.min_percentage.toFixed(2)}%</span> : <span className="text-slate-400 italic">None</span>}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                    {program.program_fees !== null ? <span className="font-semibold text-slate-800">${program.program_fees.toFixed(2)}</span> : <span className="text-slate-400 italic">None</span>}
                  </td>
                  <td className="px-6 py-4 whitespace-normal text-sm text-slate-500">
                    {program.allowed_tracks ? <code className="bg-slate-100 px-2 py-1 rounded border border-slate-200 text-xs text-slate-700">{program.allowed_tracks}</code> : <span className="text-slate-400 italic">All Allowed</span>}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button onClick={() => handleEdit(program)} className="text-indigo-600 hover:text-indigo-900 inline-flex items-center gap-1">
                      <Edit2 size={16} /> Edit
                    </button>
                  </td>
                </tr>
              ))}
              {programs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-500">No programs found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {editingProgram && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden flex flex-col max-h-full">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-semibold text-lg text-slate-900">Edit Gatekeeper Rules</h3>
              <button onClick={handleCancel} className="text-slate-400 hover:text-slate-600 transition-colors">
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 space-y-5 overflow-y-auto">
              {error && (
                <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm flex items-center gap-2">
                  <ShieldAlert size={16} />
                  {error}
                </div>
              )}
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Minimum Percentage (%)</label>
                <input 
                  type="number" 
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[rgb(20,41,82)]/50 focus:border-[rgb(20,41,82)]"
                  value={editForm.min_percentage}
                  onChange={e => setEditForm({...editForm, min_percentage: e.target.value ? Number(e.target.value) : ''})}
                  placeholder="Enter a value (0-100)"
                  min="0"
                  max="100"
                  step="0.1"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Program Fees</label>
                <input 
                  type="number" 
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[rgb(20,41,82)]/50 focus:border-[rgb(20,41,82)]"
                  value={editForm.program_fees}
                  onChange={e => setEditForm({...editForm, program_fees: e.target.value ? Number(e.target.value) : ''})}
                  placeholder="Enter exact override fee"
                  min="0"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Allowed Tracks</label>
                <input 
                  type="text" 
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[rgb(20,41,82)]/50 focus:border-[rgb(20,41,82)]"
                  value={editForm.allowed_tracks}
                  onChange={e => setEditForm({...editForm, allowed_tracks: e.target.value})}
                  placeholder="e.g. ['science', 'math']"
                />
              </div>
            </div>
            
            <div className="px-6 py-4 border-t border-slate-100 flex justify-end gap-3 bg-slate-50 shrink-0">
              <button 
                onClick={handleCancel} 
                disabled={isSaving}
                className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button 
                onClick={handleSave} 
                disabled={isSaving} 
                className="px-5 py-2 text-sm font-medium text-white bg-[rgb(20,41,82)] hover:bg-[rgb(30,55,100)] rounded-lg transition-colors flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed shadow-sm"
              >
                {isSaving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
