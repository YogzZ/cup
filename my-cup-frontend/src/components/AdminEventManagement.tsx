import React, { useEffect, useState } from 'react';

interface Event {
  id: number;
  name: string;
  description: string | null;
  start_date: string;
  end_date: string | null;
  mode: string; // 'knockout' or 'league'
}

interface NewEvent {
  name: string;
  description: string;
  start_date: string;
  end_date: string;
  mode: string;
}

const AdminEventManagement: React.FC = () => {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newEvent, setNewEvent] = useState<NewEvent>({
    name: '',
    description: '',
    start_date: '',
    end_date: '',
    mode: 'knockout', // Default mode
  });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null); // To track which event is being deleted
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // New state to control form visibility
  const [showCreateForm, setShowCreateForm] = useState(false);

  const fetchEvents = async () => {
    try {
      const token = localStorage.getItem('adminToken');
      if (!token) {
        setError('Authentication token not available. Please log in as admin.');
        setLoading(false);
        return;
      }

      const response = await fetch('http://localhost:8000/events', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch events');
      }

      const data: Event[] = await response.json();
      setEvents(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []); // Empty dependency array means this effect runs once after initial render

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setNewEvent({ ...newEvent, [name]: value });
  };

  const handleCreateEvent = async (e: React.FormEvent<HTMLFormElement>) => {
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

      const response = await fetch('http://localhost:8000/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(newEvent),
      });

      if (!response.ok) {
         const errorData = await response.json();
         throw new Error(errorData.detail || 'Failed to create event');
      }

      // Event created successfully, clear form, hide form and refresh list
      setNewEvent({
        name: '',
        description: '',
        start_date: '',
        end_date: '',
        mode: 'knockout',
      });
      setShowCreateForm(false); // Hide the form
      fetchEvents(); // Refresh the event list

    } catch (err: any) {
      setCreateError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteEvent = async (eventId: number) => {
      setDeleting(eventId);
      setDeleteError(null);

      try {
        const token = localStorage.getItem('adminToken');
        if (!token) {
            setDeleteError('Authentication token not available. Please log in as admin.');
            setDeleting(null);
            return;
        }

        const response = await fetch(`http://localhost:8000/events/${eventId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to delete event');
        }

        // Event deleted successfully, refresh the list
        fetchEvents();

      } catch (err: any) {
          setDeleteError(err.message);
      } finally {
          setDeleting(null);
      }
  };


  if (loading) {
    return <div>Loading events...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div className="admin-event-management-container">
      <h2>Admin Event Management</h2>

      {/* Conditional rendering based on showCreateForm state */}
      {showCreateForm ? (
        /* Create Event Form View */
        <div>
          <h3>Create New Event</h3>
          <form onSubmit={handleCreateEvent}>
            <div>
              <label htmlFor="name">Name:</label>
              <input
                type="text"
                id="name"
                name="name"
                value={newEvent.name}
                onChange={handleInputChange}
                required
              />
            </div>
            <div>
              <label htmlFor="description">Description:</label>
              <input
                type="text"
                id="description"
                name="description"
                value={newEvent.description}
                onChange={handleInputChange}
              />
            </div>
            <div>
              <label htmlFor="start_date">Start Date:</label>
              <input
                type="date"
                id="start_date"
                name="start_date"
                value={newEvent.start_date}
                onChange={handleInputChange}
                required
              />
            </div>
            <div>
              <label htmlFor="end_date">End Date:</label>
              <input
                type="date"
                id="end_date"
                name="end_date"
                value={newEvent.end_date}
                onChange={handleInputChange}
              />
            </div>
            <div>
              <label htmlFor="mode">Mode:</label>
              <select
                id="mode"
                name="mode"
                value={newEvent.mode}
                onChange={handleInputChange}
                required
              >
                <option value="knockout">Knockout</option>
                <option value="league">League</option>
              </select>
            </div>
            <button type="submit" disabled={creating}>
              {creating ? 'Creating...' : 'Create Event'}
            </button>
            {/* Cancel Button */}
            <button type="button" onClick={() => setShowCreateForm(false)} disabled={creating}>
              Cancel
            </button>
            {createError && <p style={{ color: 'red' }}>{createError}</p>}
          </form>
        </div>
      ) : (
        /* Event List View */
        <div>
          <h3>Event List</h3>
          {/* New Create Event Button */}
          <button onClick={() => setShowCreateForm(true)}>Create New Event</button>
          {deleteError && <p style={{ color: 'red' }}>{deleteError}</p>}
          {events.length === 0 ? (
            <p>No events found.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Description</th>
                  <th>Start Date</th>
                  <th>End Date</th>
                  <th>Mode</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id}>
                    <td>{event.id}</td>
                    <td>{event.name}</td>
                    <td>{event.description || 'N/A'}</td>
                    <td>{event.start_date}</td>
                    <td>{event.end_date || 'N/A'}</td>
                    <td>{event.mode}</td>
                    <td>
                      <button onClick={() => handleDeleteEvent(event.id)} disabled={deleting === event.id}>
                        {deleting === event.id ? 'Deleting...' : 'Delete'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
};

export default AdminEventManagement; 