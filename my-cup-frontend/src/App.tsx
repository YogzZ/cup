import './App.css';
import { Routes, Route, Link, Navigate } from 'react-router-dom';
import AdminUserManagement from './components/AdminUserManagement';
// import AdminLogin from './components/AdminLogin'; // Comment out or remove AdminLogin import
import AdminEventManagement from './components/AdminEventManagement';
import ProtectedRoute from './components/ProtectedRoute';
import UserRegister from './components/UserRegister';
import UserLogin from './components/UserLogin'; // Import UserLogin
import UserProfile from './components/UserProfile'; // Import UserProfile
import UserEventList from './components/UserEventList'; // Import UserEventList
import EventDetail from './components/EventDetail'; // Import EventDetail
import UserMatchHistory from './components/UserMatchHistory'; // Import UserMatchHistory
import { useState, useEffect } from 'react';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('userToken'));

  useEffect(() => {
    // Listen for changes in localStorage to update login status
    const handleStorageChange = () => {
      setIsLoggedIn(!!localStorage.getItem('userToken'));
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  return (
    <>
      <nav>
        <ul>
          <li>
            <Link to="/">Home</Link>
          </li>
          {/* Conditionally render Login/Register or Profile link */}
          {isLoggedIn ? (
            <li>
              <Link to="/profile">Profile</Link>
            </li>
          ) : (
            <>
              <li>
                <Link to="/login">Login</Link>
              </li>
              <li>
                <Link to="/register">Register</Link>
              </li>
            </>
          )}
          <li>
            <Link to="/events">Events</Link>
          </li>
          {/* These links will eventually be only for admins */}
          <li>
            <Link to="/admin/users">Admin Users</Link>
          </li>
          <li>
            <Link to="/admin/events">Admin Events</Link>
          </li>
        </ul>
      </nav>

      <Routes>
        <Route path="/" element={<UserLogin />} /> {/* Set UserLogin as the home page */}
        {/* <Route path="/" element={<UserEventList />} /> Set UserEventList as the home page */}
        <Route path="/register" element={<UserRegister />} />
        <Route path="/events" element={<UserEventList />} /> {/* Add events route */}
        <Route path="/events/:eventId" element={<EventDetail />} /> {/* Add event detail route */}

        {/* Protected Routes (for both users and admins for now) */}
        <Route element={<ProtectedRoute />}> {/* Use ProtectedRoute here */}
          <Route path="profile" element={<UserProfile />} /> {/* User Profile Route */}
          <Route path="admin/users" element={<AdminUserManagement />} /> {/* Admin user route */}
          <Route path="admin/events" element={<AdminEventManagement />} /> {/* Admin event route */}
          <Route path="profile/matches" element={<UserMatchHistory />} /> {/* User Match History Route */}
        </Route>

        {/* Add a catch-all route for 404 or redirect to home */}
        <Route path="*" element={<Navigate to="/" replace />} />

      </Routes>
    </>
  );
}

export default App;
