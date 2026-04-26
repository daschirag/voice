import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./AuthContext";
import Login from "./Login";
import Register from "./Register";
import ClientDashboard from "./ClientDashboard";
import AdminDashboard from "./AdminDashboard";

function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div style={{ minHeight:"100vh", display:"flex", alignItems:"center",
      justifyContent:"center", background:"var(--bg)" }}>
      <div style={{ textAlign:"center" }}>
        <div style={{ fontSize:36, marginBottom:16 }}>🎙️</div>
        <div style={{ color:"var(--text3)", fontSize:14 }}>Loading...</div>
      </div>
    </div>
  );
  if (!user) return <Navigate to="/login" replace/>;
  if (role && user.role !== role) return <Navigate to={user.role==="admin"?"/admin":"/client"} replace/>;
  return children;
}

function Root() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace/>;
  return <Navigate to={user.role==="admin"?"/admin":"/client"} replace/>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Root/>}/>
          <Route path="/login" element={<Login/>}/>
          <Route path="/register" element={<Register/>}/>
          <Route path="/client" element={
            <ProtectedRoute role="client"><ClientDashboard/></ProtectedRoute>
          }/>
          <Route path="/admin" element={
            <ProtectedRoute role="admin"><AdminDashboard/></ProtectedRoute>
          }/>
          <Route path="*" element={<Navigate to="/" replace/>}/>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}