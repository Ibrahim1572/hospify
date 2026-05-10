import { useAuth } from '../context/AuthContext';

export default function Dashboard() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-heading font-bold text-slate-900">
        Welcome back, {user?.full_name}!
      </h1>
      <p className="text-slate-600 text-lg">
        You are logged in as <span className="font-semibold text-primary-600">{user?.role}</span>.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <div className="card p-6">
          <h3 className="font-heading font-semibold text-lg text-slate-900">Your Profile</h3>
          <ul className="mt-4 space-y-2 text-sm text-slate-600">
            <li><span className="font-medium text-slate-900">Name:</span> {user?.full_name}</li>
            <li><span className="font-medium text-slate-900">Email:</span> {user?.email}</li>
            <li><span className="font-medium text-slate-900">Role:</span> {user?.role}</li>
          </ul>
        </div>

        {/* Real-time Alerts Placeholder */}
        <div className="card p-6 md:col-span-2 border-l-4 border-l-yellow-400">
          <div className="flex items-center justify-between">
            <h3 className="font-heading font-semibold text-lg text-slate-900">Active Alerts</h3>
            <span className="badge badge-warning">Live</span>
          </div>
          <div className="mt-4 text-sm text-slate-600">
            <p>Real-time Firebase alert sync will appear here.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
