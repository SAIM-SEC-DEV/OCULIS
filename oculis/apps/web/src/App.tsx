import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Home } from './pages/Home'
import { Analysis } from './pages/Analysis'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/analysis/:id" element={<Analysis />} />
      </Routes>
    </Layout>
  )
}
