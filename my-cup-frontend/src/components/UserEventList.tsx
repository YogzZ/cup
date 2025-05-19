import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

interface Event {
  id: number;
  name: string;
  description: string | null;
  start_date: string;
  end_date: string | null;
  mode: string; // 'knockout' or 'league'
}

const UserEventList: React.FC = () => {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredEvents, setFilteredEvents] = useState<Event[]>([]);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        // Ordinary users can also view events, authentication might be optional or different
        // For now, we assume the /events endpoint is accessible to logged-in users (with userToken)
        const token = localStorage.getItem('userToken'); // Use userToken
        // Note: Backend /events endpoint might require authentication, even for viewing
        // If so, the token should be included in the headers.

        const response = await fetch('http://localhost:8000/events', {
           // Add headers with token if backend /events requires authentication for viewing
           headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch events');
        }

        const data: Event[] = await response.json();
        setEvents(data);
        setFilteredEvents(data); // Initialize filteredEvents with all events
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
  }, []); // Empty dependency array means this effect runs once after initial render

  useEffect(() => {
    // Filter events whenever searchTerm or events change
    const lowerCaseSearchTerm = searchTerm.toLowerCase();
    const filtered = events.filter(event => 
      event.name.toLowerCase().includes(lowerCaseSearchTerm) ||
      event.description?.toLowerCase().includes(lowerCaseSearchTerm) ||
      event.mode.toLowerCase().includes(lowerCaseSearchTerm)
    );
    setFilteredEvents(filtered);
  }, [searchTerm, events]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  if (loading) {
    return <div>Loading events...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div className="user-event-list-container">
      <h2>Available Events</h2>

      <div>
        <input
          type="text"
          placeholder="Search events..."
          value={searchTerm}
          onChange={handleSearchChange}
        />
      </div>

      {filteredEvents.length === 0 ? (
        <p>No events found.</p>
      ) : (
        <ul>
          {filteredEvents.map((event) => (
            <li key={event.id}>
              <Link to={`/events/${event.id}`}>{event.name}</Link>
              <p>{event.description || 'No description'}</p>
              <p>Dates: {event.start_date} - {event.end_date || 'Ongoing'}</p>
              <p>Mode: {event.mode}</p>
              {/* Actions like Join/Leave will be added later */}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default UserEventList; 