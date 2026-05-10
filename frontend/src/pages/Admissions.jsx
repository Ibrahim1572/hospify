import { useState, useEffect } from 'react';
import api from '../api/axios';

export default function Admissions() {
  const [admissions, setAdmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAdmissions();
  }, []);

  const fetchAdmissions = async () => {
    try {
      setLoading(true);
      const res = await api.get('/admissions');
      // Only show active admissions by default
      setAdmissions(res.data.filter(a => a.status === 'active'));
      setError(null);
    } catch (err) {
      setError('Failed to load admissions. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const handleDischarge = async (admissionId) => {
    if (!window.confirm("Are you sure you want to discharge this patient? This will generate a final bill and free the bed.")) return;
    
    try {
      await api.post(`/admissions/${admissionId}/discharge`);
      // Refresh list
      fetchAdmissions();
    } catch (err) {
      alert(err.response?.data?.error || "Failed to discharge patient");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-heading font-bold text-slate-900">Active Admissions</h1>
        <button className="btn-primary">
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
          New Admission
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-xl border border-red-200">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {admissions.length === 0 ? (
            <div className="col-span-full card p-8 text-center text-slate-500">
              No active admissions found.
            </div>
          ) : (
            admissions.map((admission) => (
              <div key={admission.admission_id} className="card p-6 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-heading font-bold text-slate-900">{admission.patient_name}</h3>
                      <p className="text-sm text-slate-500">Admitted: {new Date(admission.admitted_at).toLocaleString()}</p>
                    </div>
                    <span className="badge badge-info uppercase">
                      {admission.admission_type}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mt-4 bg-slate-50 rounded-lg p-4">
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Doctor in Charge</p>
                      <p className="text-sm font-medium text-slate-800 mt-1">{admission.doctor_name}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Bed Assignment</p>
                      <p className="text-sm font-medium text-slate-800 mt-1">Ward {admission.ward_id} • Bed {admission.bed_number}</p>
                    </div>
                  </div>
                </div>
                
                <div className="mt-6 flex justify-end space-x-3 pt-4 border-t border-slate-100">
                  <button className="btn-secondary text-sm">Vitals</button>
                  <button className="btn-secondary text-sm">Prescriptions</button>
                  <button 
                    onClick={() => handleDischarge(admission.admission_id)}
                    className="inline-flex items-center justify-center px-4 py-2 bg-red-50 text-red-700 border border-red-200 rounded-lg font-medium shadow-sm hover:bg-red-100 focus:outline-none transition-colors duration-200 text-sm"
                  >
                    Discharge Patient
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
