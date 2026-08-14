import { Routes, Route, Navigate } from "react-router-dom";
import Home from "./pages/Home";
import Login from "./pages/Login";
import AdminLogin from "./pages/AdminLogin";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Layout } from "./components/Layout";
import Dashboard from "./pages/portal/Dashboard";
import Schedule from "./pages/portal/Schedule";
import History from "./pages/portal/History";
import Progress from "./pages/portal/Progress";
import Courses from "./pages/portal/Courses";
import Appointments from "./pages/portal/Appointments";
import { AdminProtectedRoute } from "./components/admin/AdminProtectedRoute";
import { AdminLayout } from "./components/admin/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminDocuments from "./pages/admin/AdminDocuments";
import AdminStudents from "./pages/admin/AdminStudents";
import AdminStudentDetail from "./pages/admin/AdminStudentDetail";
import AdminCourses from "./pages/admin/AdminCourses";
import AdminEnrollments from "./pages/admin/AdminEnrollments";
import AdminConfig from "./pages/admin/AdminConfig";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/admin/login" element={<AdminLogin />} />

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

      <Route element={<AdminProtectedRoute />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/documents" element={<AdminDocuments />} />
          <Route path="/admin/students" element={<AdminStudents />} />
          <Route path="/admin/students/:studentId" element={<AdminStudentDetail />} />
          <Route path="/admin/courses" element={<AdminCourses />} />
          <Route path="/admin/enrollments" element={<AdminEnrollments />} />
          <Route path="/admin/config" element={<AdminConfig />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
