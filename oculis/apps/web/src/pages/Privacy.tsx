import { Link } from 'react-router-dom'
import { Reveal } from '../components/Reveal'

export function Privacy() {
  return (
    <div className="info-page">
      <Reveal>
        <Link to="/" className="back-btn">← Back to OCULIS</Link>

        <div className="info-hero">
          <div className="eyebrow">PRIVACY POLICY</div>
          <h1>Your inspection should not become<br /><span>someone else's data.</span></h1>
          <p>
            This policy describes the intended privacy model for the current
            OCULIS application. Update the retention and processing statements
            before public deployment so they match the production backend.
          </p>
        </div>
      </Reveal>

      <div className="privacy-list">
        <Reveal>
          <section className="info-panel">
            <div className="eyebrow">01 / SUBMITTED URLS</div>
            <h2>What you provide</h2>
            <p>
              OCULIS receives the URL submitted for analysis. The URL is used
              to perform the requested security inspection and generate the
              corresponding analysis result.
            </p>
          </section>
        </Reveal>

        <Reveal>
          <section className="info-panel">
            <div className="eyebrow">02 / ANALYSIS DATA</div>
            <h2>What may be observed</h2>
            <p>
              An inspection may generate technical artifacts including DNS,
              TLS, HTTP, redirect, browser and network metadata, depending on
              what the target exposes and what the analysis pipeline captures.
            </p>
          </section>
        </Reveal>

        <Reveal>
          <section className="info-panel">
            <div className="eyebrow">03 / LOCAL SAFETY</div>
            <h2>Your browser is not the inspection environment.</h2>
            <p>
              The core purpose of OCULIS is to inspect the destination remotely
              so the submitted target is not directly opened by the visitor's
              browser as part of the analysis workflow.
            </p>
          </section>
        </Reveal>
      </div>
    </div>
  )
}
