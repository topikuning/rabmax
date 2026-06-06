import { Navigate, Route, Routes } from 'react-router-dom';
import { auth } from '@/lib/api';
import { Shell } from '@/components/shell';
import Login from '@/pages/Login';
import Projects from '@/pages/Projects';
import Ahsp from '@/pages/Ahsp';
import BahanUpah from '@/pages/BahanUpah';
import Workspace from '@/pages/Workspace';
import Admin from '@/pages/Admin';

function Guard({ children }: { children: JSX.Element }) {
  return auth.isAuthed() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Guard><Shell /></Guard>}>
        <Route path="/" element={<Projects />} />
        <Route path="/projects/:id" element={<Workspace />} />
        <Route path="/ahsp" element={<Ahsp />} />
        <Route path="/bahan-upah" element={<BahanUpah />} />
        <Route path="/admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
