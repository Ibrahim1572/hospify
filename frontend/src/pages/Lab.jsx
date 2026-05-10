import { useState, useEffect } from 'react';
import api from '../api/axios';

export default function Lab() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const res = await api.get('/lab/orders/all');
      setOrders(res.data);
      setError(null);
    } catch (err) {
      setError('Failed to load lab orders.');
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'stat': return 'text-red-700 bg-red-100 border-red-200';
      case 'urgent': return 'text-orange-700 bg-orange-100 border-orange-200';
      default: return 'text-blue-700 bg-blue-100 border-blue-200';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-heading font-bold text-slate-900">Laboratory Orders</h1>
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {orders.length === 0 ? (
            <div className="col-span-full card p-8 text-center text-slate-500">
              No lab orders found.
            </div>
          ) : (
            orders.map((order) => (
              <div key={order.order_id} className="card flex flex-col">
                <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                  <div className="font-semibold text-slate-900 uppercase tracking-wide text-sm">{order.test_name}</div>
                  <span className={`px-2 py-1 text-xs font-bold uppercase rounded border ${getPriorityColor(order.priority)}`}>
                    {order.priority}
                  </span>
                </div>
                <div className="p-4 flex-1">
                  <div className="mb-4">
                    <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Patient</p>
                    <p className="text-sm font-medium text-slate-900">{order.patient_name}</p>
                    <p className="text-xs text-slate-500">Admitted in: {order.ward_name}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Ordered By</p>
                    <p className="text-sm text-slate-800">{order.doctor_name}</p>
                    <p className="text-xs text-slate-500">{new Date(order.ordered_at).toLocaleString()}</p>
                  </div>
                </div>
                <div className="p-4 bg-slate-50 border-t border-slate-100 flex justify-between items-center">
                  <span className={`badge ${order.status === 'completed' ? 'badge-success' : 'badge-warning'}`}>
                    {order.status}
                  </span>
                  {order.status === 'pending' ? (
                    <button className="btn-primary py-1.5 px-3 text-sm">Enter Results</button>
                  ) : (
                    <button className="btn-secondary py-1.5 px-3 text-sm">View Report</button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
