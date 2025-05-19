import React, { useEffect, useState } from 'react';

interface User {
  id: number;
  username: string;
  email: string | null;
  registration_date: string;
  role: string;
}

const AdminUserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newUser, setNewUser] = useState({ username: '', password: '', email: '' });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null); // To track which user is being deleted
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('adminToken');
      if (!token) {
        setError('Authentication token not available. Please log in as admin.');
        setLoading(false);
        return;
      }

      const response = await fetch('http://localhost:8000/users', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch users');
      }

      const data: User[] = await response.json();
      setUsers(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []); // Empty dependency array means this effect runs once after initial render

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setNewUser({ ...newUser, [name]: value });
  };

  const handleCreateUser = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);

    try {
      const token = localStorage.getItem('adminToken');
       if (!token) {
          setCreateError('Authentication token not available. Please log in as admin.');
          setCreating(false);
          return;
        }

      const response = await fetch('http://localhost:8000/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(newUser),
      });

      if (!response.ok) {
         const errorData = await response.json();
         throw new Error(errorData.detail || 'Failed to create user');
      }

      // User created successfully, clear form and refresh list
      setNewUser({ username: '', password: '', email: '' });
      fetchUsers(); // Refresh the user list

    } catch (err: any) {
      setCreateError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteUser = async (userId: number) => {
      setDeleting(userId);
      setDeleteError(null);

      try {
        const token = localStorage.getItem('adminToken');
        if (!token) {
            setDeleteError('Authentication token not available. Please log in as admin.');
            setDeleting(null);
            return;
        }

        const response = await fetch(`http://localhost:8000/users/${userId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to delete user');
        }

        // User deleted successfully, refresh the list
        fetchUsers();

      } catch (err: any) {
          setDeleteError(err.message);
      } finally {
          setDeleting(null);
      }
  };


  if (loading) {
    return <div>Loading users...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div className="admin-user-management-container">
      <h2>Admin User Management</h2>

      <h3>Create New User</h3>
      <form onSubmit={handleCreateUser}>
        <div>
          <label htmlFor="username">Username:</label>
          <input
            type="text"
            id="username"
            name="username"
            value={newUser.username}
            onChange={handleInputChange}
            required
          />
        </div>
        <div>
          <label htmlFor="password">Password:</label>
          <input
            type="password"
            id="password"
            name="password"
            value={newUser.password}
            onChange={handleInputChange}
            required
          />
        </div>
        <div>
          <label htmlFor="email">Email:</label>
          <input
            type="email"
            id="email"
            name="email"
            value={newUser.email}
            onChange={handleInputChange}
          />
        </div>
        <button type="submit" disabled={creating}>
          {creating ? 'Creating...' : 'Create User'}
        </button>
        {createError && <p style={{ color: 'red' }}>{createError}</p>}
      </form>

      <h3>Existing Users</h3>
      {deleteError && <p style={{ color: 'red' }}>{deleteError}</p>}
      {users.length === 0 ? (
        <p>No users found.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Registration Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.id}</td>
                <td>{user.username}</td>
                <td>{user.email || 'N/A'}</td>
                <td>{user.role}</td>
                <td>{new Date(user.registration_date).toLocaleDateString()}</td>
                <td>
                  {/* Action buttons (Edit, Delete) */}
                  <button disabled>Edit</button>
                  <button onClick={() => handleDeleteUser(user.id)} disabled={deleting === user.id}>
                    {deleting === user.id ? 'Deleting...' : 'Delete'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default AdminUserManagement; 