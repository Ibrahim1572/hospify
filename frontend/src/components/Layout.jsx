import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = [
    { name: 'Dashboard', path: '/', roles: ['super_admin', 'doctor', 'nurse', 'receptionist', 'lab_technician', 'pharmacist', 'billing_staff'] },
    { name: 'Patients', path: '/patients', roles: ['super_admin', 'doctor', 'nurse', 'receptionist'] },
    { name: 'Admissions', path: '/admissions', roles: ['super_admin', 'doctor', 'nurse', 'receptionist'] },
    { name: 'Beds', path: '/beds', roles: ['super_admin', 'doctor', 'nurse'] },
    { name: 'Appointments', path: '/appointments', roles: ['super_admin', 'doctor', 'receptionist'] },
    { name: 'Pharmacy', path: '/pharmacy', roles: ['super_admin', 'pharmacist', 'doctor'] },
    { name: 'Lab', path: '/lab', roles: ['super_admin', 'lab_technician', 'doctor'] },
    { name: 'Billing', path: '/billing', roles: ['super_admin', 'billing_staff', 'receptionist'] },
    { name: 'Admin', path: '/admin', roles: ['super_admin'] },
  ];

  const filteredNav = navItems.filter(item => item.roles.includes(user?.role));

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <span className="font-heading font-bold text-xl text-primary-600">Hospify</span>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                {filteredNav.map(item => (
                  <Link
                    key={item.name}
                    to={item.path}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                      location.pathname === item.path || (location.pathname.startsWith(item.path) && item.path !== '/')
                        ? 'border-primary-500 text-slate-900'
                        : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'
                    }`}
                  >
                    {item.name}
                  </Link>
                ))}
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-slate-600">
                <span className="font-medium text-slate-900">{user?.full_name}</span> ({user?.role})
              </div>
              <button
                onClick={logout}
                className="btn-secondary text-sm px-3 py-1.5"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
