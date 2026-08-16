import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Home } from './pages/Home'
import { Analysis } from './pages/Analysis'
import { About } from './pages/About'
import { Privacy } from './pages/Privacy'
import { FAQ } from './pages/FAQ'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/analysis/:id" element={<Analysis />} />
        <Route path="/about" element={<About />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/faq" element={<FAQ />} />
      </Routes>
    </Layout>
  )
}
