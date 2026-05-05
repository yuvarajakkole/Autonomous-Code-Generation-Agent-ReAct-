import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import HomePage from './pages/HomePage'
import AgentPage from './pages/AgentPage'
import HistoryPage from './pages/HistoryPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/"               element={<HomePage />} />
        <Route path="/agent/:sessionId" element={<AgentPage />} />
        <Route path="/history"        element={<HistoryPage />} />
      </Routes>
    </Layout>
  )
}
