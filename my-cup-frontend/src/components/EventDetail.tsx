import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Link } from 'react-router-dom';
// Assuming you have a function to get current user ID from token
// import { getCurrentUserId } from '../utils/auth'; // You might need a utility for this

interface EventDetailData {
  id: number;
  name: string;
  description: string | null;
  start_date: string;
  end_date: string | null;
  mode: string; // 'knockout' or 'league'
}

interface Participant {
    id: number;
    username: string;
}

interface Match {
    id: number;
    stage: string | null;
    match_date: string | null;
    match_time: string | null;
    user1_id: number | null;
    user1_username: string | null; // Now available from backend
    user2_id: number | null;
    user2_username: string | null; // Now available from backend
    venue: string | null;
    // Add result info if needed, e.g., scores, winner
    score1: number | null;
    score2: number | null;
    winner_id: number | null;
    // Potentially add a 'status' field like 'scheduled', 'completed', 'cancelled'
    status: string | null;
}

interface Standing {
    user_id: number;
    username: string;
    points: number;
    wins: number;
    draws: number;
    losses: number;
    goals_scored: number;
    goals_against: number;
    games_played: number;
    goal_difference: number;
    position?: number;
}

const EventDetail: React.FC = () => {
  const { eventId } = useParams<{ eventId: string }>();
  const [event, setEvent] = useState<EventDetailData | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [standings, setStandings] = useState<Standing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRegistered, setIsRegistered] = useState(false);
  const [joiningLeaving, setJoiningLeaving] = useState(false);
  const [joinLeaveError, setJoinLeaveError] = useState<string | null>(null);

  // Helper function to check if current user is in the participants list
  const checkRegistrationStatus = (participantsList: Participant[]) => {
    const userToken = localStorage.getItem('userToken');
    if (!userToken) return false; // Not logged in, not registered

    // Assuming token contains user info or you can decode it to get user ID
    // For now, let's assume we can get the current user's username from somewhere,
    // or ideally, the backend /events/{event_id}/participants should indicate if the current user is registered.
    // A simpler approach for now: fetch current user profile and check ID against participant list.
    // Or, modify backend /events/{event_id}/participants to include registration status for current user.
    // Let's use a basic check against username from a hypothetical source for now.

    // TODO: Replace with actual way to get current user ID/username
    // const currentUserId = getCurrentUserId();
    // return participantsList.some(p => p.id === currentUserId);
    // For now, a placeholder check:
    // return participantsList.some(p => p.username === 'loggedInUsername');

    // A more reliable approach: fetch current user profile
    const fetchCurrentUserAndCheckRegistration = async () => {
        try {
            const currentUserToken = localStorage.getItem('userToken');
            if (!currentUserToken) return false; // Not logged in

            const response = await fetch('http://localhost:8000/users/me', {
                headers: { 'Authorization': `Bearer ${currentUserToken}` },
            });
            if (!response.ok) {
                 console.error('Failed to fetch current user for registration check', await response.json());
                 return false;
            }
            const currentUser = await response.json();
            return participantsList.some(p => p.id === currentUser.id);

        } catch (err) {
            console.error('Error fetching current user for registration check', err);
            return false;
        }
    };

    // This needs to be called and its result used to set isRegistered.
    // This makes the useEffect more complex, maybe better to fetch user first,
    // or have backend indicate registration status.

    // For simplicity in this step, let's assume participants list is enough and we can check against username.
    // This is a temporary simplification.
     const loggedInUsername = '...'; // TODO: Get actual logged in username
     return participantsList.some(p => p.username === loggedInUsername);


  };

  const fetchEventDetails = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch Event Basic Details
      const token = localStorage.getItem('userToken'); // Get token
      
      const eventResponse = await fetch(`http://localhost:8000/events/${eventId}`, {
           headers: token ? { 'Authorization': `Bearer ${token}` } : {}, // Include token if available
      });

      if (!eventResponse.ok) {
           if (eventResponse.status === 404) {
               throw new Error('Event not found.');
           } else {
               // For other errors, check if it's a 401 and if a token was expected but missing.
               // If no token was sent, a 401 here might mean the endpoint requires auth,
               // but we want basic info to be public.
               // Let's assume the backend allows GET /events/{eventId} without auth for basic info
               // and only restricts certain details or actions.
               // If the backend *does* require auth for *any* info, we'd need a public endpoint.
               const errorData = await eventResponse.json();
               // If the error is NOT 401 or if a token was present and still failed, throw the error.
               if (eventResponse.status !== 401 || token) {
                   throw new Error(errorData.detail || 'Failed to fetch event details');
               } else {
                   // If it's a 401 and no token was sent, it means auth is required for something,
                   // but we can proceed to fetch public data.
                   console.warn('Could not fetch event details with token, attempting public access.');
                   // Continue without throwing, assuming subsequent fetches are public or handle auth.
               }
           }
      }
      
      // Only parse and set event data if the response was OK (meaning we got basic data)
      let eventData: EventDetailData | null = null;
      if (eventResponse.ok) {
           eventData = await eventResponse.json();
           setEvent(eventData);
      } else {
          setEvent(null); // Set event to null if basic fetch failed
      }

      // Fetch Participants (Public)
      const participantsResponse = await fetch(`http://localhost:8000/events/${eventId}/participants`);
      if (!participantsResponse.ok) {
           const errorData = await participantsResponse.json();
           throw new Error(errorData.detail || 'Failed to fetch participants');
      }
      const participantsData: Participant[] = await participantsResponse.json();
      setParticipants(participantsData);

      // Check registration status after fetching participants (requires token)
      if (token) { // Only attempt to fetch current user if token exists
          const currentUserResponse = await fetch('http://localhost:8000/users/me', {
              headers: { 'Authorization': `Bearer ${token}` }, // Use the same token
          });
          if (currentUserResponse.ok) {
              const currentUser = await currentUserResponse.json();
              setIsRegistered(participantsData.some(p => p.id === currentUser.id));
          } else {
               console.error('Failed to fetch current user for registration check', await currentUserResponse.json());
               setIsRegistered(false); // Assume not registered if cannot get user info or fetch fails
          }
      } else {
          setIsRegistered(false); // Not logged in, so not registered
      }

      // Fetch Matches (Public, now includes usernames)
      const matchesResponse = await fetch(`http://localhost:8000/events/${eventId}/matches`);
      if (!matchesResponse.ok) {
           const errorData = await matchesResponse.json();
           throw new Error(errorData.detail || 'Failed to fetch matches');
      }
      const matchesData: Match[] = await matchesResponse.json();
      // setMatches(matchesData); // Will set matches after fetching results

      // Fetch results for each match
      const matchesWithResults = await Promise.all(matchesData.map(async (match) => {
          if (match.status === 'completed') { // Only fetch results for completed matches
              try {
                  const resultResponse = await fetch(`http://localhost:8000/matches/${match.id}/results`);
                  if (!resultResponse.ok) {
                       // Log error but don't block the whole process
                       console.error(`Failed to fetch results for match ${match.id}:`, await resultResponse.json());
                       return match; // Return original match data if fetching results fails
                  }
                  const resultData = await resultResponse.json();
                  return { ...match, ...resultData }; // Merge match data with result data
              } catch (err) {
                   console.error(`Error fetching results for match ${match.id}:`, err);
                   return match; // Return original match data on error
              }
          } else {
              return match; // Return original match data for non-completed matches
          }
      }));

      setMatches(matchesWithResults); // Set matches state with results

      // Fetch Standings if mode is 'league' (Public)
      if (eventData?.mode === 'league') { // Check eventData is not null
           const standingsResponse = await fetch(`http://localhost:8000/events/${eventId}/standings`);
           if (!standingsResponse.ok) {
              const errorData = await standingsResponse.json();
              throw new Error(errorData.detail || 'Failed to fetch standings');
           }
           const standingsData: Standing[] = await standingsResponse.json();
           setStandings(standingsData);
      } else {
          setStandings([]); // Clear standings if not league mode or event data is null
      }


    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (eventId) {
        fetchEventDetails();
    }
  }, [eventId]); // Rerun effect if eventId changes

  const handleJoinEvent = async () => {
    setJoiningLeaving(true);
    setJoinLeaveError(null);
    try {
      const token = localStorage.getItem('userToken');
      if (!token) {
        setJoinLeaveError('Please log in to join this event.');
        setJoiningLeaving(false);
        return;
      }
      const response = await fetch(`http://localhost:8000/events/${eventId}/join`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to join event');
      }

      // Successfully joined, refresh details
      fetchEventDetails();

    } catch (err: any) {
      setJoinLeaveError(err.message);
    } finally {
      setJoiningLeaving(false);
    }
  };

  const handleLeaveEvent = async () => {
    setJoiningLeaving(true);
    setJoinLeaveError(null);
    try {
      const token = localStorage.getItem('userToken');
      if (!token) {
        setJoinLeaveError('Please log in to leave this event.');
        setJoiningLeaving(false);
        return;
      }
      const response = await fetch(`http://localhost:8000/events/${eventId}/leave`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

       if (response.status === 404) {
           setJoinLeaveError('You are not registered for this event.');
       } else if (!response.ok) {
           const errorData = await response.json();
           throw new Error(errorData.detail || 'Failed to leave event');
       }

      // Successfully left, refresh details
      fetchEventDetails();

    } catch (err: any) {
      setJoinLeaveError(err.message);
    } finally {
      setJoiningLeaving(false);
    }
  };


  if (loading) {
    return <div>Loading event details...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!event) {
      return <div>Event not found.</div>; // Handle case where event is null after loading
  }

  return (
    <div className="event-detail-container">
      <h2>{event.name}</h2>
      <p><strong>Description:</strong> {event.description || 'N/A'}</p>
      <p><strong>Dates:</strong> {event.start_date} - {event.end_date || 'Ongoing'}</p>
      <p><strong>Mode:</strong> {event.mode}</p>

      {/* Join/Leave Event Buttons */}
      <div>
          {localStorage.getItem('userToken') ? ( // Only show buttons if logged in
              isRegistered ? (
                  <button onClick={handleLeaveEvent} disabled={joiningLeaving}>
                      {joiningLeaving ? 'Leaving...' : 'Leave Event'}
                  </button>
              ) : (
                   <button onClick={handleJoinEvent} disabled={joiningLeaving}>
                       {joiningLeaving ? 'Joining...' : 'Join Event'}
                   </button>
              )
          ) : (
              <p><Link to="/login">Log in</Link> to join or leave this event.</p>
          )}
          {joinLeaveError && <p style={{ color: 'red' }}>{joinLeaveError}</p>}
      </div>

      <h3>Participants ({participants.length})</h3>
      {participants.length === 0 ? (
          <p>No participants registered yet.</p>
      ) : (
          <ul>
              {participants.map(participant => (
                  <li key={participant.id}>{participant.username}</li>
              ))}
          </ul>
      )}

      <h3>Matches</h3>
      {matches.length === 0 ? (
          <p>No matches scheduled yet.</p>
      ) : (
          <table>
              <thead>
                  <tr>
                      <th>Stage</th>
                      <th>Date</th>
                      <th>Time</th>
                      <th>Venue</th>
                      <th>Players</th>
                      {/* Add result columns if needed */}
                  </tr>
              </thead>
              <tbody>
                  {matches.map(match => (
                      <tr key={match.id}>
                          <td>{match.stage || 'N/A'}</td>
                          <td>{match.match_date || 'N/A'}</td>
                          <td>{match.match_time || 'N/A'}</td>
                          <td>{match.venue || 'N/A'}</td>
                           {/* Display participant usernames using data from backend */}
                          <td>{match.user1_username || 'N/A'} vs {match.user2_username || 'N/A'}</td>
                          {/* Add result data here if available */}
                          <td>
                              {match.status === 'completed' && match.score1 !== null && match.score2 !== null ? (
                                  `${match.score1} - ${match.score2}`
                              ) : match.status === 'cancelled' ? (
                                  'Cancelled'
                              ) : (
                                  'Upcoming' // Or any other suitable indicator
                              )}
                          </td>
                          <td>
                              {match.status === 'completed' && match.winner_id !== null ? (
                                  match.winner_id === match.user1_id ? match.user1_username : match.user2_username
                              ) : (
                                  '-'
                              )}
                          </td>
                      </tr>
                  ))}
              </tbody>
          </table>
      )}

      {event.mode === 'league' && standings.length > 0 && (
          <> {/* Use React Fragment */}
              <h3>League Standings</h3>
              <table>
                  <thead>
                      <tr>
                          <th>Position</th>
                          <th>Player</th>
                          <th>Points</th>
                          <th>Played</th>
                          <th>Wins</th>
                          <th>Draws</th>
                          <th>Losses</th>
                          <th>Goals Scored</th>
                          <th>Goals Against</th>
                          <th>Goal Difference</th>
                      </tr>
                  </thead>
                  <tbody>
                      {standings.map(standing => (
                          <tr key={standing.user_id}>
                              <td>{standing.position}</td>
                              <td>{standing.username}</td>
                              <td>{standing.points}</td>
                              <td>{standing.games_played}</td>
                              <td>{standing.wins}</td>
                              <td>{standing.draws}</td>
                              <td>{standing.losses}</td>
                              <td>{standing.goals_scored}</td>
                              <td>{standing.goals_against}</td>
                              <td>{standing.goal_difference}</td>
                          </tr>
                      ))}
                  </tbody>
              </table>
          </>
      )}

    </div>
  );
};

export default EventDetail; 