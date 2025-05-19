import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';

const ProtectedRoute: React.FC = () => {
  // Check if either adminToken or userToken exists in localStorage
  const adminToken = localStorage.getItem('adminToken');
  const userToken = localStorage.getItem('userToken');

  // If either token is found, render the child routes/components
  // Otherwise, redirect to the login page
  return (adminToken || userToken) ? <Outlet /> : <Navigate to="/login" />;
};

export default ProtectedRoute; 