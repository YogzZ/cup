import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

const UserLogin: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Note: The backend /login endpoint expects form data,
      // not JSON for OAuth2PasswordRequestForm.
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const response = await fetch('http://localhost:8000/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await response.json();
      // Assuming the backend returns a JWT token in 'access_token' and a 'role' field
      const token = data.access_token;
      // Assuming backend sends user role, fetch full user details to get role
      // The /login endpoint might not return role directly, fetch /users/me instead
      // Or modify backend /login to return role

      // Let's modify the backend /login to return role for simplicity
      // For now, assuming backend /login *does* return role as per previous comment
      const userRole = data.role; // Assuming backend sends user role

      // Store the user token based on role
      if (userRole === 'organizer') { // Assuming 'organizer' is the admin role
          localStorage.setItem('adminToken', token);
          // Clean up potential old user token
          localStorage.removeItem('userToken');
      } else {
          localStorage.setItem('userToken', token);
          // Clean up potential old admin token
          localStorage.removeItem('adminToken');
      }
      
      // Also store the user role for frontend logic
      localStorage.setItem('userRole', userRole); 

      // Redirect based on user role
      if (userRole === 'organizer') {
          navigate('/admin/events'); // Redirect admin to admin event management
      } else {
          navigate('/events'); // Redirect regular user to events list
      }

    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>User Login</h2>
      <form onSubmit={handleLogin}>
        <div>
          <label htmlFor="user-login-username">Username:</label>
          <input
            type="text"
            id="user-login-username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="user-login-password">Password:</label>
          <input
            type="password"
            id="user-login-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Logging in...' : 'Login'}
        </button>
        {error && <p style={{ color: 'red' }}>{error}</p>}
      </form>
      <p>Don't have an account? <Link to="/register">Register here</Link>.</p>
    </div>
  );
};

export default UserLogin; 