import { useState, useEffect } from 'react';
import { collection, onSnapshot } from 'firebase/firestore';
import api from '../api/axios';
import { db } from '../firebase';

export default function Beds() {
  const [wards, setWards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchWards();

    const unsubscribe = onSnapshot(collection(db, 'beds'), (snapshot) => {
      snapshot.docChanges().forEach((change) => {
        if (change.type === 'modified' || change.type === 'added') {
          const bedData = change.doc.data();
          setWards(prevWards => prevWards.map(ward => ({
            ...ward,
            beds: ward.beds.map(bed => 
              bed.bed_id === bedData.bed_id 
                ? { ...bed, status: bedData.status } 
                : bed
            )
          })));
        }
      });
    }, (err) => {
      console.error("Firebase real-time listener error:", err);
    });

    return () => unsubscribe();
  }, []);

  const fetchWards = async () => {
    try {
      setLoading(true);
      const res = await api.get('/wards');
      setWards(res.data);
      setError(null);
    } catch (err) {
      setError('Failed to load beds. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'available': return 'bg-green-100 text-green-800 border-green-200';
      case 'occupied': return 'bg-red-100 text-red-800 border-red-200';
      case 'maintenance': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default: return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-heading font-bold text-slate-900">Bed Availability</h1>
        <div className="flex space-x-2">
          <span className="badge bg-green-100 text-green-800 px-3 py-1">Available</span>
          <span className="badge bg-red-100 text-red-800 px-3 py-1">Occupied</span>
          <span className="badge bg-yellow-100 text-yellow-800 px-3 py-1">Maintenance</span>
        </div>
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
        <div className="space-y-8">
          {wards.map((ward) => (
            <div key={ward.ward_id} className="card p-6">
              <div className="flex justify-between items-end border-b border-slate-100 pb-4 mb-4">
                <div>
                  <h2 className="text-xl font-heading font-bold text-slate-900">{ward.ward_name}</h2>
                  <p className="text-sm text-slate-500 capitalize">Floor {ward.floor_number} • {ward.ward_type} Ward</p>
                </div>
                <div className="text-right">
                  <div className="text-sm text-slate-500">Occupancy</div>
                  <div className="font-semibold text-slate-900">
                    {ward.beds.filter(b => b.status === 'occupied').length} / {ward.beds.length}
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-4">
                {ward.beds.map(bed => (
                  <div 
                    key={bed.bed_id} 
                    className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-transform hover:scale-105 cursor-pointer ${getStatusColor(bed.status)}`}
                  >
                    <svg className="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>
                    <span className="font-bold font-heading">{bed.bed_number}</span>
                    <span className="text-xs mt-1 uppercase tracking-wider font-semibold opacity-80">{bed.status}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
