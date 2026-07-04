import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Tool from "./pages/Tool.jsx";
import WaterTool from "./pages/WaterTool.jsx";
import MyAlerts from "./pages/MyAlerts.jsx";
import "./App.css";

function ProtectedRoute({ children }) {
  const { isLoggedIn, checking } = useAuth();
  if (checking) return <div style={{ padding: "2rem" }}>Loading…</div>;
  if (!isLoggedIn) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/tool" element={<ProtectedRoute><Tool /></ProtectedRoute>} />
      <Route path="/water-tool" element={<ProtectedRoute><WaterTool /></ProtectedRoute>} />
      <Route path="/my-alerts" element={<ProtectedRoute><MyAlerts /></ProtectedRoute>} />
    </Routes>
  );
}