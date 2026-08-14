import { Routes, Route, Navigate } from "react-router-dom";
import Home from "./pages/Home";
import Login from "./pages/Login";
import AdminLogin from "./pages/AdminLogin";
import Admin from "./pages/Admin";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Layout } from "./components/Layout";
import Dashboard from "./pages/portal/Dashboard";
import Schedule from "./pages/portal/Schedule";
import History from "./pages/portal/History";
import Progress from "./pages/portal/Progress";
import Courses from "./pages/portal/Courses";
import Appointments from "./pages/portal/Appointments";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/admin/login" element={<AdminLogin />} />
      <Route path="/admin" element={<Admin />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/portal" element={<Dashboard />} />
          <Route path="/portal/schedule" element={<Schedule />} />
          <Route path="/portal/history" element={<History />} />
          <Route path="/portal/progress" element={<Progress />} />
          <Route path="/portal/courses" element={<Courses />} />
          <Route path="/portal/appointments" element={<Appointments />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
