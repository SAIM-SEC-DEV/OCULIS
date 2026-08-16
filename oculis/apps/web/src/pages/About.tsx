import { Link } from 'react-router-dom'
import { Reveal } from '../components/Reveal'

export function About() {
  return (
    <div className="info-page">
      <Reveal>
        <Link to="/" className="back-btn">← Back to OCULIS</Link>

        <div className="info-hero">
          <div className="eyebrow">ABOUT OCULIS</div>
          <h1>See what is behind the link.<br /><span>Before you visit it.</span></h1>
          <p>
            OCULIS is a remote web-threat inspection platform designed to let
            users investigate suspicious URLs without opening those destinations
            in their own browser.
          </p>
        </div>
      </Reveal>

      <div className="info-grid">
        <Reveal>
          <section className="info-panel">
            <div className="eyebrow">MISSION</div>
            <h2>Move the risk away from the user.</h2>
            <p>
              OCULIS inspects a submitted URL from an isolated analysis
              environment and returns an evidence-backed assessment of what
              the destination exposed.
            </p>
          </section>
        </Reveal>

        <Reveal delay={1}>
          <section className="info-panel">
            <div className="eyebrow">PRINCIPLE</div>
            <h2>Evidence over assumptions.</h2>
            <p>
              A security verdict should explain itself. OCULIS connects risk
              signals to observable evidence such as redirects, network
              requests, browser artifacts and infrastructure information.
            </p>
          </section>
        </Reveal>
      </div>

      <Reveal>
        <section className="info-panel info-panel--wide">
          <div className="eyebrow">HOW OCULIS WORKS</div>
          <div className="info-steps">
            <div><span>01</span><h3>Submit</h3><p>Provide the URL you want inspected.</p></div>
            <div><span>02</span><h3>Isolate</h3><p>The target is analyzed remotely rather than opened locally.</p></div>
            <div><span>03</span><h3>Observe</h3><p>OCULIS captures infrastructure, browser and network evidence.</p></div>
            <div><span>04</span><h3>Explain</h3><p>The result is presented as an evidence-backed assessment.</p></div>
          </div>
        </section>
      </Reveal>
    </div>
  )
}
