import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Reveal } from '../components/Reveal'

const FAQS = [
  {
    q: 'Does OCULIS open the URL in my browser?',
    a: 'No. The intended OCULIS workflow performs the inspection remotely so the target is not directly opened by the visitor during analysis.',
  },
  {
    q: 'What does OCULIS actually inspect?',
    a: 'Depending on the analysis stage, OCULIS can inspect URL structure, infrastructure signals, redirects, HTTP behavior, browser-rendered content and observed network requests.',
  },
  {
    q: 'Does HTTPS mean a website is safe?',
    a: 'No. HTTPS protects transport between the browser and the destination, but it does not by itself prove that the destination is trustworthy.',
  },
  {
    q: 'Why does OCULIS show evidence with the risk score?',
    a: 'The goal is explainability. A score without supporting evidence is difficult to audit, so findings are tied to observable signals collected during the inspection.',
  },
  {
    q: 'Can OCULIS detect every malicious website?',
    a: 'No security scanner can guarantee detection of every malicious destination. OCULIS provides an evidence-based assessment and should be treated as a security aid, not absolute proof of safety.',
  },
  {
    q: 'Why might an analysis take longer than expected?',
    a: 'Infrastructure resolution, redirects, remote browser rendering and network collection can each add time. OCULIS keeps these stages separate so the result can show where time was spent.',
  },
]

export function FAQ() {
  const [open, setOpen] = useState<number | null>(0)

  return (
    <div className="info-page">
      <Reveal>
        <Link to="/" className="back-btn">← Back to OCULIS</Link>

        <div className="info-hero">
          <div className="eyebrow">FREQUENTLY ASKED QUESTIONS</div>
          <h1>Understand the system<br /><span>before you trust the result.</span></h1>
          <p>
            Common questions about how OCULIS performs remote URL inspection,
            what the results mean and where its boundaries are.
          </p>
        </div>
      </Reveal>

      <Reveal>
        <section className="faq-list">
          {FAQS.map((item, index) => {
            const isOpen = open === index

            return (
              <article key={item.q} className={`faq-item ${isOpen ? 'is-open' : ''}`}>
                <button
                  className="faq-question"
                  onClick={() => setOpen(isOpen ? null : index)}
                  aria-expanded={isOpen}
                >
                  <span>{item.q}</span>
                  <span className="faq-symbol">{isOpen ? '−' : '+'}</span>
                </button>

                <div className="faq-answer">
                  <p>{item.a}</p>
                </div>
              </article>
            )
          })}
        </section>
      </Reveal>
    </div>
  )
}
