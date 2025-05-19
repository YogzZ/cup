import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

interface UserProfileData {
  username: string;
  email: string | null;
  id: number; // Add id as it's needed for the backend update endpoint (though /me should know it)
  // Add other user profile fields if available from backend, e.g., registration_date, role
}

const UserProfile: React.FC = () => {
  const [user, setUser] = useState<UserProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState({ username: '', email: '' });
  const [updating, setUpdating] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);

  const fetchUserProfile = async () => {
    try {
      const token = localStorage.getItem('userToken'); // Use userToken
      if (!token) {
        setError('Authentication token not available. Please log in.');
        setLoading(false);
        return;
      }

      // Assuming backend has a GET /users/me endpoint
      const response = await fetch('http://localhost:8000/users/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch user profile');
      }

      const data: UserProfileData = await response.json();
      setUser(data);
      setEditFormData({ username: data.username, email: data.email || '' });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUserProfile();
  }, []); // Empty dependency array means this effect runs once after initial render

  const handleEditInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setEditFormData({ ...editFormData, [name]: value });
  };

  const handleUpdateProfile = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setUpdating(true);
    setUpdateError(null);

    try {
      const token = localStorage.getItem('userToken');
      if (!token) {
         setUpdateError('Authentication token not available. Please log in.');
         setUpdating(false);
         return;
       }

      // Backend PUT /users/me endpoint expects UserProfileUpdate model
      const response = await fetch('http://localhost:8000/users/me', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(editFormData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update profile');
      }

      // Profile updated successfully, refresh data and exit editing mode
      fetchUserProfile();
      setIsEditing(false);

    } catch (err: any) {
      setUpdateError(err.message);
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return <div>Loading profile...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!user) {
      return <div>No user data available.</div>;
  }

  return (
    <div>
      <h2>User Profile</h2>

      {!isEditing ? (
        <div>
          <p><strong>Username:</strong> {user.username}</p>
          <p><strong>Email:</strong> {user.email || 'N/A'}</p>
          {/* Display other user info here */}
          <p><Link to="/profile/matches">View Match History</Link></p>
          <button onClick={() => setIsEditing(true)}>Edit Profile</button>
        </div>
      ) : (
        <form onSubmit={handleUpdateProfile}>
          <h3>Edit Profile</h3>
          <div>
            <label htmlFor="edit-username">Username:</label>
            <input
              type="text"
              id="edit-username"
              name="username"
              value={editFormData.username}
              onChange={handleEditInputChange}
              required
            />
          </div>
          <div>
            <label htmlFor="edit-email">Email:</label>
            <input
              type="email"
              id="edit-email"
              name="email"
              value={editFormData.email}
              onChange={handleEditInputChange}
            />
          </div>
          <button type="submit" disabled={updating}>
            {updating ? 'Saving...' : 'Save Changes'}
          </button>
          <button type="button" onClick={() => setIsEditing(false)} disabled={updating}>Cancel</button>
          {updateError && <p style={{ color: 'red' }}>{updateError}</p>}
        </form>
      )}
    </div>
  );
};

export default UserProfile; 