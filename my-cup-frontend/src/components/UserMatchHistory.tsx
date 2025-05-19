import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

interface Match {
    id: number;
    event_name: string;
    stage: string | null;
    match_date: string | null;
    match_time: string | null;
    user1_username: string | null;
    user2_username: string | null;
    score1: number | null;
    score2: number | null;
    winner_username: string | null;
    status: string | null;
}

const UserMatchHistory: React.FC = () => {
    const [matches, setMatches] = useState<Match[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchUserMatches = async () => {
            try {
                setLoading(true);
                setError(null);

                const token = localStorage.getItem('userToken');
                if (!token) {
                    setError('Authentication token not available. Please log in.');
                    setLoading(false);
                    return;
                }

                const response = await fetch('http://localhost:8000/users/me/matches', {
                    headers: { 'Authorization': `Bearer ${token}` },
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to fetch match history');
                }

                const matchesData: Match[] = await response.json();
                setMatches(matchesData);

            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchUserMatches();
    }, []); // Empty dependency array means this effect runs once on mount

    if (loading) {
        return <div>Loading match history...</div>;
    }

    if (error) {
        return <div>Error: {error}</div>;
    }

    return (
        <div className="user-match-history-container">
            <h2>Your Match History</h2>
            {matches.length === 0 ? (
                <p>No matches found.</p>
            ) : (
                <table>
                    <thead>
                        <tr>
                            <th>Event</th>
                            <th>Stage</th>
                            <th>Date</th>
                            <th>Time</th>
                            <th>Players</th>
                            <th>Result</th>
                            <th>Winner</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {matches.map(match => (
                            <tr key={match.id}>
                                <td>{match.event_name}</td>
                                <td>{match.stage || 'N/A'}</td>
                                <td>{match.match_date || 'N/A'}</td>
                                <td>{match.match_time || 'N/A'}</td>
                                <td>{match.user1_username || 'N/A'} vs {match.user2_username || 'N/A'}</td>
                                <td>
                                    {match.status === 'completed' && match.score1 !== null && match.score2 !== null ? (
                                        `${match.score1} - ${match.score2}`
                                    ) : (
                                        '-'
                                    )}
                                </td>
                                <td>{match.winner_username || '-'}</td>
                                <td>{match.status || 'N/A'}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
};

export default UserMatchHistory; 